"""Web Push(VAPID)发送。

设计约束:
- 未配置 VAPID(或没装 pywebpush)时 enabled() 为 False,所有发送函数直接 no-op,
  订阅端点返回 enabled=false——push 是可选增强,缺配置绝不影响触发/流式/停止等核心功能。
- payload 只带类型/run_id/短标题,不带 prompt 全文或命令全文:Web Push 消息体虽然
  端到端加密(aes128gcm,只有订阅浏览器能解),但仍坚持最小化原则。
- 发送失败只影响该订阅:404/410(订阅已失效)自动清理,其他异常吞掉不冒泡——
  推送失败绝不能把 run 状态搞挂。
"""

import asyncio
import json

from . import config, store

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - 环境没装 pywebpush 时静默关闭
    webpush = None
    WebPushException = Exception


def enabled() -> bool:
    return bool(
        webpush is not None
        and config.VAPID_PRIVATE_KEY
        and config.VAPID_PUBLIC_KEY
        and config.VAPID_SUBJECT
    )


def _send_one(subscription: dict, payload: str) -> None:
    webpush(
        subscription_info=subscription,
        data=payload,
        vapid_private_key=config.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": config.VAPID_SUBJECT},
    )


async def notify_all(payload: dict) -> None:
    """向所有订阅广播一条通知。任何失败都不冒泡到调用方(推送挂了不能影响 run)。"""
    if not enabled():
        return
    try:
        data = json.dumps(payload, ensure_ascii=False)
        subs = store.list_push_subscriptions()
    except Exception:  # noqa: BLE001
        return
    for sub in subs:
        try:
            # pywebpush 是同步 requests 实现,丢线程池避免卡住事件循环。
            await asyncio.to_thread(_send_one, sub["subscription"], data)
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):  # 订阅已被浏览器/推送服务作废
                store.remove_push_subscription(sub["endpoint"])
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - 网络抖动等,跳过这个订阅
            continue


async def notify_run_event(event_type: str, run_id: str, body: str) -> None:
    titles = {
        "run_completed": "运行完成",
        "run_failed": "运行失败",
        "approval_pending": "等待确认",
    }
    await notify_all(
        {
            "type": event_type,
            "run_id": run_id,
            "title": titles.get(event_type, "remote-control"),
            "body": body,
        }
    )
