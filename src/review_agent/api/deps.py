"""API 依赖注入。"""

from functools import lru_cache
from typing import Any

from fastapi import HTTPException, status

from review_agent.agent.graph import build_resume_graph, build_review_graph
from review_agent.application.approval_service import ApprovalService
from review_agent.application.review_service import ReviewService
from review_agent.config.settings import get_settings
from review_agent.repository.postgres_review_task_repo import PostgresReviewTaskRepository
from review_agent.repository.review_task_repo import ReviewTaskRepository


@lru_cache
def get_review_repository() -> ReviewTaskRepository:
    """返回全局仓储实例。"""
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未配置 PostgreSQL 连接，请设置 REVIEW_AGENT_DATABASE_URL。",
        )
    return PostgresReviewTaskRepository(settings.database_url)


@lru_cache
def get_review_graph() -> Any:
    """返回首次评审图。"""
    return build_review_graph()


@lru_cache
def get_resume_graph() -> Any:
    """返回审批恢复图。"""
    return build_resume_graph()


@lru_cache
def get_review_service() -> ReviewService:
    """返回评审服务实例。"""
    return ReviewService(
        repository=get_review_repository(),
        graph=get_review_graph(),
    )


@lru_cache
def get_approval_service() -> ApprovalService:
    """返回审批服务实例。"""
    return ApprovalService(
        repository=get_review_repository(),
        resume_graph=get_resume_graph(),
    )
