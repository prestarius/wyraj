"""Run history in SQLite: every run remembered, statistics later."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from wyraj.persistence.paths import wyraj_home

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    seed INTEGER NOT NULL,
    origin TEXT NOT NULL,
    turns INTEGER NOT NULL,
    max_depth INTEGER NOT NULL,
    cause TEXT NOT NULL
)
"""


class RunRecord(NamedTuple):
    ts: str
    seed: int
    origin: str
    turns: int
    max_depth: int
    cause: str


def history_path() -> Path:
    return wyraj_home() / "history.db"


def record_run(
    *,
    seed: int,
    origin: str,
    turns: int,
    max_depth: int,
    cause: str,
    when: datetime,
    db_path: Path | None = None,
) -> None:
    target = db_path or history_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as conn:
        conn.execute(_SCHEMA)
        conn.execute(
            "INSERT INTO runs (ts, seed, origin, turns, max_depth, cause)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (when.isoformat(timespec="seconds"), seed, origin, turns, max_depth, cause),
        )


def recent_runs(limit: int = 10, db_path: Path | None = None) -> list[RunRecord]:
    target = db_path or history_path()
    if not target.exists():
        return []
    with sqlite3.connect(target) as conn:
        rows = conn.execute(
            "SELECT ts, seed, origin, turns, max_depth, cause FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [RunRecord(*row) for row in rows]
