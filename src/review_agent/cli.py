"""命令行启动入口。"""

from review_agent.config.settings import get_settings


def main() -> None:
    """启动本地开发服务。"""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "review_agent.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
