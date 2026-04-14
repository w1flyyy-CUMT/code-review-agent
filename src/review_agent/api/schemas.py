"""API 请求与响应模型。"""

from typing import Any

from pydantic import BaseModel, Field

from src.review_agent.domain.enums import ApprovalDecision


class CreateReviewRequest(BaseModel):
    """创建评审任务请求。"""

    repo_path: str
    diff_text: str


class ApprovalRequest(BaseModel):
    """审批请求。"""

    decision: ApprovalDecision
    comment: str | None = None


class ReviewResponse(BaseModel):
    """评审结果响应。"""

    task_id: str
    status: str
    risk_level: str
    approval_required: bool
    approval_status: str
    current_node: str | None = None
    next_action: str | None = None
    waiting_reason: str | None = None
    trace_id: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    report_markdown: str = ""
