"""配置加载测试。"""

from pathlib import Path
from typing import Any

from review_agent.config.settings import Settings


def test_settings_can_load_values_from_dotenv() -> None:
    env_dir = Path(__file__).resolve().parents[2] / ".tmp_test_settings"
    env_dir.mkdir(exist_ok=True)
    env_file = env_dir / ".env"
    env_file.write_text(
        "\n".join(
            [
                "REVIEW_AGENT_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/review_agent",
                "REVIEW_AGENT_DASHSCOPE_MODEL=qwen-max",
                "REVIEW_AGENT_DASHSCOPE_TIMEOUT_SECONDS=45",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(**cast_env_file_arg(env_file))

    assert settings.database_url == "postgresql://postgres:postgres@127.0.0.1:5432/review_agent"
    assert settings.dashscope_model == "qwen-max"
    assert settings.dashscope_timeout_seconds == 45


def test_settings_can_load_values_from_env_example() -> None:
    env_file = Path(__file__).resolve().parents[2] / ".env.example"

    settings = Settings(**cast_env_file_arg(env_file))

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.database_url == "postgresql://postgres:postgres@127.0.0.1:5432/review_agent"
    assert settings.dashscope_model == "qwen-plus"
    assert settings.dashscope_timeout_seconds == 30


def cast_env_file_arg(env_file: Path) -> dict[str, Any]:
    """为类型检查器提供 BaseSettings 专用构造参数。"""
    return {"_env_file": env_file}
