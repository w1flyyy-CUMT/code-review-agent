"""评审任务应用服务。"""

from __future__ import annotations

from typing import Any

from review_agent.agent.state import AgentState
from review_agent.common.clock import utc_now
from review_agent.common.ids import new_task_id, new_trace_id
from review_agent.domain.models import ReviewTask, TraceEvent
from review_agent.repository.review_task_repo import ReviewTaskRepository


class ReviewService:
    """组织一次完整的评审任务执行。"""

    def __init__(self, repository: ReviewTaskRepository, graph: Any) -> None:
        self._repository = repository
        self._graph = graph

    async def run_review(self, task_id: str, repo_path: str, diff_text: str) -> AgentState:
        """执行评审图。"""
        initial_state = AgentState(
            task_id=task_id,
            repo_path=repo_path,
            diff_text=diff_text,
            trace_id=new_trace_id(),
        )
        result = await self._graph.ainvoke(initial_state)
        return AgentState.model_validate(result)

    async def create_review(self, repo_path: str, diff_text: str) -> ReviewTask:
        """创建并执行评审任务。"""
        task_id = new_task_id()
        state = await self.run_review(task_id=task_id, repo_path=repo_path, diff_text=diff_text)
        task = self._task_from_state(state)
        self._append_trace(task, "create_review", "已完成首次评审执行")
        self._repository.save(task)
        return task

    def get_review(self, task_id: str) -> ReviewTask:
        """查询评审任务。"""
        return self._repository.get(task_id)

    def _task_from_state(self, state: AgentState) -> ReviewTask:
        now = utc_now()
        return ReviewTask(
            task_id=state.task_id,
            repo_path=state.repo_path,
            diff_text=state.diff_text,
            status=state.status,
            current_node=state.current_node,
            next_action=state.next_action,
            waiting_reason=state.waiting_reason,
            changed_files=state.changed_files,
            selected_skills=state.selected_skills,
            analysis_depth=state.analysis_depth,
            priority_files=state.priority_files,
            requires_context_review=state.requires_context_review,
            skill_results=state.skill_results,
            findings=state.findings,
            tool_runs=state.tool_runs,
            risk_level=state.risk_level,
            confidence=state.confidence,
            manual_review_reasons=state.manual_review_reasons,
            evidence_count=state.evidence_count,
            approval_required=state.approval_required,
            approval_status=state.approval_status,
            approval_comment=state.approval_comment,
            report_json=state.report_json,
            report_markdown=state.report_markdown,
            trace_id=state.trace_id or new_trace_id(),
            retry_count=state.retry_count,
            last_error=state.last_error,
            errors=state.errors,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def state_from_task(task: ReviewTask) -> AgentState:
        """将持久化任务转换为图状态。"""
        return AgentState(
            task_id=task.task_id,
            repo_path=task.repo_path,
            diff_text=task.diff_text,
            status=task.status,
            current_node=task.current_node,
            next_action=task.next_action,
            waiting_reason=task.waiting_reason,
            changed_files=task.changed_files,
            selected_skills=task.selected_skills,
            analysis_depth=task.analysis_depth,
            priority_files=task.priority_files,
            requires_context_review=task.requires_context_review,
            skill_results=task.skill_results,
            findings=task.findings,
            tool_runs=task.tool_runs,
            risk_level=task.risk_level,
            confidence=task.confidence,
            manual_review_reasons=task.manual_review_reasons,
            evidence_count=task.evidence_count,
            approval_required=task.approval_required,
            approval_status=task.approval_status,
            approval_comment=task.approval_comment,
            report_json=task.report_json,
            report_markdown=task.report_markdown,
            trace_id=task.trace_id,
            retry_count=task.retry_count,
            last_error=task.last_error,
            errors=task.errors,
        )

    @staticmethod
    def apply_state(task: ReviewTask, state: AgentState) -> ReviewTask:
        """将最新状态回写到任务对象。"""
        task.status = state.status
        task.current_node = state.current_node
        task.next_action = state.next_action
        task.waiting_reason = state.waiting_reason
        task.changed_files = state.changed_files
        task.selected_skills = state.selected_skills
        task.analysis_depth = state.analysis_depth
        task.priority_files = state.priority_files
        task.requires_context_review = state.requires_context_review
        task.skill_results = state.skill_results
        task.findings = state.findings
        task.tool_runs = state.tool_runs
        task.risk_level = state.risk_level
        task.confidence = state.confidence
        task.manual_review_reasons = state.manual_review_reasons
        task.evidence_count = state.evidence_count
        task.approval_required = state.approval_required
        task.approval_status = state.approval_status
        task.approval_comment = state.approval_comment
        task.report_json = state.report_json
        task.report_markdown = state.report_markdown
        task.trace_id = state.trace_id or task.trace_id
        task.retry_count = state.retry_count
        task.last_error = state.last_error
        task.errors = state.errors
        task.updated_at = utc_now()
        return task

    @staticmethod
    def _append_trace(task: ReviewTask, node: str, message: str) -> None:
        task.trace_events.append(
            TraceEvent(
                node=node,
                message=message,
                created_at=utc_now(),
            )
        )
