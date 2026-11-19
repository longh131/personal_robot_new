# -*- coding: utf-8 -*-
"""Long-term facts in SQLite. Short-term dialogue stays in the talk loop.

Not a chat log. Facts are typed, timestamped, upserted, and can be invalidated.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from settings import robot_get

log = logging.getLogger("awake.memory")

DB_PATH = Path("/opt/personal_robot/data/memory/facts.sqlite")
SCHEMA = 1
_QUESTION = ("吗", "呢", "啥", "什么", "幾", "几", "？", "?")
_WRITE_HINTS = (
    "记住",
    "记得",
    "别忘",
    "我喜欢",
    "我愛",
    "我爱喝",
    "我爱吃",
    "不加",
    "不要加",
    "过敏",
    "我叫",
    "以后叫",
    "我是",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def should_extract(text: str) -> bool:
    raw = text or ""
    if any(q in raw for q in _QUESTION):
        return False
    return any(h in raw for h in _WRITE_HINTS)


class Store:
    def __init__(self, path: Path = DB_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self) -> None:
        ver = int(self._db.execute("PRAGMA user_version").fetchone()[0])
        if ver >= SCHEMA:
            return
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS facts (
              id INTEGER PRIMARY KEY,
              kind TEXT NOT NULL,
              key TEXT NOT NULL,
              value TEXT NOT NULL,
              text TEXT NOT NULL,
              salience REAL NOT NULL DEFAULT 1.0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              source TEXT,
              valid INTEGER NOT NULL DEFAULT 1,
              UNIQUE(kind, key)
            );
            CREATE INDEX IF NOT EXISTS facts_kind ON facts(kind);
            CREATE INDEX IF NOT EXISTS facts_valid ON facts(valid);
            """
        )
        self._db.execute(f"PRAGMA user_version={SCHEMA}")
        self._db.commit()

    def upsert(
        self,
        *,
        kind: str,
        key: str,
        value: str,
        text: str,
        source: str = "",
        salience: float = 1.0,
    ) -> None:
        kind = _slug(kind) or "other"
        key = _slug(key) or "note"
        value = (value or "").strip()
        text = (text or value).strip()
        if not value:
            return
        now = _now()
        self._db.execute(
            """
            INSERT INTO facts(kind, key, value, text, salience, created_at, updated_at, source, valid)
            VALUES(?,?,?,?,?,?,?,?,1)
            ON CONFLICT(kind, key) DO UPDATE SET
              value=excluded.value,
              text=excluded.text,
              salience=excluded.salience,
              updated_at=excluded.updated_at,
              source=excluded.source,
              valid=1
            """,
            (kind, key, value, text, float(salience), now, now, (source or "")[:200]),
        )
        self._db.commit()
        log.info("memory upsert kind=%s key=%s", kind, key)

    def get(self, kind: str, key: str) -> sqlite3.Row | None:
        row = self._db.execute(
            "SELECT * FROM facts WHERE kind=? AND key=? AND valid=1",
            (_slug(kind), _slug(key)),
        ).fetchone()
        return row

    def forget(self, kind: str, key: str) -> bool:
        cur = self._db.execute(
            "UPDATE facts SET valid=0, updated_at=? WHERE kind=? AND key=? AND valid=1",
            (_now(), _slug(kind), _slug(key)),
        )
        self._db.commit()
        return cur.rowcount > 0

    def list_valid(self, limit: int = 12) -> list[sqlite3.Row]:
        limit = max(1, min(50, int(limit)))
        return list(
            self._db.execute(
                "SELECT * FROM facts WHERE valid=1 ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
        )

    def search_valid(self, query: str, limit: int = 8) -> list[sqlite3.Row]:
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{2,}", query or "")
        if not tokens:
            return self.list_valid(limit)
        seen: set[int] = set()
        rows: list[sqlite3.Row] = []
        for tok in tokens[:6]:
            like = f"%{tok}%"
            for row in self._db.execute(
                "SELECT * FROM facts WHERE valid=1 AND (text LIKE ? OR value LIKE ? OR key LIKE ?) LIMIT 8",
                (like, like, like),
            ):
                rid = int(row["id"])
                if rid not in seen:
                    seen.add(rid)
                    rows.append(row)
        return rows[:limit]

    def prompt_block(self, query: str = "") -> str:
        limit = int(robot_get("memory", "prompt_limit", default=20) or 20)
        rows: list[sqlite3.Row] = []
        seen: set[int] = set()
        for row in self._db.execute(
            "SELECT * FROM facts WHERE valid=1 AND kind='preference' ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ):
            seen.add(int(row["id"]))
            rows.append(row)
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{2,}", query or "")
        for tok in tokens[:6]:
            like = f"%{tok}%"
            for row in self._db.execute(
                "SELECT * FROM facts WHERE valid=1 AND (text LIKE ? OR value LIKE ? OR key LIKE ?) LIMIT 8",
                (like, like, like),
            ):
                rid = int(row["id"])
                if rid not in seen:
                    seen.add(rid)
                    rows.append(row)
        if len(rows) < min(8, limit):
            for row in self._db.execute(
                "SELECT * FROM facts WHERE valid=1 ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ):
                rid = int(row["id"])
                if rid not in seen:
                    seen.add(rid)
                    rows.append(row)
        rows = rows[:limit]
        if not rows:
            return ""
        lines = [
            f"- {r['text']}（{r['kind']}/{r['key']}，{r['updated_at'][:10]}）" for r in rows
        ]
        return "已知关于主人的长期事实：\n" + "\n".join(lines)


def _slug(raw: str) -> str:
    s = re.sub(r"\s+", "_", (raw or "").strip().lower())
    s = re.sub(r"[^a-z0-9_\u4e00-\u9fff]+", "", s)
    return s[:64]


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store
