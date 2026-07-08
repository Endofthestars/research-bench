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

# ---- P2:权限确认中继 -------------------------------------------------------
# 灰区:黑名单之外、但影响不可逆或出站的 Bash 命令,执行前挂起等人工确认。
# 划分依据(最小集合,不把日常命令变成交互式):
#   1) 不可逆删除(rm -rf/-fr,根目录变体已在黑名单里硬拒);
#   2) 向远端发布(git push,--force 变体已在黑名单里硬拒);
#   3) 供应链引入(包管理器 install/add,远程代码进入执行环境)。
# 其余命令维持原策略(直接放行)——确认中继是在"允许"之上加的安全增强,
# 黑名单命中的硬拒绝路径永远优先、永远不进确认(见 runner.py 的判定顺序)。
# 可用 REMOTE_CONTROL_CONFIRM_BASH_PATTERNS 覆盖(";;" 分隔的正则;设为空串则
# 关闭确认中继,回到 P1 行为)。
_confirm_raw = os.environ.get(
    "REMOTE_CONTROL_CONFIRM_BASH_PATTERNS",
    r"rm\s+-[a-z]*[rf][a-z]*[rf][a-z]*\s"
    r";;\bgit\s+push\b"
    r";;\b(pip3?|npm|pnpm|yarn|uv|conda|apt(-get)?)\s+(install|add)\b",
)
CONFIRM_BASH_PATTERNS = [p for p in (s.strip() for s in _confirm_raw.split(";;")) if p]

# 确认等待超时:到点没人裁决就默认拒绝(保守缺省)。
APPROVAL_TIMEOUT_SECONDS = int(os.environ.get("REMOTE_CONTROL_APPROVAL_TIMEOUT_SECONDS", "120"))

# ---- P2:Web Push(VAPID) --------------------------------------------------
# 三个都配齐(且装了 pywebpush)才启用推送;缺任何一个则整个 push 功能静默关闭,
# 其余功能不受影响。生成方法见 deploy/.env.example 注释。
VAPID_PRIVATE_KEY = os.environ.get("REMOTE_CONTROL_VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("REMOTE_CONTROL_VAPID_PUBLIC_KEY", "")
VAPID_SUBJECT = os.environ.get("REMOTE_CONTROL_VAPID_SUBJECT", "")  # 形如 mailto:you@example.com

# 订阅数量上限:防止 token 泄露后被灌垃圾订阅撑爆存储/推送风暴。
MAX_PUSH_SUBSCRIPTIONS = int(os.environ.get("REMOTE_CONTROL_MAX_PUSH_SUBSCRIPTIONS", "20"))


# ---- P3:research-bench 集成 ------------------------------------------------
def _load_presets() -> list[dict[str, str]]:
    """解析 REMOTE_CONTROL_PRESETS="label1=prompt1;;label2=prompt2"。

    前端把这些渲染成"填充输入框"的按钮(点击只填充、不直接提交,保留人工确认
    一步),方便常用的 research-bench 斜杠命令一键带出。未配置则不显示。
    """
    raw = os.environ.get("REMOTE_CONTROL_PRESETS", "")
    presets: list[dict[str, str]] = []
    for item in raw.split(";;"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        label, prompt = item.split("=", 1)
        label, prompt = label.strip(), prompt.strip()
        if label and prompt:
            presets.append({"label": label, "prompt": prompt})
    return presets


PRESETS: list[dict[str, str]] = _load_presets()


def _load_probe_files() -> dict[str, Path]:
    """解析 REMOTE_CONTROL_PROBE_FILES="name1=/path/a.json;;name2=/path/b.json"。

    白名单式:只有 env 里显式登记的探针文件可被读取,请求方无法指定任意路径
    (与 PROJECT_DIRS 同一道防线)。这是 DESIGN §3.2 探针-看门狗设计的只读查看端,
    服务绝不写探针文件。
    """
    raw = os.environ.get("REMOTE_CONTROL_PROBE_FILES", "")
    probes: dict[str, Path] = {}
    for item in raw.split(";;"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        name, path_str = item.split("=", 1)
        name = name.strip()
        if name:
            probes[name] = Path(path_str.strip()).resolve()
    return probes


PROBE_FILES: dict[str, Path] = _load_probe_files()

# 探针心跳判新旧的年龄阈值(秒);前端据此标色。
PROBE_STALE_SECONDS = int(os.environ.get("REMOTE_CONTROL_PROBE_STALE_SECONDS", "300"))

# 单个探针文件读取上限(字节),防被超大文件撑爆内存。
PROBE_MAX_BYTES = int(os.environ.get("REMOTE_CONTROL_PROBE_MAX_BYTES", "65536"))
