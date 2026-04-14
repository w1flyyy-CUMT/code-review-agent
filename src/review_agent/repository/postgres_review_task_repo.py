"""PostgreSQL 任务仓储实现。"""

from __future__ import annotations

from typing import Any

from psycopg import Connection, connect
from psycopg.types.json import Jsonb

from src.review_agent.common.errors import TaskNotFoundError
from src.review_agent.domain.models import ReviewTask


class PostgresReviewTaskRepository:
    """基于 PostgreSQL 的评审任务仓储。"""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._ensure_schema()

    def save(self, task: ReviewTask) -> None:
        """将任务快照写入 PostgreSQL。"""
        payload = task.model_dump(mode="json")

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO review_tasks (
                        task_id,
                        status,
                        risk_level,
                        approval_status,
                        created_at,
                        updated_at,
                        payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (task_id) DO UPDATE
                    SET
                        status = EXCLUDED.status,
                        risk_level = EXCLUDED.risk_level,
                        approval_status = EXCLUDED.approval_status,
                        updated_at = EXCLUDED.updated_at,
                        payload = EXCLUDED.payload
                    """,
                    (
                        task.task_id,
                        task.status.value,
                        task.risk_level.value,
                        task.approval_status.value,
                        task.created_at,
                        task.updated_at,
                        Jsonb(payload),
                    ),
                )
            conn.commit()

    def get(self, task_id: str) -> ReviewTask:
        """根据任务编号读取任务快照。"""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT payload FROM review_tasks WHERE task_id = %s",
                    (task_id,),
                )
                row = cursor.fetchone()

        if row is None:
            raise TaskNotFoundError(f"未找到评审任务：{task_id}")

        return ReviewTask.model_validate(row[0])

    def _ensure_schema(self) -> None:
        """确保任务表存在。"""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS review_tasks (
                        task_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        approval_status TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        payload JSONB NOT NULL
                    )
                    """,
                )
            conn.commit()

    def _connect(self) -> Connection[Any]:
        """创建数据库连接。"""
        return connect(self._dsn)
