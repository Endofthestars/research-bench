import asyncio
import json
import re

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from . import approvals, config, push, store

_DANGEROUS_RE = [re.compile(p) for p in config.DANGEROUS_BASH_PATTERNS]
_CONFIRM_RE = [re.compile(p) for p in config.CONFIRM_BASH_PATTERNS]

# run_id → 后台任务句柄(main.py 里 create_task 后调用 track 登记),
# stop 端点靠它取消运行。任务结束(含取消)后由 done callback 自动清理。
_active_tasks: dict[str, asyncio.Task] = {}

# 结构化日志里各类文本字段的截断上限:transcript 是给面板看的摘要视图,
# 不是完整存档(完整对话在 Claude Code 自己的 session 文件里,resume 不受影响)。
_TEXT_LIMIT = 4000
_PREVIEW_LIMIT = 600


def track(run_id: str, task: asyncio.Task) -> None:
    _active_tasks[run_id] = task
    task.add_done_callback(lambda _t: _active_tasks.pop(run_id, None))


def stop_run(run_id: str) -> bool:
    """取消 run 的后台任务。返回是否真的发出了取消(没有活任务则 False)。

    取消语义:cancel 让 execute_run 里的 `async for message in query(...)` 抛
    CancelledError,SDK 的 query() 生成器在 finally 里关闭 transport——先给 CLI
    子进程发 SIGTERM,宽限期内没退再 SIGKILL(见 claude_agent_sdk/_internal/
    transport/subprocess_cli.py 的 close 逻辑)。所以 asyncio 层取消就足以真正
    杀掉底下的子进程,不需要我们自己管 PID。
    """
    task = _active_tasks.get(run_id)
    if task is None or task.done():
        return False
    task.cancel()
    return True


def _build_can_use_tool(run_id: str, log_path: str):
    """按 run 构造 can_use_tool 回调(确认中继需要知道自己属于哪个 run / 写哪个日志)。

    判定顺序是安全边界的一部分,不可调换:
    1. 黑名单命中 → 硬拒绝,**不进确认中继**(不存在"人工放行黑名单命令"的路径);
    2. 灰区命中 → 挂起等人工裁决,超时默认拒绝;
    3. 其余 → 放行(与 P1 之前的策略一致)。
    """

    async def _can_use_tool(tool_name, tool_input, context):
        if tool_name == "Bash":
            cmd = str(tool_input.get("command", ""))
            for pattern in _DANGEROUS_RE:
                if pattern.search(cmd):
                    return PermissionResultDeny(
                        message=f"remote-control guard 拦截:命令匹配高危特征 {pattern.pattern!r}"
                    )
            for pattern in _CONFIRM_RE:
                if pattern.search(cmd):
                    allowed = await approvals.request_approval(
                        run_id, log_path, tool_name, _clip(cmd, _PREVIEW_LIMIT)
                    )
                    if allowed:
                        return PermissionResultAllow()
                    return PermissionResultDeny(
                        message="remote-control 确认中继:被拒绝或超时未确认(默认拒绝)"
                    )
        return PermissionResultAllow()

    return _can_use_tool


def _clip(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + f"…[截断,共{len(text)}字符]"


def _tool_result_text(content) -> str:
    """ToolResultBlock.content 可能是 str 或 [{'type':'text','text':...}, ...]。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text", "")))
        else:
            parts.append(str(item))
    return "\n".join(parts)


def _events_from_message(message) -> list[dict]:
    """把 SDK 消息拍平成最小结构化事件(每个事件一行 JSONL,也是 SSE log 事件的 data)。

    字段约定(前端按 type 分块渲染,未知 type/非 JSON 行按纯文本兜底,兼容旧 repr 日志):
    - {"type":"text","role":"assistant"|"user","text":...}
    - {"type":"thinking","text":...}
    - {"type":"tool_use","tool_name":...,"input":<截断的入参摘要>}
    - {"type":"tool_result","text":...,"is_error":bool}
    - {"type":"system","subtype":...,"session_id":?,"model":?}
    - {"type":"result","subtype":...,"is_error":bool,"total_cost_usd":?,"num_turns":?}
    """
    if isinstance(message, SystemMessage):
        event = {"type": "system", "subtype": message.subtype}
        if message.subtype == "init":
            event["session_id"] = message.data.get("session_id")
            event["model"] = message.data.get("model")
        return [event]

    if isinstance(message, AssistantMessage):
        events = []
        for block in message.content:
            if isinstance(block, TextBlock):
                events.append({"type": "text", "role": "assistant", "text": _clip(block.text, _TEXT_LIMIT)})
            elif isinstance(block, ThinkingBlock):
                events.append({"type": "thinking", "text": _clip(block.thinking, _PREVIEW_LIMIT)})
            elif isinstance(block, ToolUseBlock):
                events.append(
                    {
                        "type": "tool_use",
                        "tool_name": block.name,
                        "input": _clip(json.dumps(block.input, ensure_ascii=False), _PREVIEW_LIMIT),
                    }
                )
        return events

    if isinstance(message, UserMessage):
        events = []
        if isinstance(message.content, str):
            events.append({"type": "text", "role": "user", "text": _clip(message.content, _TEXT_LIMIT)})
        else:
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    events.append(
                        {
                            "type": "tool_result",
                            "text": _clip(_tool_result_text(block.content), _PREVIEW_LIMIT),
                            "is_error": bool(block.is_error),
                        }
                    )
                elif isinstance(block, TextBlock):
                    events.append({"type": "text", "role": "user", "text": _clip(block.text, _TEXT_LIMIT)})
        return events

    if isinstance(message, ResultMessage):
        return [
            {
                "type": "result",
                "subtype": message.subtype,
                "is_error": message.is_error,
                "total_cost_usd": message.total_cost_usd,
                "num_turns": message.num_turns,
                "duration_ms": message.duration_ms,
            }
        ]

    # 未知消息类型:repr 兜底,前端按纯文本渲染。
    return [{"type": "raw", "text": _clip(repr(message), _PREVIEW_LIMIT)}]


async def execute_run(run_id: str, prompt: str, cwd: str, resume_session_id: str | None = None) -> None:
    store.set_status(run_id, "running")
    run = store.get_run(run_id)
    log_path = run["log_path"]

    options = ClaudeAgentOptions(
        cwd=cwd,
        permission_mode=config.FIXED_PERMISSION_MODE,
        max_turns=config.MAX_TURNS,
        max_budget_usd=config.MAX_BUDGET_USD,
        can_use_tool=_build_can_use_tool(run_id, log_path),
        # 续聊:resume 原 run 的 session(不设 fork_session,延续同一会话上下文)。
        # 权限模式/预算/黑名单与首次触发完全一致,续聊不是权限放宽的通道。
        resume=resume_session_id,
    )

    async def _prompt_stream():
        # can_use_tool 要求流式输入(AsyncIterable),不能直接传字符串,见 SDK 报错:
        # "can_use_tool callback requires streaming mode."
        yield {"type": "user", "message": {"role": "user", "content": prompt}}

    try:
        with open(log_path, "a", encoding="utf-8") as f:

            async def _run() -> None:
                async for message in query(prompt=_prompt_stream(), options=options):
                    for event in _events_from_message(message):
                        f.write(json.dumps(event, ensure_ascii=False) + "\n")
                    f.flush()
                    # session_id 落库:init 系统消息里最早出现(即使 run 中途失败/被停
                    # 也已捕获),ResultMessage 里再兜底一次。
                    if isinstance(message, SystemMessage) and message.subtype == "init":
                        session_id = message.data.get("session_id")
                        if session_id:
                            store.set_session_id(run_id, session_id)
                    elif isinstance(message, ResultMessage):
                        if message.session_id:
                            store.set_session_id(run_id, message.session_id)
                        store.set_result_meta(
                            run_id,
                            total_cost_usd=message.total_cost_usd,
                            num_turns=message.num_turns,
                            usage=message.usage,
                        )

            await asyncio.wait_for(_run(), timeout=config.RUN_TIMEOUT_SECONDS)
        store.set_status(run_id, "completed")
        await push.notify_run_event("run_completed", run_id, f"run {run_id} 完成")
    except asyncio.TimeoutError:
        store.set_status(run_id, "failed", error="timeout")
        await push.notify_run_event("run_failed", run_id, f"run {run_id} 超时")
    except asyncio.CancelledError:
        # stop 端点(或进程退出)取消了任务:落状态后继续向上抛,遵守取消协议。
        # 主动停止不推送(是用户自己操作的,推了也是噪音)。
        store.set_status(run_id, "stopped")
        raise
    except Exception as exc:  # noqa: BLE001 - 任何异常都要落到 run 状态里,不能让后台任务默默失败
        store.set_status(run_id, "failed", error=str(exc))
        await push.notify_run_event("run_failed", run_id, f"run {run_id} 失败")
