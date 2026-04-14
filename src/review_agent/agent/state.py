"""Agent 状态定义。"""

from typing import Any

from pydantic import BaseModel, Field

from review_agent.domain.enums import ApprovalStatus, RiskLevel, TaskStatus
from review_agent.domain.models import ChangedFile, Finding, ToolRunResult


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
    analysis_depth: str | None = None
    priority_files: list[str] = Field(default_factory=list)
    requires_context_review: bool = False
    skill_results: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    tool_runs: list[ToolRunResult] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    confidence: float | None = None
    manual_review_reasons: list[str] = Field(default_factory=list)
    evidence_count: int = 0

    approval_required: bool = False
    approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    approval_comment: str | None = None

    report_json: dict[str, Any] | None = None
    report_markdown: str | None = None

    trace_id: str | None = None
    retry_count: int = 0
    last_error: str | None = None
    errors: list[str] = Field(default_factory=list)
