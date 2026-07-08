import json
import sqlite3
import time
import uuid

from . import config

# 结束态集合:进入其中任何一个后 run 不再变化(stop 端点对这些状态返回 409)。
TERMINAL_STATUSES = ("completed", "failed", "stopped")

# 幂等迁移:老库文件缺这些列时启动补上(ALTER TABLE ADD COLUMN),新库直接建全。
_MIGRATION_COLUMNS = {
    "duration_seconds": "REAL",
    "total_cost_usd": "REAL",
    "num_turns": "INTEGER",
    "usage_json": "TEXT",
    "session_id": "TEXT",
    "parent_run_id": "TEXT",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                project_key TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                started_at REAL,
                finished_at REAL,
                log_path TEXT NOT NULL,
                error TEXT,
                source_ip TEXT,
                duration_seconds REAL,
                total_cost_usd REAL,
                num_turns INTEGER,
                usage_json TEXT,
                session_id TEXT,
                parent_run_id TEXT
            )
            """
        )
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
        for column, col_type in _MIGRATION_COLUMNS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE runs ADD COLUMN {column} {col_type}")
        # P2 新表:CREATE IF NOT EXISTS 本身就是幂等迁移。
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                endpoint TEXT PRIMARY KEY,
                subscription_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_approvals (
                approval_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                input_preview TEXT,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                decided_at REAL,
                decided_by TEXT
            )
            """
        )


def create_run(project_key: str, prompt: str, source_ip: str, parent_run_id: str | None = None) -> str:
    run_id = uuid.uuid4().hex[:12]
    log_path = str(config.LOG_DIR / f"{run_id}.log")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO runs (run_id, project_key, prompt, status, created_at, log_path, source_ip, parent_run_id) "
            "VALUES (?, ?, ?, 'queued', ?, ?, ?, ?)",
            (run_id, project_key, prompt, time.time(), log_path, source_ip, parent_run_id),
        )
    return run_id


def set_session_id(run_id: str, session_id: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE runs SET session_id=? WHERE run_id=?", (session_id, run_id))


def list_children(run_id: str) -> list[str]:
    """对话链的直接后继(continue 出来的 run),按创建时间排序。"""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT run_id FROM runs WHERE parent_run_id=? ORDER BY created_at", (run_id,)
        ).fetchall()
        return [r["run_id"] for r in rows]


def set_status(run_id: str, status: str, error: str | None = None) -> None:
    now = time.time()
    with _connect() as conn:
        if status == "running":
            conn.execute("UPDATE runs SET status=?, started_at=? WHERE run_id=?", (status, now, run_id))
        elif status in TERMINAL_STATUSES:
            # duration 以 started_at 为基准(没跑起来就被停的用 created_at 兜底);
            # WHERE 里排除已是结束态的行,避免 stop 端点和 runner 的取消回调二次覆盖。
            conn.execute(
                "UPDATE runs SET status=?, finished_at=?, error=?, "
                "duration_seconds = ? - COALESCE(started_at, created_at) "
                "WHERE run_id=? AND status NOT IN ('completed', 'failed', 'stopped')",
                (status, now, error, now, run_id),
            )
        else:
            conn.execute("UPDATE runs SET status=? WHERE run_id=?", (status, run_id))


def set_result_meta(
    run_id: str,
    total_cost_usd: float | None = None,
    num_turns: int | None = None,
    usage: dict | None = None,
) -> None:
    """记录 SDK ResultMessage 里的用量信息(没有 ResultMessage 的 run 这些字段保持 NULL)。"""
    with _connect() as conn:
        conn.execute(
            "UPDATE runs SET total_cost_usd=?, num_turns=?, usage_json=? WHERE run_id=?",
            (total_cost_usd, num_turns, json.dumps(usage) if usage else None, run_id),
        )


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    raw = d.pop("usage_json", None)
    try:
        d["usage"] = json.loads(raw) if raw else None
    except ValueError:
        d["usage"] = None
    return d


def get_run(run_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return _row_to_dict(row) if row else None


def list_runs(limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def count_active() -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM runs WHERE status IN ('queued', 'running')"
        ).fetchone()
        return row["c"]


# ---- P2:Web Push 订阅 -------------------------------------------------------


def upsert_push_subscription(endpoint: str, subscription: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO push_subscriptions (endpoint, subscription_json, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(endpoint) DO UPDATE SET subscription_json=excluded.subscription_json",
            (endpoint, json.dumps(subscription), time.time()),
        )


def remove_push_subscription(endpoint: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint=?", (endpoint,))


def list_push_subscriptions() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT endpoint, subscription_json FROM push_subscriptions").fetchall()
    subs = []
    for r in rows:
        try:
            subs.append({"endpoint": r["endpoint"], "subscription": json.loads(r["subscription_json"])})
        except ValueError:
            continue
    return subs


def count_push_subscriptions() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM push_subscriptions").fetchone()["c"]


# ---- P2:权限确认中继 --------------------------------------------------------


def create_approval(approval_id: str, run_id: str, tool_name: str, input_preview: str, expires_at: float) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO pending_approvals (approval_id, run_id, tool_name, input_preview, status, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, 'pending', ?, ?)",
            (approval_id, run_id, tool_name, input_preview, time.time(), expires_at),
        )


def get_approval(approval_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM pending_approvals WHERE approval_id=?", (approval_id,)).fetchone()
        return dict(row) if row else None


def finalize_approval(approval_id: str, status: str, decided_by: str | None) -> bool:
    """把 pending 的确认请求落成 allowed/denied/expired。守卫:只有 pending 能被裁决;
    返回是否真的完成了状态迁移(False = 已被裁决过/已过期,调用方按 409 处理)。"""
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE pending_approvals SET status=?, decided_at=?, decided_by=? "
            "WHERE approval_id=? AND status='pending'",
            (status, time.time(), decided_by, approval_id),
        )
        return cur.rowcount == 1
