"""JSON 报告生成。"""

from typing import Any

from review_agent.domain.models import ReviewTask


class JsonReportBuilder:
    """生成结构化评审报告。"""

    def build(self, task: ReviewTask) -> dict[str, Any]:
        """构建 JSON 报告。"""
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "risk_level": task.risk_level.value,
            "analysis_depth": task.analysis_depth,
            "priority_files": task.priority_files,
            "confidence": task.confidence,
            "manual_review_reasons": task.manual_review_reasons,
            "evidence_count": task.evidence_count,
            "approval_required": task.approval_required,
            "approval_status": task.approval_status.value,
            "changed_files": [
                changed_file.model_dump(mode="json") for changed_file in task.changed_files
            ],
            "findings": [finding.model_dump(mode="json") for finding in task.findings],
            "tool_runs": [tool_run.model_dump(mode="json") for tool_run in task.tool_runs],
            "trace_id": task.trace_id,
        }
