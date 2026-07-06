import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("REMOTE_CONTROL_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "runs.db"
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG_PATH = DATA_DIR / "audit.log"

BEARER_TOKEN = os.environ.get("REMOTE_CONTROL_TOKEN")
if not BEARER_TOKEN:
    raise RuntimeError("REMOTE_CONTROL_TOKEN 环境变量未设置,拒绝启动(不允许无鉴权对外提供服务)")


def _load_project_dirs() -> dict[str, Path]:
    """解析 REMOTE_CONTROL_PROJECT_DIRS="key1=/path/one,key2=/path/two"。

    客户端只能传 key,不能传任意路径——这是防止触发接口被用来对整台服务器
    做任意目录操作的第一道白名单闸门。
    """
    raw = os.environ.get("REMOTE_CONTROL_PROJECT_DIRS", "")
    projects: dict[str, Path] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise RuntimeError(f"REMOTE_CONTROL_PROJECT_DIRS 格式错误,缺少 '=': {item!r}")
        key, path_str = item.split("=", 1)
        key = key.strip()
        path = Path(path_str.strip()).resolve()
        if not path.is_dir():
            raise RuntimeError(f"project_dir 不存在或不是目录: {path}")
        projects[key] = path
    if not projects:
        raise RuntimeError("REMOTE_CONTROL_PROJECT_DIRS 未配置任何允许触发的目录,拒绝启动")
    return projects


PROJECT_DIRS: dict[str, Path] = _load_project_dirs()

MAX_CONCURRENT_RUNS = int(os.environ.get("REMOTE_CONTROL_MAX_CONCURRENT", "2"))
RUN_TIMEOUT_SECONDS = int(os.environ.get("REMOTE_CONTROL_TIMEOUT_SECONDS", "1800"))
MAX_TURNS = int(os.environ.get("REMOTE_CONTROL_MAX_TURNS", "40"))
MAX_BUDGET_USD = float(os.environ.get("REMOTE_CONTROL_MAX_BUDGET_USD", "2.0"))
RATE_LIMIT_PER_MINUTE = int(os.environ.get("REMOTE_CONTROL_RATE_LIMIT_PER_MINUTE", "10"))

# 权限上限:写死在代码里,不作为 API 可调参数,杜绝客户端把它升级成
# bypassPermissions/dontAsk/auto。TriggerRequest 里也不暴露这个字段。
FIXED_PERMISSION_MODE = "acceptEdits"

# can_use_tool 里额外拦截的高危 Bash 命令特征(和插件里 guard-train-channel.sh /
# guard-protected-write.sh 的思路一致:黑名单拦截明显危险操作,而不是假设 SDK 权限模式够用)。
DANGEROUS_BASH_PATTERNS = [
    r"rm\s+-rf\s+/(\s|$)",
    r"\bsudo\b",
    r"curl[^|]*\|\s*(ba)?sh",
    r"wget[^|]*\|\s*(ba)?sh",
    r"git\s+push\s+[^\n]*--force",
    r":\(\)\s*\{\s*:\|\:&\s*\}\s*;\s*:",
    r"mkfs\.",
    r">\s*/dev/sd",
    r"\bshutdown\b|\breboot\b|\bhalt\b",
]
