import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import aiosqlite


@dataclass(frozen=True)
class AuditRecord:
    user_id: int
    question: str
    sql: str | None
    result: str | None
    success: bool
    error: str | None
    language: str | None = None


class AuditRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    role TEXT NOT NULL,
                    added_by INTEGER,
                    created_at TEXT NOT NULL
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    sql TEXT,
                    result TEXT,
                    success INTEGER NOT NULL,
                    error TEXT,
                    language TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            await conn.commit()

    async def upsert_user(self, user_id: int, role: str, added_by: int | None) -> None:
        created_at = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, role, added_by, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET role=excluded.role
                """,
                (user_id, role, added_by, created_at),
            )
            await conn.commit()

    async def remove_user(self, user_id: int) -> bool:
        async with aiosqlite.connect(self._db_path) as conn:
            cursor = await conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await conn.commit()
            return cursor.rowcount > 0

    async def list_user_ids(self, role: str | None = None) -> list[int]:
        async with aiosqlite.connect(self._db_path) as conn:
            if role:
                cursor = await conn.execute(
                    "SELECT user_id FROM users WHERE role = ? ORDER BY user_id ASC",
                    (role,),
                )
            else:
                cursor = await conn.execute("SELECT user_id FROM users ORDER BY user_id ASC")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_user_role(self, user_id: int) -> str | None:
        async with aiosqlite.connect(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT role FROM users WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def is_user(self, user_id: int) -> bool:
        async with aiosqlite.connect(self._db_path) as conn:
            cursor = await conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row is not None

    async def is_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT 1 FROM users WHERE user_id = ? AND role = 'admin'", (user_id,)
            )
            row = await cursor.fetchone()
            return row is not None

    async def record_audit(self, record: AuditRecord) -> None:
        created_at = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO audits (
                    user_id, question, sql, result, success, error, language, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.user_id,
                    record.question,
                    record.sql,
                    record.result,
                    1 if record.success else 0,
                    record.error,
                    record.language,
                    created_at,
                ),
            )
            await conn.commit()

    @staticmethod
    def serialize_result(data: Any) -> str:
        return json.dumps(data, ensure_ascii=True, default=str)
