"""任务仓储抽象与内存实现。"""

from __future__ import annotations

from typing import Protocol

from review_agent.common.errors import TaskNotFoundError
from review_agent.domain.models import ReviewTask


class ReviewTaskRepository(Protocol):
    """评审任务仓储契约。"""

    def save(self, task: ReviewTask) -> None:
        """保存任务。"""

    def get(self, task_id: str) -> ReviewTask:
        """根据任务编号获取任务。"""


class InMemoryReviewTaskRepository:
    """基于内存的任务仓储。

    当前实现主要用于测试或本地隔离场景。
    """

    def __init__(self) -> None:
        self._tasks: dict[str, ReviewTask] = {}

    def save(self, task: ReviewTask) -> None:
        """保存任务。"""
        self._tasks[task.task_id] = task

    def get(self, task_id: str) -> ReviewTask:
        """根据任务编号获取任务。"""
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise TaskNotFoundError(f"未找到评审任务：{task_id}") from exc
