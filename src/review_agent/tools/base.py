"""工具基础模型。"""

from pathlib import Path

from pydantic import BaseModel, Field


class ToolExecutionRequest(BaseModel):
    """工具执行请求。"""

    repo_path: Path
    targets: list[str] = Field(default_factory=list)
    timeout_seconds: int = 30
