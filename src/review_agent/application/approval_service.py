"""审批服务。"""

from __future__ import annotations

from typing import Any

from review_agent.agent.state import AgentState
from review_agent.application.review_service import ReviewService
from review_agent.common.clock import utc_now
from review_agent.common.errors import ApprovalError
from review_agent.domain.enums import ApprovalDecision, ApprovalStatus, TaskStatus
from review_agent.domain.models import ApprovalRecord, ReviewTask, TraceEvent
from review_agent.repository.review_task_repo import ReviewTaskRepository


class ApprovalService:
    """处理高风险结果审批。"""

    def __init__(self, repository: ReviewTaskRepository, resume_graph: Any) -> None:
        self._repository = repository
        self._resume_graph = resume_graph

    async def submit_approval(
        self,
        task_id: str,
        decision: ApprovalDecision,
        comment: str | None,
    ) -> ReviewTask:
        """提交审批结果，并在必要时恢复执行。"""
        task = self._repository.get(task_id)

        if not task.approval_required:
            raise ApprovalError("当前任务不需要审批。")
        if task.status != TaskStatus.WAITING_APPROVAL:
            raise ApprovalError("当前任务不处于待审批状态。")

        task.approval_comment = comment
        task.approval_status = (
            ApprovalStatus.APPROVED
            if decision == ApprovalDecision.APPROVE
            else ApprovalStatus.REJECTED
        )
        task.approval_record = ApprovalRecord(
            decision=decision,
            status=task.approval_status,
            comment=comment,
            decided_at=utc_now(),
        )
        task.trace_events.append(
            TraceEvent(
                node="approval",
                message=f"审批完成：{decision.value}",
                created_at=utc_now(),
            )
        )

        state = ReviewService.state_from_task(task)
        state.approval_comment = comment
        state.approval_status = task.approval_status

        resumed_result = await self._resume_graph.ainvoke(state)
        resumed_state = AgentState.model_validate(resumed_result)
        task = ReviewService.apply_state(task, resumed_state)
        self._repository.save(task)
        return task
