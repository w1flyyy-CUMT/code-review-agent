"""反思决策与审批恢复测试。"""

from review_agent.agent.nodes import (
    generate_report_node,
    reflect_and_decide_node,
    resume_after_approval_node,
)
from review_agent.agent.state import AgentState
from review_agent.domain.enums import ApprovalStatus, FindingSeverity, RiskLevel, TaskStatus
from review_agent.domain.models import Evidence, Finding


def _build_state(findings: list[Finding]) -> AgentState:
    return AgentState(
        task_id="rvw_001",
        repo_path="D:/demo/repo",
        diff_text="diff --git a/app/demo.py b/app/demo.py",
        selected_skills=["diff_summary_skill", "risk_pattern_skill"],
        findings=findings,
        evidence_count=sum(len(finding.evidences) for finding in findings),
    )


def _finding(
    *,
    severity: FindingSeverity,
    confidence: float = 0.9,
    needs_approval: bool = False,
    evidences: list[Evidence] | None = None,
    category: str = "reliability",
) -> Finding:
    return Finding(
        title="示例问题",
        category=category,
        severity=severity,
        confidence=confidence,
        file_path="app/demo.py",
        start_line=1,
        end_line=3,
        summary="示例摘要",
        suggestion="示例建议",
        skill_name="test_skill",
        needs_approval=needs_approval,
        evidences=evidences or [],
    )


async def test_reflect_and_decide_node_marks_high_risk_and_requires_approval() -> None:
    state = _build_state(
        [
            _finding(
                severity=FindingSeverity.HIGH,
                confidence=0.88,
                evidences=[
                    Evidence(
                        source_type="diff",
                        snippet="except Exception:\n    pass",
                        reason="命中了高风险规则",
                    )
                ],
            )
        ]
    )

    result = await reflect_and_decide_node(state)

    assert result.risk_level == RiskLevel.HIGH
    assert result.approval_required is True
    assert result.approval_status == ApprovalStatus.PENDING
    assert result.status == TaskStatus.WAITING_APPROVAL
    assert result.confidence is not None
    assert "存在高风险评审结论，需要人工确认处置策略。" in result.manual_review_reasons


async def test_reflect_and_decide_node_promotes_explicit_approval_reason() -> None:
    state = _build_state(
        [
            _finding(
                severity=FindingSeverity.LOW,
                needs_approval=True,
                evidences=[
                    Evidence(
                        source_type="tool",
                        source_id="pytest",
                        snippet="pytest failed",
                        reason="测试失败",
                    )
                ],
            )
        ]
    )

    result = await reflect_and_decide_node(state)

    assert result.risk_level == RiskLevel.LOW
    assert result.approval_required is True
    assert result.approval_status == ApprovalStatus.PENDING
    assert "存在显式要求审批的评审结论。" in result.manual_review_reasons


async def test_reflect_and_decide_node_keeps_low_risk_task_auto_complete_ready() -> None:
    state = _build_state(
        [
            _finding(
                severity=FindingSeverity.MEDIUM,
                confidence=0.86,
                category="test",
                evidences=[
                    Evidence(
                        source_type="diff_summary",
                        snippet="未发现测试改动",
                        reason="测试影响启发式判断",
                    )
                ],
            )
        ]
    )

    result = await reflect_and_decide_node(state)

    assert result.risk_level == RiskLevel.MEDIUM
    assert result.approval_required is False
    assert result.approval_status == ApprovalStatus.NOT_REQUIRED
    assert result.status == TaskStatus.RUNNING
    assert result.next_action == "generate_report"
    assert result.manual_review_reasons == []
    assert result.confidence is not None and result.confidence >= 0.8


async def test_resume_after_approval_rejection_stops_flow() -> None:
    state = _build_state([_finding(severity=FindingSeverity.HIGH)])
    state.approval_required = True
    state.approval_status = ApprovalStatus.REJECTED

    resumed_state = await resume_after_approval_node(state)

    assert resumed_state.status == TaskStatus.FAILED
    assert resumed_state.last_error == "审批已拒绝，评审流程终止。"
    assert resumed_state.next_action is None


async def test_resume_after_approval_can_generate_report() -> None:
    state = _build_state(
        [
            _finding(
                severity=FindingSeverity.HIGH,
                evidences=[
                    Evidence(
                        source_type="diff",
                        snippet="except Exception:\n    pass",
                        reason="命中了高风险规则",
                    )
                ],
            )
        ]
    )
    state.approval_required = True
    state.approval_status = ApprovalStatus.APPROVED
    state.waiting_reason = "存在高风险评审结论，需要人工确认处置策略。"
    state.risk_level = RiskLevel.HIGH
    state.confidence = 0.9
    state.manual_review_reasons = ["存在高风险评审结论，需要人工确认处置策略。"]

    resumed_state = await resume_after_approval_node(state)

    assert resumed_state.status == TaskStatus.RUNNING
    assert resumed_state.waiting_reason is None

    reported_state = await generate_report_node(resumed_state)

    assert reported_state.status == TaskStatus.COMPLETED
    assert reported_state.current_node == "generate_report"
    assert reported_state.report_json is not None
    assert reported_state.report_markdown is not None
