from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    automation_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    error_type TEXT,
    error_message TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_executions_name_started
    ON executions (automation_name, started_at);
CREATE INDEX IF NOT EXISTS idx_executions_status ON executions (status);
"""


@dataclass(frozen=True)
class Execution:
    id: str
    automation_name: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    error_type: str | None
    error_message: str | None
    metadata: dict[str, Any]

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()


@dataclass(frozen=True)
class Summary:
    total: int
    successful: int
    failed: int
    running: int
    average_duration_seconds: float | None

    @property
    def success_rate(self) -> float:
        completed = self.successful + self.failed
        return self.successful / completed if completed else 0.0


class AutomationMonitor:
    """Registra execuções de automações em uma base SQLite."""

    def __init__(self, database: str = "automation_monitor.db") -> None:
        self.database = database
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _serialize(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Execution:
        return Execution(
            id=row["id"],
            automation_name=row["automation_name"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            status=row["status"],
            error_type=row["error_type"],
            error_message=row["error_message"],
            metadata=json.loads(row["metadata"]),
        )

    def start(self, automation_name: str, metadata: dict[str, Any] | None = None) -> str:
        if not automation_name.strip():
            raise ValueError("automation_name não pode ser vazio")
        execution_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO executions (id, automation_name, started_at, status, metadata) "
                "VALUES (?, ?, ?, 'running', ?)",
                (execution_id, automation_name, self._serialize(self._now()), json.dumps(metadata or {})),
            )
        return execution_id

    def finish(self, execution_id: str, status: str = "success", error: BaseException | None = None) -> Execution:
        if status not in {"success", "failed"}:
            raise ValueError("status deve ser 'success' ou 'failed'")
        if status == "failed" and error is None:
            error_type, error_message = "Failure", "Execução marcada como falha"
        elif error is not None:
            error_type, error_message = type(error).__name__, str(error)
        else:
            error_type = error_message = None
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE executions SET finished_at = ?, status = ?, error_type = ?, error_message = ? "
                "WHERE id = ? AND status = 'running'",
                (self._serialize(self._now()), status, error_type, error_message, execution_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"execução inexistente ou já finalizada: {execution_id}")
            row = connection.execute("SELECT * FROM executions WHERE id = ?", (execution_id,)).fetchone()
        return self._from_row(row)

    def get(self, execution_id: str) -> Execution:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM executions WHERE id = ?", (execution_id,)).fetchone()
        if row is None:
            raise ValueError(f"execução não encontrada: {execution_id}")
        return self._from_row(row)

    @contextmanager
    def track(self, automation_name: str, metadata: dict[str, Any] | None = None) -> Iterator[str]:
        execution_id = self.start(automation_name, metadata)
        try:
            yield execution_id
        except BaseException as error:
            self.finish(execution_id, status="failed", error=error)
            raise
        else:
            self.finish(execution_id)

    def summary(self, automation_name: str | None = None, since: datetime | None = None) -> Summary:
        clauses: list[str] = []
        parameters: list[str] = []
        if automation_name:
            clauses.append("automation_name = ?")
            parameters.append(automation_name)
        if since:
            clauses.append("started_at >= ?")
            parameters.append(self._serialize(since))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful, "
                "SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed, "
                "SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running, "
                "AVG(CASE WHEN finished_at IS NOT NULL THEN "
                "(julianday(finished_at) - julianday(started_at)) * 86400 END) "
                f"AS average_duration FROM executions {where}", parameters
            ).fetchone()
        return Summary(row["total"] or 0, row["successful"] or 0, row["failed"] or 0,
                       row["running"] or 0, row["average_duration"])

    def recent(self, limit: int = 20) -> list[Execution]:
        if limit < 1:
            raise ValueError("limit deve ser maior que zero")
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM executions ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._from_row(row) for row in rows]


def since_days(days: int) -> datetime:
    if days < 0:
        raise ValueError("days não pode ser negativo")
    return datetime.now(timezone.utc) - timedelta(days=days)