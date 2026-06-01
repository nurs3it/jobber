"""Локальное хранилище: per-dialog курсоры, seen-store (SQLite).

Всё в storage/ и в .gitignore. НИКОГДА не хранит секреты или содержимое CV — только
технические курсоры и хэши «уже видели».

  - cursor — последний обработанный message_id на диалог (для iter_new_messages).
  - seen   — множество (source, dialog_id, message_id) для точного дедупа.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.paths import data_dir

DB_PATH = data_dir("storage", "jobber.db")


class Store:
    """Фасад над SQLite для курсоров и seen-store."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS cursors ("
                "source TEXT, dialog_id TEXT, cursor TEXT, "
                "PRIMARY KEY (source, dialog_id))"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS seen ("
                "source TEXT, dialog_id TEXT, message_id TEXT, "
                "PRIMARY KEY (source, dialog_id, message_id))"
            )

    # --- курсоры ---

    def get_cursor(self, source: str, dialog_id: str) -> str | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT cursor FROM cursors WHERE source=? AND dialog_id=?",
                (source, dialog_id),
            ).fetchone()
        return row[0] if row else None

    def set_cursor(self, source: str, dialog_id: str, cursor: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO cursors (source, dialog_id, cursor) VALUES (?, ?, ?) "
                "ON CONFLICT(source, dialog_id) DO UPDATE SET cursor=excluded.cursor",
                (source, dialog_id, cursor),
            )

    # --- seen-store ---

    def is_seen(self, source: str, dialog_id: str, message_id: str) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM seen WHERE source=? AND dialog_id=? AND message_id=?",
                (source, dialog_id, message_id),
            ).fetchone()
        return row is not None

    def mark_seen(self, source: str, dialog_id: str, message_id: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO seen (source, dialog_id, message_id) VALUES (?, ?, ?)",
                (source, dialog_id, message_id),
            )

    def reset(self) -> None:
        """Сбросить курсоры и seen-store (для /seen-reset)."""
        with self._conn() as c:
            c.execute("DELETE FROM cursors")
            c.execute("DELETE FROM seen")
