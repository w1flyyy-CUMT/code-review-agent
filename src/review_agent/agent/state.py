"""Agent 状态定义。"""

from typing import Any

from pydantic import BaseModel, Field

from src.review_agent.domain.enums import ApprovalStatus, RiskLevel, TaskStatus
from src.review_agent.domain.models import ChangedFile, Finding, ToolRunResult


class AgentState(BaseModel):
    """LangGraph 共享状态。"""

    task_id: str
    repo_path: str
    diff_text: str

    status: TaskStatus = TaskStatus.PENDING
    current_node: str | None = None
    next_action: str | None = None
    waiting_reason: str | None = None

    changed_files: list[ChangedFile] = Field(default_factory=list)
    selected_skills: list[str] = Field(default_factory=list)
    skill_results: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    tool_runs: list[ToolRunResult] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW

    approval_required: bool = False
    approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    approval_comment: str | None = None

    report_json: dict[str, Any] | None = None
    report_markdown: str | None = None

    trace_id: str | None = None
    retry_count: int = 0
    last_error: str | None = None
    errors: list[str] = Field(default_factory=list)
