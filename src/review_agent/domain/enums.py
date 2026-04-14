"""领域枚举定义。"""

from enum import StrEnum


class TaskStatus(StrEnum):
    """评审任务状态。"""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(StrEnum):
    """任务级风险等级。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(StrEnum):
    """审批状态。"""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecision(StrEnum):
    """审批动作。"""

    APPROVE = "approve"
    REJECT = "reject"


class FindingSeverity(StrEnum):
    """Finding 严重级别。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
