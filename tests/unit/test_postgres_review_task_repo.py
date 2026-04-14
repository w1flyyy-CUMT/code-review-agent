"""PostgreSQL 任务仓储测试。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from psycopg.types.json import Jsonb

from review_agent.common.errors import TaskNotFoundError
from review_agent.domain.enums import ApprovalStatus, RiskLevel, TaskStatus
from review_agent.domain.models import ReviewTask
from review_agent.repository.postgres_review_task_repo import PostgresReviewTaskRepository


class FakeCursor:
    """模拟数据库游标。"""

    def __init__(self, row: tuple[dict[str, Any]] | None = None) -> None:
        self.row = row
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> tuple[dict[str, Any]] | None:
        return self.row

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class FakeConnection:
    """模拟数据库连接。"""

    def __init__(self, row: tuple[dict[str, Any]] | None = None) -> None:
        self.cursor_instance = FakeCursor(row=row)
        self.committed = False

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


def _build_task() -> ReviewTask:
    now = datetime(2026, 4, 14, tzinfo=UTC)
    return ReviewTask(
        task_id="rvw_pg_001",
        repo_path="D:/demo/repo",
        diff_text="diff --git a/a.py b/a.py",
        status=TaskStatus.COMPLETED,
        risk_level=RiskLevel.LOW,
        approval_status=ApprovalStatus.NOT_REQUIRED,
        trace_id="trace_pg_001",
        created_at=now,
        updated_at=now,
    )


def test_postgres_repository_save_persists_json_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    init_conn = FakeConnection()
    save_conn = FakeConnection()
    connections = iter([init_conn, save_conn])

    monkeypatch.setattr(
        "review_agent.repository.postgres_review_task_repo.connect",
        lambda dsn: next(connections),
    )

    repository = PostgresReviewTaskRepository("postgresql://demo")
    task = _build_task()
    repository.save(task)

    assert init_conn.committed is True
    assert save_conn.committed is True
    save_query, save_params = save_conn.cursor_instance.executed[0]
    assert "INSERT INTO review_tasks" in save_query
    assert save_params is not None
    assert save_params[0] == "rvw_pg_001"
    assert save_params[1] == "completed"
    assert isinstance(save_params[6], Jsonb)


def test_postgres_repository_get_restores_review_task(monkeypatch: pytest.MonkeyPatch) -> None:
    task = _build_task()
    payload = task.model_dump(mode="json")
    init_conn = FakeConnection()
    get_conn = FakeConnection(row=(payload,))
    connections = iter([init_conn, get_conn])

    monkeypatch.setattr(
        "review_agent.repository.postgres_review_task_repo.connect",
        lambda dsn: next(connections),
    )

    repository = PostgresReviewTaskRepository("postgresql://demo")
    restored = repository.get(task.task_id)

    assert restored.task_id == task.task_id
    assert restored.trace_id == task.trace_id
    assert get_conn.cursor_instance.executed[0][1] == (task.task_id,)


def test_postgres_repository_get_raises_when_task_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_conn = FakeConnection()
    get_conn = FakeConnection(row=None)
    connections = iter([init_conn, get_conn])

    monkeypatch.setattr(
        "review_agent.repository.postgres_review_task_repo.connect",
        lambda dsn: next(connections),
    )

    repository = PostgresReviewTaskRepository("postgresql://demo")

    with pytest.raises(TaskNotFoundError):
        repository.get("missing-task")
