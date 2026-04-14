"""API 依赖注入测试。"""

from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException

from review_agent.api import deps
from review_agent.domain.models import ReviewTask


class FakeRepository:
    """用于依赖注入测试的假仓储。"""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def save(self, task: ReviewTask) -> None:
        """满足仓储协议。"""

    def get(self, task_id: str) -> ReviewTask:
        """满足仓储协议。"""
        raise NotImplementedError


def test_get_review_repository_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    deps.get_review_repository.cache_clear()
    monkeypatch.setattr(
        deps,
        "get_settings",
        lambda: SimpleNamespace(database_url=None),
    )

    with pytest.raises(HTTPException) as exc_info:
        deps.get_review_repository()

    assert exc_info.value.status_code == 500
    assert "REVIEW_AGENT_DATABASE_URL" in str(exc_info.value.detail)


def test_get_review_repository_builds_postgres_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deps.get_review_repository.cache_clear()
    monkeypatch.setattr(
        deps,
        "get_settings",
        lambda: SimpleNamespace(database_url="postgresql://demo"),
    )
    monkeypatch.setattr(
        deps,
        "PostgresReviewTaskRepository",
        FakeRepository,
    )

    repository = cast(FakeRepository, deps.get_review_repository())

    assert repository.dsn == "postgresql://demo"
