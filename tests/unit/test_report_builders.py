"""报告构建器与报告服务测试。"""

from datetime import UTC, datetime

import pytest

from review_agent.application.report_service import ReportService
from review_agent.domain.enums import (
    ApprovalDecision,
    ApprovalStatus,
    FindingSeverity,
    RiskLevel,
    TaskStatus,
)
from review_agent.domain.models import (
    ApprovalRecord,
    ChangedFile,
    Finding,
    ReviewTask,
    ToolRunResult,
)
from review_agent.reporting.json_report import JsonReportBuilder
from review_agent.reporting.markdown_report import MarkdownReportBuilder


def _build_task() -> ReviewTask:
    return ReviewTask(
        task_id="rvw_002",
        repo_path="D:/demo/repo",
        diff_text="diff --git a/app/demo.py b/app/demo.py",
        status=TaskStatus.COMPLETED,
        changed_files=[
            ChangedFile(
                path="app/demo.py",
                language="python",
                change_type="modified",
                added_lines=7,
                deleted_lines=2,
            )
        ],
        findings=[
            Finding(
                title="示例问题",
                category="reliability",
                severity=FindingSeverity.HIGH,
                confidence=0.88,
                file_path="app/demo.py",
                start_line=1,
                end_line=3,
                summary="示例摘要",
                suggestion="示例建议",
                skill_name="test_skill",
            )
        ],
        tool_runs=[
            ToolRunResult(
                tool_name="ruff",
                command=["ruff", "check", "."],
                success=True,
                skipped=False,
                exit_code=0,
                stdout="ok",
                stderr="",
                summary="静态检查通过",
            )
        ],
        risk_level=RiskLevel.HIGH,
        approval_required=True,
        approval_status=ApprovalStatus.APPROVED,
        approval_comment="已确认",
        approval_record=ApprovalRecord(
            decision=ApprovalDecision.APPROVE,
            status=ApprovalStatus.APPROVED,
            comment="已确认",
            decided_at=datetime(2026, 4, 14, tzinfo=UTC),
        ),
        trace_id="trace-001",
        created_at=datetime(2026, 4, 14, tzinfo=UTC),
        updated_at=datetime(2026, 4, 14, tzinfo=UTC),
    )


def test_json_report_builder_includes_core_structured_fields() -> None:
    task = _build_task()

    report = JsonReportBuilder().build(task)

    assert report["task_id"] == "rvw_002"
    assert report["status"] == "completed"
    assert report["risk_level"] == "high"
    assert report["approval_status"] == "approved"
    assert report["trace_id"] == "trace-001"
    assert report["changed_files"][0]["path"] == "app/demo.py"
    assert report["findings"][0]["title"] == "示例问题"
    assert report["tool_runs"][0]["tool_name"] == "ruff"


def test_markdown_report_builder_renders_approval_section() -> None:
    task = _build_task()

    report = MarkdownReportBuilder().build(task)

    assert "# " in report
    assert "## Findings" in report
    assert "## 审批记录" in report
    assert "示例问题" in report
    assert "ruff" in report
    assert "已确认" in report


def test_report_service_populates_both_report_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    task = _build_task()
    service = ReportService()

    def _build_json(current_task: ReviewTask) -> dict[str, str]:
        return {"task_id": current_task.task_id}

    def _build_markdown(current_task: ReviewTask) -> str:
        return "markdown-report"

    monkeypatch.setattr(service._json_builder, "build", _build_json)
    monkeypatch.setattr(service._markdown_builder, "build", _build_markdown)

    result = service.build(task)

    assert result is task
    assert task.report_json == {"task_id": "rvw_002"}
    assert task.report_markdown == "markdown-report"
