"""LangGraph 节点实现。"""

from __future__ import annotations

import asyncio

from src.review_agent.agent.state import AgentState
from src.review_agent.common.clock import utc_now
from src.review_agent.domain.enums import ApprovalStatus, FindingSeverity, RiskLevel, TaskStatus
from src.review_agent.domain.models import ChangedFile, Finding, ReviewTask, ToolRunResult
from src.review_agent.reporting.json_report import JsonReportBuilder
from src.review_agent.reporting.markdown_report import MarkdownReportBuilder
from src.review_agent.skills.base import SkillContext
from src.review_agent.skills.registry import SkillRegistry
from src.review_agent.skills.router import SkillRouter
from src.review_agent.tools.git_diff_tool import GitDiffTool

skill_registry = SkillRegistry()
skill_router = SkillRouter()
diff_tool = GitDiffTool()
json_report_builder = JsonReportBuilder()
markdown_report_builder = MarkdownReportBuilder()


async def parse_diff_node(state: AgentState) -> AgentState:
    """解析原始 diff。"""
    state.current_node = "parse_diff"
    state.status = TaskStatus.RUNNING
    state.changed_files = diff_tool.parse(state.diff_text)
    return state


async def classify_files_node(state: AgentState) -> AgentState:
    """为变更文件补充分类与风险标签。"""
    state.current_node = "classify_files"

    for changed_file in state.changed_files:
        changed_file.file_type = _infer_file_type(changed_file)

        for tag in _infer_risk_tags(changed_file):
            _append_unique(changed_file.risk_tags, tag)

    return state


async def route_skills_node(state: AgentState) -> AgentState:
    """选择本次任务要执行的 skills。"""
    state.current_node = "route_skills"
    state.selected_skills = skill_router.route(state.changed_files)
    return state


async def run_skills_node(state: AgentState) -> AgentState:
    """并行执行所有选中的 skills。"""
    state.current_node = "run_skills"

    ctx = SkillContext(
        task_id=state.task_id,
        repo_path=state.repo_path,
        diff_text=state.diff_text,
        changed_files=state.changed_files,
        config={},
    )

    coroutines = []
    for skill_name in state.selected_skills:
        skill = skill_registry.get(skill_name)
        coroutines.append(skill.run(ctx))

    results = await asyncio.gather(*coroutines, return_exceptions=True)

    normalized_results: list[dict[str, object]] = []
    tool_runs: list[ToolRunResult] = []
    for result in results:
        if isinstance(result, BaseException):
            normalized_results.append(
                {
                    "skill_name": "unknown",
                    "findings": [],
                    "tool_runs": [],
                    "status": "failed",
                    "error_message": str(result),
                    "warnings": [],
                }
            )
            state.errors.append(str(result))
            continue

        skill_result = result
        normalized_results.append(skill_result.model_dump(mode="json"))
        tool_runs.extend(skill_result.tool_runs)

    state.skill_results = normalized_results
    state.tool_runs = tool_runs
    return state


async def aggregate_findings_node(state: AgentState) -> AgentState:
    """聚合并去重 findings。"""
    state.current_node = "aggregate_findings"

    findings: list[Finding] = []
    seen_keys: set[str] = set()

    for result in state.skill_results:
        raw_findings = result.get("findings", [])
        if not isinstance(raw_findings, list):
            continue

        for item in raw_findings:
            finding = Finding.model_validate(item)
            dedupe_key = finding.dedupe_key or (
                f"{finding.file_path}:{finding.start_line}:{finding.category}:{finding.title}"
            )
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            findings.append(finding)

    state.findings = findings
    return state


async def score_risk_node(state: AgentState) -> AgentState:
    """计算任务整体风险。"""
    state.current_node = "score_risk"

    severities = [finding.severity for finding in state.findings]

    if FindingSeverity.CRITICAL in severities:
        state.risk_level = RiskLevel.CRITICAL
    elif FindingSeverity.HIGH in severities:
        state.risk_level = RiskLevel.HIGH
    elif FindingSeverity.MEDIUM in severities:
        state.risk_level = RiskLevel.MEDIUM
    else:
        state.risk_level = RiskLevel.LOW

    state.approval_required = state.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL} or any(
        finding.needs_approval for finding in state.findings
    )
    state.approval_status = (
        ApprovalStatus.PENDING if state.approval_required else ApprovalStatus.NOT_REQUIRED
    )
    return state


async def approval_gate_node(state: AgentState) -> AgentState:
    """将任务挂起，等待人工审批。"""
    state.current_node = "approval_gate"
    state.status = TaskStatus.WAITING_APPROVAL
    state.waiting_reason = "存在高风险问题，需要人工审批"
    state.next_action = "submit_approval"
    return state


async def resume_after_approval_node(state: AgentState) -> AgentState:
    """在审批结束后恢复执行。"""
    state.current_node = "resume_after_approval"

    if state.approval_status == ApprovalStatus.REJECTED:
        state.status = TaskStatus.FAILED
        state.last_error = "审批已拒绝，评审流程终止。"
        state.next_action = None
        return state

    state.status = TaskStatus.RUNNING
    state.waiting_reason = None
    state.next_action = "generate_report"
    return state


async def generate_report_node(state: AgentState) -> AgentState:
    """通过 reporting 层生成评审报告。"""
    state.current_node = "generate_report"

    if state.approval_status == ApprovalStatus.REJECTED:
        state.status = TaskStatus.FAILED
    else:
        state.status = TaskStatus.COMPLETED

    report_task = _build_report_task(state)
    state.report_json = json_report_builder.build(report_task)
    state.report_markdown = markdown_report_builder.build(report_task)
    state.next_action = None
    return state


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _infer_file_type(file: ChangedFile) -> str:
    path_lower = file.path.lower()
    symbol_names = [symbol.lower() for symbol in file.symbols]

    if "test" in path_lower or any(symbol.startswith("function:test_") for symbol in symbol_names):
        return "test"

    if any(keyword in path_lower for keyword in {"migration", "migrations", "alembic", "versions"}):
        return "migration"

    if file.language in {"yaml", "toml", "json"} or path_lower.endswith((".env", ".ini")):
        return "config"

    if file.language == "markdown":
        return "documentation"

    return "code"


def _infer_risk_tags(file: ChangedFile) -> list[str]:
    path_lower = file.path.lower()
    symbol_names = [symbol.lower() for symbol in file.symbols]
    hunk_headers = [hunk.header.lower() for hunk in file.hunks if hunk.header]
    haystacks = [path_lower, *symbol_names, *hunk_headers]
    tags: list[str] = []

    if file.file_type == "test":
        tags.append("test")
        return tags

    if file.file_type == "migration":
        tags.append("migration")

    if file.file_type == "config":
        tags.append("config")

    auth_keywords = {"auth", "login", "token", "session", "credential"}
    if any(_contains_keyword(text, auth_keywords) for text in haystacks):
        tags.append("auth")

    permission_keywords = {"permission", "role", "policy", "scope"}
    if any(_contains_keyword(text, permission_keywords) for text in haystacks):
        tags.append("permission")

    database_keywords = {"repository", "model", "schema", "sql", "query"}
    if any(_contains_keyword(text, database_keywords) for text in haystacks):
        tags.append("database")

    if any(symbol.startswith("import:sqlalchemy") for symbol in symbol_names):
        tags.append("database")

    if any(_contains_keyword(text, {"api", "route", "router", "endpoint"}) for text in haystacks):
        tags.append("api")

    if "api" in tags and any(
        symbol.startswith("function:") and not symbol.startswith("function:_")
        for symbol in symbol_names
    ):
        tags.append("public_api")

    if file.change_type == "deleted" or any(
        _contains_keyword(text, {"delete", "remove", "drop"}) for text in haystacks
    ):
        tags.append("delete")

    return tags


def _contains_keyword(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _build_report_task(state: AgentState) -> ReviewTask:
    """将图状态转换为报告生成所需的任务快照。"""
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
        skill_results=state.skill_results,
        findings=state.findings,
        tool_runs=state.tool_runs,
        risk_level=state.risk_level,
        approval_required=state.approval_required,
        approval_status=state.approval_status,
        approval_comment=state.approval_comment,
        report_json=state.report_json,
        report_markdown=state.report_markdown,
        trace_id=state.trace_id or "trace_missing",
        retry_count=state.retry_count,
        last_error=state.last_error,
        errors=state.errors,
        created_at=now,
        updated_at=now,
    )
