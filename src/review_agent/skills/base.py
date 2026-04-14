"""Skill 基础契约。"""

from typing import Any, Protocol

from pydantic import BaseModel, Field

from review_agent.domain.models import ChangedFile, Finding, ToolRunResult


class SkillContext(BaseModel):
    """Skill 运行上下文。"""

    task_id: str
    repo_path: str
    diff_text: str
    changed_files: list[ChangedFile]
    config: dict[str, Any] = Field(default_factory=dict)


class SkillResult(BaseModel):
    """Skill 输出结果。"""

    skill_name: str
    findings: list[Finding] = Field(default_factory=list)
    tool_runs: list[ToolRunResult] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    raw_outputs: dict[str, Any] = Field(default_factory=dict)
    status: str = "success"
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ReviewSkill(Protocol):
    """Skill 协议。"""

    skill_name: str

    async def run(self, ctx: SkillContext) -> SkillResult:
        """执行 skill。"""
