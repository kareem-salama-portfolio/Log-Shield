"""SQLite connections and transaction management."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class ClosingConnection(sqlite3.Connection):
    """Connection context manager that also releases its file handle."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, factory=ClosingConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.executescript(schema)
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(incidents)")
            }
            if "status_updated_at" not in columns:
                connection.execute(
                    "ALTER TABLE incidents ADD COLUMN status_updated_at TEXT NOT NULL DEFAULT ''"
                )
            connection.execute(
                "UPDATE incidents SET status_updated_at=? WHERE status_updated_at=''",
                (__import__("datetime").datetime.now().isoformat(timespec="seconds"),),
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
