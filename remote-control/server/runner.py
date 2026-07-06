import asyncio
import re

from claude_agent_sdk import (
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    query,
)

from . import config, store

_DANGEROUS_RE = [re.compile(p) for p in config.DANGEROUS_BASH_PATTERNS]


async def _can_use_tool(tool_name, tool_input, context):
    if tool_name == "Bash":
        cmd = str(tool_input.get("command", ""))
        for pattern in _DANGEROUS_RE:
            if pattern.search(cmd):
                return PermissionResultDeny(
                    message=f"remote-control guard 拦截:命令匹配高危特征 {pattern.pattern!r}"
                )
    return PermissionResultAllow()


async def execute_run(run_id: str, prompt: str, cwd: str) -> None:
    store.set_status(run_id, "running")
    run = store.get_run(run_id)
    log_path = run["log_path"]

    options = ClaudeAgentOptions(
        cwd=cwd,
        permission_mode=config.FIXED_PERMISSION_MODE,
        max_turns=config.MAX_TURNS,
        max_budget_usd=config.MAX_BUDGET_USD,
        can_use_tool=_can_use_tool,
    )

    async def _prompt_stream():
        # can_use_tool 要求流式输入(AsyncIterable),不能直接传字符串,见 SDK 报错:
        # "can_use_tool callback requires streaming mode."
        yield {"type": "user", "message": {"role": "user", "content": prompt}}

    try:
        with open(log_path, "a", encoding="utf-8") as f:

            async def _run() -> None:
                async for message in query(prompt=_prompt_stream(), options=options):
                    f.write(repr(message) + "\n")
                    f.flush()

            await asyncio.wait_for(_run(), timeout=config.RUN_TIMEOUT_SECONDS)
        store.set_status(run_id, "completed")
    except asyncio.TimeoutError:
        store.set_status(run_id, "failed", error="timeout")
    except Exception as exc:  # noqa: BLE001 - 任何异常都要落到 run 状态里,不能让后台任务默默失败
        store.set_status(run_id, "failed", error=str(exc))
