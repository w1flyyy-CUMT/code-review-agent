"""FastAPI 应用入口。"""

from fastapi import FastAPI

from review_agent.api.routes_approvals import router as approvals_router
from review_agent.api.routes_health import router as health_router
from review_agent.api.routes_reviews import router as reviews_router
from review_agent.config.logging import configure_logging
from review_agent.config.settings import get_settings


def create_app() -> FastAPI:
    """创建应用实例。"""
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="面向 Git Diff 的智能代码评审 Agent",
    )
    app.include_router(approvals_router)
    app.include_router(health_router)
    app.include_router(reviews_router)
    return app


app = create_app()
