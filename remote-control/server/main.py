import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from typing import Literal

from . import approvals, auth, config, push, runner, store
from .auth import verify_stream_access, verify_token

_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_RUNS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init_db()
    yield


app = FastAPI(title="remote-control", lifespan=lifespan)


class TriggerRequest(BaseModel):
    # 注意:这里故意不暴露 permission_mode 字段——权限上限在 runner.py 里写死,
    # 客户端没有任何办法把它调高。
    project_key: str = Field(..., description="必须命中服务端白名单里的 key,不接受任意路径")
    prompt: str = Field(..., min_length=1, max_length=8000)


class ContinueRequest(BaseModel):
    # 故意只收 prompt:project_key/cwd 沿用原 run(续聊不允许换项目),
    # permission_mode 等与首次触发一样由服务端写死。
    prompt: str = Field(..., min_length=1, max_length=8000)


class PushSubscription(BaseModel):
    # 浏览器 PushSubscription.toJSON() 的最小必需形状,多余字段忽略。
    endpoint: str = Field(..., min_length=1, max_length=2000)
    keys: dict[str, str] = Field(..., description="p256dh + auth")


class PushUnsubscribe(BaseModel):
    endpoint: str = Field(..., min_length=1, max_length=2000)


class ApprovalDecision(BaseModel):
    decision: Literal["allow", "deny"]


def _audit(event: str) -> None:
    with open(config.AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(event + "\n")


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/config/projects", dependencies=[Depends(verify_token)])
async def list_projects():
    return {"projects": sorted(config.PROJECT_DIRS.keys())}


@app.get("/config/presets", dependencies=[Depends(verify_token)])
async def list_presets():
    """常用 prompt 预设(label + prompt);前端渲染成填充输入框的按钮。未配置则空。"""
    return {"presets": config.PRESETS}


@app.get("/probes", dependencies=[Depends(verify_token)])
async def list_probes():
    """只读查看 env 白名单里登记的探针 JSON 文件(DESIGN §3.2 探针-看门狗的查看端)。

    单个文件缺席/超大/非法 JSON 只在该项返回 error,不整体失败;绝不写探针文件。
    """
    import json

    now = time.time()
    result = []
    for name, path in config.PROBE_FILES.items():
        item: dict = {"name": name}
        try:
            if not path.is_file():
                item["error"] = "not found"
            elif path.stat().st_size > config.PROBE_MAX_BYTES:
                item["error"] = f"file too large (> {config.PROBE_MAX_BYTES} bytes)"
            else:
                mtime = path.stat().st_mtime
                item["mtime"] = mtime
                item["age_seconds"] = round(now - mtime, 1)
                item["stale"] = (now - mtime) > config.PROBE_STALE_SECONDS
                item["data"] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            item["error"] = f"invalid json: {e}"
        except OSError as e:
            item["error"] = f"read error: {e}"
        result.append(item)
    return {"probes": result, "stale_threshold_seconds": config.PROBE_STALE_SECONDS}


@app.post("/triggers", dependencies=[Depends(verify_token)])
async def create_trigger(req: TriggerRequest, request: Request):
    if req.project_key not in config.PROJECT_DIRS:
        raise HTTPException(status_code=400, detail="unknown project_key")
    if store.count_active() >= config.MAX_CONCURRENT_RUNS:
        raise HTTPException(status_code=429, detail="too many concurrent runs, try again later")

    source_ip = request.client.host if request.client else "unknown"
    run_id = store.create_run(req.project_key, req.prompt, source_ip)
    cwd = str(config.PROJECT_DIRS[req.project_key])

    _audit(
        f"{time.time()} trigger run_id={run_id} project_key={req.project_key} "
        f"ip={source_ip} prompt={req.prompt!r}"
    )

    async def _bounded_run() -> None:
        async with _semaphore:
            await runner.execute_run(run_id, req.prompt, cwd)

    task = asyncio.create_task(_bounded_run())
    runner.track(run_id, task)  # 登记任务句柄,stop 端点靠它取消
    return {"run_id": run_id, "status": "queued"}


@app.get("/triggers", dependencies=[Depends(verify_token)])
async def list_triggers():
    return store.list_runs()


@app.get("/triggers/{run_id}", dependencies=[Depends(verify_token)])
async def get_trigger(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="not found")
    run["children"] = store.list_children(run_id)  # 对话链:continue 出来的后继 run
    return run


@app.post("/triggers/{run_id}/continue", dependencies=[Depends(verify_token)])
async def continue_trigger(run_id: str, req: ContinueRequest, request: Request):
    """会话续聊:以 SDK resume 方式在原 run 的会话上下文里继续执行新 prompt。

    沿用原 run 的 project_key/cwd,客户端无法换项目;权限模式/预算/超时/黑名单
    与首次触发完全一致,续聊不放宽任何安全边界。
    """
    parent = store.get_run(run_id)
    if not parent:
        raise HTTPException(status_code=404, detail="not found")
    if parent["status"] not in store.TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail=f"run not finished yet (status={parent['status']})")
    if not parent["session_id"]:
        raise HTTPException(status_code=409, detail="run has no session_id, cannot resume")
    if parent["project_key"] not in config.PROJECT_DIRS:
        # 白名单可能在原 run 之后收紧过:key 已被移除的项目不允许续聊。
        raise HTTPException(status_code=409, detail="project_key no longer allowed")
    if store.count_active() >= config.MAX_CONCURRENT_RUNS:
        raise HTTPException(status_code=429, detail="too many concurrent runs, try again later")

    source_ip = request.client.host if request.client else "unknown"
    new_run_id = store.create_run(parent["project_key"], req.prompt, source_ip, parent_run_id=run_id)
    store.set_session_id(new_run_id, parent["session_id"])  # 先继承,跑起来后被实际值覆盖
    cwd = str(config.PROJECT_DIRS[parent["project_key"]])

    _audit(
        f"{time.time()} continue run_id={new_run_id} parent={run_id} "
        f"session={parent['session_id']} project_key={parent['project_key']} "
        f"ip={source_ip} prompt={req.prompt!r}"
    )

    async def _bounded_run() -> None:
        async with _semaphore:
            await runner.execute_run(new_run_id, req.prompt, cwd, resume_session_id=parent["session_id"])

    task = asyncio.create_task(_bounded_run())
    runner.track(new_run_id, task)
    return {"run_id": new_run_id, "parent_run_id": run_id, "status": "queued"}


@app.get("/triggers/{run_id}/log", response_class=PlainTextResponse, dependencies=[Depends(verify_token)])
async def get_trigger_log(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="not found")
    log_path = Path(run["log_path"])
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8")[-20000:]


@app.post("/triggers/{run_id}/stop", dependencies=[Depends(verify_token)])
async def stop_trigger(run_id: str, request: Request):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="not found")
    if run["status"] in store.TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail=f"run already finished (status={run['status']})")

    source_ip = request.client.host if request.client else "unknown"
    _audit(f"{time.time()} stop run_id={run_id} ip={source_ip}")

    cancelled = runner.stop_run(run_id)
    # 无论是否有活任务都直接落 stopped:
    # - 没有活任务(服务重启残留的僵尸行)时这是唯一的落点;
    # - 任务还排在信号量队列里(execute_run 未开始)时,取消不会经过 runner 的
    #   CancelledError 分支,同样只能靠这里落状态;
    # - 正在跑的任务,runner 的 CancelledError 分支也会写 stopped——set_status 对
    #   结束态有守卫(不覆盖已结束的行),两边谁先写都幂等,也不会把恰好抢先
    #   completed/failed 的 run 错标成 stopped。
    # 子进程由 SDK transport 的 close 逻辑 SIGTERM(宽限后 SIGKILL),真正停得下来。
    store.set_status(run_id, "stopped")
    return {"run_id": run_id, "status": "stopped", "cancelled_live_task": cancelled}


@app.post("/triggers/{run_id}/stream-ticket", dependencies=[Depends(verify_token)])
async def create_stream_ticket(run_id: str):
    """用 Bearer token 换一张短时一次性 ticket,给 EventSource(不能带自定义头)用。"""
    if not store.get_run(run_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ticket": auth.issue_stream_ticket(run_id), "expires_in": auth.STREAM_TICKET_TTL_SECONDS}


@app.get("/triggers/{run_id}/stream", dependencies=[Depends(verify_stream_access)])
async def stream_trigger_log(run_id: str, request: Request):
    """SSE:从头回放日志,然后跟随新行;run 进入结束态后发 end 事件并关闭。

    runner 把每条 SDK message 拍平成 JSONL 事件追加写进日志文件并 flush(旧 run 是
    repr 纯文本行,前端按"JSON 解析失败即纯文本"兜底),所以这里用最简单可靠的
    方式:轮询 tail 文件(1s 间隔),不引入新依赖。
    """
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="not found")
    log_path = Path(run["log_path"])

    async def _events():
        pos = 0
        pending = ""  # 半行缓冲:writer flush 时可能落下不完整的一行
        while True:
            # 先读状态再读文件:状态变结束态之前写入的行,一定能被本轮或下一轮读到,
            # 不会漏尾巴。
            current = store.get_run(run_id)
            status = current["status"] if current else "unknown"
            if log_path.exists():
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    pending += f.read()
                    pos = f.tell()
                *lines, pending = pending.split("\n")
                for line in lines:
                    yield f"event: log\ndata: {line}\n\n"
            if status in store.TERMINAL_STATUSES or current is None:
                if pending:
                    yield f"event: log\ndata: {pending}\n\n"
                yield f"event: end\ndata: {status}\n\n"
                return
            if await request.is_disconnected():
                return
            await asyncio.sleep(1.0)

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 防 nginx 类反代缓冲;Caddy 对 event-stream 自动不缓冲
        },
    )


# ---- P2:Web Push 订阅 -------------------------------------------------------


@app.get("/push/config", dependencies=[Depends(verify_token)])
async def push_config():
    """前端订阅前先问:push 是否启用 + VAPID 公钥(applicationServerKey)。"""
    return {"enabled": push.enabled(), "public_key": config.VAPID_PUBLIC_KEY or None}


@app.post("/push/subscriptions", dependencies=[Depends(verify_token)])
async def add_push_subscription(sub: PushSubscription):
    if not push.enabled():
        raise HTTPException(status_code=409, detail="push not configured on server")
    if not sub.endpoint.startswith("https://"):
        raise HTTPException(status_code=400, detail="endpoint must be https")
    if "p256dh" not in sub.keys or "auth" not in sub.keys:
        raise HTTPException(status_code=400, detail="keys must contain p256dh and auth")
    if store.count_push_subscriptions() >= config.MAX_PUSH_SUBSCRIPTIONS:
        raise HTTPException(status_code=429, detail="too many push subscriptions")
    store.upsert_push_subscription(sub.endpoint, {"endpoint": sub.endpoint, "keys": sub.keys})
    return {"ok": True}


@app.delete("/push/subscriptions", dependencies=[Depends(verify_token)])
async def delete_push_subscription(body: PushUnsubscribe):
    store.remove_push_subscription(body.endpoint)
    return {"ok": True}


# ---- P2:权限确认中继 --------------------------------------------------------


@app.post("/approvals/{approval_id}", dependencies=[Depends(verify_token)])
async def decide_approval(approval_id: str, body: ApprovalDecision, request: Request):
    """人工裁决灰区工具调用。404=不存在;409=已裁决/已过期(过期即已默认拒绝)。

    注意:黑名单命中的命令根本不会产生 approval(runner 判定顺序硬拒在前),
    所以这个端点不存在"放行黑名单命令"的能力。
    """
    approval = store.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="not found")

    source_ip = request.client.host if request.client else "unknown"
    status = approvals.resolve(approval_id, body.decision == "allow", source_ip)
    _audit(
        f"{time.time()} approval decision={body.decision} result={status or 'conflict'} "
        f"approval_id={approval_id} run_id={approval['run_id']} tool={approval['tool_name']} ip={source_ip}"
    )
    if status is None:
        raise HTTPException(
            status_code=409, detail=f"approval already settled (status={store.get_approval(approval_id)['status']})"
        )
    return {"approval_id": approval_id, "status": status}


# Web 面板静态文件(index.html/app.js/manifest.json/sw.js/icons)。挂在最后,
# 保证上面这些 API 路由优先匹配。
_web_dir = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")
