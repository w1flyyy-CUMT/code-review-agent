"""审批接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from review_agent.api.deps import get_approval_service
from review_agent.api.schemas import ApprovalRequest, ReviewResponse
from review_agent.application.approval_service import ApprovalService
from review_agent.common.errors import ApprovalError, TaskNotFoundError

router = APIRouter(tags=["approvals"])


@router.post("/reviews/{task_id}/approvals", response_model=ReviewResponse)
async def submit_approval(
    task_id: str,
    req: ApprovalRequest,
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> ReviewResponse:
    """提交审批结果并恢复执行。"""
    try:
        task = await service.submit_approval(task_id, req.decision, req.comment)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ReviewResponse(
        task_id=task.task_id,
        status=task.status.value,
        risk_level=task.risk_level.value,
        approval_required=task.approval_required,
        approval_status=task.approval_status.value,
        current_node=task.current_node,
        next_action=task.next_action,
        waiting_reason=task.waiting_reason,
        trace_id=task.trace_id,
        findings=[finding.model_dump(mode="json") for finding in task.findings],
        report_markdown=task.report_markdown or "",
    )
