"""领域模型定义。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from review_agent.domain.enums import (
    ApprovalDecision,
    ApprovalStatus,
    FindingSeverity,
    RiskLevel,
    TaskStatus,
)


class Hunk(BaseModel):
    """Diff hunk 信息。"""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str | None = None


class ChangedFile(BaseModel):
    """变更文件信息。"""

    path: str
    language: str
    change_type: str
    added_lines: int = 0
    deleted_lines: int = 0
    file_type: str = "code"
    risk_tags: list[str] = Field(default_factory=list)
    hunks: list[Hunk] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    """证据片段。"""

    source_type: str
    source_id: str | None = None
    path: str | None = None
    snippet: str
    score: float | None = None
    reason: str | None = None


class ToolRunResult(BaseModel):
    """外部工具运行结果。"""

    tool_name: str
    command: list[str] = Field(default_factory=list)
    success: bool
    skipped: bool = False
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    summary: str = ""


class Finding(BaseModel):
    """结构化评审结论。"""

    title: str
    category: str
    severity: FindingSeverity
    confidence: float
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    summary: str
    suggestion: str
    review_comment: str | None = None
    skill_name: str
    dedupe_key: str | None = None
    evidences: list[Evidence] = Field(default_factory=list)
    needs_approval: bool = False


class TraceEvent(BaseModel):
    """链路事件。"""

    node: str
    message: str
    created_at: datetime


class ApprovalRecord(BaseModel):
    """审批记录。"""

    decision: ApprovalDecision
    status: ApprovalStatus
    comment: str | None = None
    decided_at: datetime


class ReviewTask(BaseModel):
    """持久化后的评审任务快照。"""

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
    approval_record: ApprovalRecord | None = None

    report_json: dict[str, Any] | None = None
    report_markdown: str | None = None

    trace_id: str
    trace_events: list[TraceEvent] = Field(default_factory=list)
    retry_count: int = 0
    last_error: str | None = None
    errors: list[str] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
