import sqlite3
import time
import uuid

from . import config


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
                source_ip TEXT
            )
            """
        )


def create_run(project_key: str, prompt: str, source_ip: str) -> str:
    run_id = uuid.uuid4().hex[:12]
    log_path = str(config.LOG_DIR / f"{run_id}.log")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO runs (run_id, project_key, prompt, status, created_at, log_path, source_ip) "
            "VALUES (?, ?, ?, 'queued', ?, ?, ?)",
            (run_id, project_key, prompt, time.time(), log_path, source_ip),
        )
    return run_id


def set_status(run_id: str, status: str, error: str | None = None) -> None:
    now = time.time()
    with _connect() as conn:
        if status == "running":
            conn.execute("UPDATE runs SET status=?, started_at=? WHERE run_id=?", (status, now, run_id))
        elif status in ("completed", "failed"):
            conn.execute(
                "UPDATE runs SET status=?, finished_at=?, error=? WHERE run_id=?",
                (status, now, error, run_id),
            )
        else:
            conn.execute("UPDATE runs SET status=? WHERE run_id=?", (status, run_id))


def get_run(run_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None


def list_runs(limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def count_active() -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM runs WHERE status IN ('queued', 'running')"
        ).fetchone()
        return row["c"]
