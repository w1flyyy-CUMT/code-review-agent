"""评审任务接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from review_agent.api.deps import get_review_service
from review_agent.api.schemas import CreateReviewRequest, ReviewResponse
from review_agent.application.review_service import ReviewService
from review_agent.common.errors import TaskNotFoundError

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    req: CreateReviewRequest,
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReviewResponse:
    """创建并执行一条评审任务。"""
    task = await service.create_review(req.repo_path, req.diff_text)
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


@router.get("/{task_id}", response_model=ReviewResponse)
async def get_review(
    task_id: str,
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReviewResponse:
    """查询评审任务。"""
    try:
        task = service.get_review(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

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
