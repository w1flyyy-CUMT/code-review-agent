"""报告服务。"""

from review_agent.domain.models import ReviewTask
from review_agent.reporting.json_report import JsonReportBuilder
from review_agent.reporting.markdown_report import MarkdownReportBuilder


class ReportService:
    """统一生成任务报告。"""

    def __init__(self) -> None:
        self._json_builder = JsonReportBuilder()
        self._markdown_builder = MarkdownReportBuilder()

    def build(self, task: ReviewTask) -> ReviewTask:
        """为任务生成报告。"""
        task.report_json = self._json_builder.build(task)
        task.report_markdown = self._markdown_builder.build(task)
        return task
