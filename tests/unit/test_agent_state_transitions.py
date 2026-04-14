"""风险评分与审批状态机测试。"""

from review_agent.agent.nodes import approval_gate_node, resume_after_approval_node, score_risk_node
from review_agent.agent.state import AgentState
from review_agent.domain.enums import ApprovalStatus, FindingSeverity, RiskLevel, TaskStatus
from review_agent.domain.models import Finding


def _build_state(findings: list[Finding]) -> AgentState:
    return AgentState(
        task_id="rvw_001",
        repo_path="D:/demo/repo",
        diff_text="diff --git a/app/demo.py b/app/demo.py",
        findings=findings,
    )


def _finding(*, severity: FindingSeverity, needs_approval: bool = False) -> Finding:
    return Finding(
        title="示例问题",
        category="reliability",
        severity=severity,
        confidence=0.9,
        file_path="app/demo.py",
        start_line=1,
        end_line=3,
        summary="示例摘要",
        suggestion="示例建议",
        skill_name="test_skill",
        needs_approval=needs_approval,
    )


async def test_score_risk_node_marks_high_risk_and_requires_approval() -> None:
    state = _build_state([_finding(severity=FindingSeverity.HIGH)])

    result = await score_risk_node(state)

    assert result.risk_level == RiskLevel.HIGH
    assert result.approval_required is True
    assert result.approval_status == ApprovalStatus.PENDING


async def test_score_risk_node_promotes_low_risk_finding_with_explicit_approval() -> None:
    state = _build_state([_finding(severity=FindingSeverity.LOW, needs_approval=True)])

    result = await score_risk_node(state)

    assert result.risk_level == RiskLevel.LOW
    assert result.approval_required is True
    assert result.approval_status == ApprovalStatus.PENDING


async def test_approval_gate_and_rejection_resume_flow() -> None:
    state = _build_state([_finding(severity=FindingSeverity.HIGH)])
    state.approval_required = True
    state.approval_status = ApprovalStatus.PENDING

    waiting_state = await approval_gate_node(state)

    assert waiting_state.status == TaskStatus.WAITING_APPROVAL
    assert waiting_state.waiting_reason == "存在高风险问题，需要人工审批"
    assert waiting_state.next_action == "submit_approval"

    waiting_state.approval_status = ApprovalStatus.REJECTED
    resumed_state = await resume_after_approval_node(waiting_state)

    assert resumed_state.status == TaskStatus.FAILED
    assert resumed_state.last_error == "审批已拒绝，评审流程终止。"
    assert resumed_state.next_action is None


async def test_resume_after_approval_accepts_non_rejected_tasks() -> None:
    state = _build_state([_finding(severity=FindingSeverity.HIGH)])
    state.approval_status = ApprovalStatus.APPROVED
    state.waiting_reason = "存在高风险问题，需要人工审批"

    resumed_state = await resume_after_approval_node(state)

    assert resumed_state.status == TaskStatus.RUNNING
    assert resumed_state.waiting_reason is None
    assert resumed_state.next_action == "generate_report"
