import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, runner, store
from .auth import verify_token

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


def _audit(event: str) -> None:
    with open(config.AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(event + "\n")


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/config/projects", dependencies=[Depends(verify_token)])
async def list_projects():
    return {"projects": sorted(config.PROJECT_DIRS.keys())}


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

    asyncio.create_task(_bounded_run())
    return {"run_id": run_id, "status": "queued"}


@app.get("/triggers", dependencies=[Depends(verify_token)])
async def list_triggers():
    return store.list_runs()


@app.get("/triggers/{run_id}", dependencies=[Depends(verify_token)])
async def get_trigger(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="not found")
    return run


@app.get("/triggers/{run_id}/log", response_class=PlainTextResponse, dependencies=[Depends(verify_token)])
async def get_trigger_log(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="not found")
    log_path = Path(run["log_path"])
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8")[-20000:]


# Web 面板静态文件(index.html/app.js/manifest.json/sw.js/icons)。挂在最后,
# 保证上面这些 API 路由优先匹配。
_web_dir = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")
