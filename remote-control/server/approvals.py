"""权限确认中继:灰区工具调用挂起等人工裁决,超时默认拒绝。

判定顺序(硬约束,见 runner.py `_build_can_use_tool`):
1. 黑名单(DANGEROUS_BASH_PATTERNS)命中 → 硬拒绝,**永远不进确认中继**;
2. 灰区(CONFIRM_BASH_PATTERNS)命中 → 这里挂起等裁决;
3. 其余 → 直接放行(与 P1 行为一致)。

挂起的请求同时走三路通知:落库(pending_approvals)、写 run 日志(经既有 SSE
推给打开的详情页)、Web Push(approval_pending)。裁决经 POST /approvals/{id}
(认证 + 审计);到 APPROVAL_TIMEOUT_SECONDS 没人裁决 → expired → 拒绝执行。
"""

import asyncio
import json
import time
import uuid

from . import config, push, store

# approval_id → (等待事件, 裁决结果)。只存在于本进程内存:服务重启后 pending 的
# 确认没有等待者,谁也放不了行——失败关闭(fail closed),符合默认拒绝原则。
_waiters: dict[str, asyncio.Event] = {}
_decisions: dict[str, bool] = {}


def _append_log_event(log_path: str, event: dict) -> None:
    # 独立 open(append)+close:与 runner 主循环的日志写入互不共享句柄,
    # O_APPEND 保证小行写入不互相覆盖。
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


async def request_approval(run_id: str, log_path: str, tool_name: str, input_preview: str) -> bool:
    """挂起一个确认请求,阻塞到有人裁决或超时。返回是否放行(超时/异常一律 False)。"""
    approval_id = uuid.uuid4().hex
    expires_at = time.time() + config.APPROVAL_TIMEOUT_SECONDS
    store.create_approval(approval_id, run_id, tool_name, input_preview, expires_at)
    _waiters[approval_id] = asyncio.Event()

    _append_log_event(
        log_path,
        {
            "type": "approval_request",
            "approval_id": approval_id,
            "tool_name": tool_name,
            "input": input_preview,
            "expires_at": expires_at,
        },
    )
    await push.notify_run_event("approval_pending", run_id, f"{tool_name} 等待确认(run {run_id})")

    try:
        await asyncio.wait_for(_waiters[approval_id].wait(), timeout=config.APPROVAL_TIMEOUT_SECONDS)
        return _decisions.get(approval_id, False)
    except asyncio.TimeoutError:
        # 超时默认拒绝:finalize 带 pending 守卫,若恰好同时被裁决则以裁决为准。
        if store.finalize_approval(approval_id, "expired", None):
            _append_log_event(
                log_path, {"type": "approval_decision", "approval_id": approval_id, "status": "expired"}
            )
            return False
        return _decisions.get(approval_id, False)
    except asyncio.CancelledError:
        # run 被 stop:把挂着的确认落成 expired,再继续向上抛。
        store.finalize_approval(approval_id, "expired", None)
        raise
    finally:
        _waiters.pop(approval_id, None)
        _decisions.pop(approval_id, None)


def resolve(approval_id: str, allow: bool, decided_by: str) -> str | None:
    """人工裁决。返回落定的状态("allowed"/"denied"),None 表示已非 pending(409)。"""
    status = "allowed" if allow else "denied"
    if not store.finalize_approval(approval_id, status, decided_by):
        return None
    _decisions[approval_id] = allow
    waiter = _waiters.get(approval_id)
    if waiter:
        waiter.set()
    # 把裁决结果也写进 run 日志,详情页(含回放)能看到闭环。
    approval = store.get_approval(approval_id)
    if approval:
        run = store.get_run(approval["run_id"])
        if run:
            _append_log_event(
                run["log_path"],
                {"type": "approval_decision", "approval_id": approval_id, "status": status},
            )
    return status
