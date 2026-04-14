"""LangGraph 节点实现。"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from review_agent.agent.state import AgentState
from review_agent.common.clock import utc_now
from review_agent.domain.enums import ApprovalStatus, FindingSeverity, RiskLevel, TaskStatus
from review_agent.domain.models import ChangedFile, Finding, ReviewTask, ToolRunResult
from review_agent.reporting.json_report import JsonReportBuilder
from review_agent.reporting.markdown_report import MarkdownReportBuilder
from review_agent.skills.base import SkillContext
from review_agent.skills.registry import SkillRegistry
from review_agent.skills.router import SkillRouter
from review_agent.tools.git_diff_tool import GitDiffTool

skill_registry = SkillRegistry()
skill_router = SkillRouter()
diff_tool = GitDiffTool()
json_report_builder = JsonReportBuilder()
markdown_report_builder = MarkdownReportBuilder()

_HIGH_RISK_TAGS = {"auth", "permission", "migration", "delete", "database", "config"}
_CONTEXT_REVIEW_TAGS = {"auth", "permission", "public_api", "database", "migration"}
_SEVERITY_WEIGHTS = {
    FindingSeverity.LOW: 1,
    FindingSeverity.MEDIUM: 2,
    FindingSeverity.HIGH: 3,
    FindingSeverity.CRITICAL: 4,
}


async def parse_input_node(state: AgentState) -> AgentState:
    """解析输入 diff，并补全 changed_files 的文件类型与风险标签。"""
    state.current_node = "parse_input"
    state.status = TaskStatus.RUNNING

    changed_files = diff_tool.parse(state.diff_text)
    for changed_file in changed_files:
        changed_file.file_type = _infer_file_type(changed_file)
        changed_file.risk_tags = _merge_unique_values(_infer_risk_tags(changed_file))

    state.changed_files = changed_files
    return state


async def plan_and_route_node(state: AgentState) -> AgentState:
    """基于变更特征规划分析策略，并选择本轮执行的 skills。"""
    state.current_node = "plan_and_route"
    state.selected_skills = skill_router.route(state.changed_files)
    state.priority_files = _select_priority_files(state.changed_files)
    state.analysis_depth = _choose_analysis_depth(state.changed_files, state.selected_skills)
    state.requires_context_review = _requires_context_review(state.changed_files)
    return state


async def execute_review_node(state: AgentState) -> AgentState:
    """并行执行已选 skills，并聚合 findings 与工具执行记录。"""
    state.current_node = "execute_review"

    ctx = SkillContext(
        task_id=state.task_id,
        repo_path=state.repo_path,
        diff_text=state.diff_text,
        changed_files=state.changed_files,
        config={
            "analysis_depth": state.analysis_depth,
            "priority_files": state.priority_files,
            "requires_context_review": state.requires_context_review,
        },
    )

    coroutines = []
    for skill_name in state.selected_skills:
        skill = skill_registry.get(skill_name)
        coroutines.append(skill.run(ctx))

    results = await asyncio.gather(*coroutines, return_exceptions=True)

    normalized_results: list[dict[str, object]] = []
    tool_runs: list[ToolRunResult] = []
    findings: list[Finding] = []

    for skill_name, result in zip(state.selected_skills, results, strict=False):
        if isinstance(result, BaseException):
            normalized_results.append(
                {
                    "skill_name": skill_name,
                    "findings": [],
                    "tool_runs": [],
                    "status": "failed",
                    "error_message": str(result),
                    "warnings": [],
                }
            )
            state.errors.append(str(result))
            continue

        normalized_results.append(result.model_dump(mode="json"))
        tool_runs.extend(result.tool_runs)
        findings.extend(result.findings)

    deduplicated_findings = _deduplicate_findings(findings)
    state.skill_results = normalized_results
    state.tool_runs = tool_runs
    state.findings = deduplicated_findings
    state.evidence_count = _count_evidences(deduplicated_findings)
    return state


async def reflect_and_decide_node(state: AgentState) -> AgentState:
    """基于首轮 findings 做反思判断，并决定是否进入人工复核。"""
    state.current_node = "reflect_and_decide"

    evidence_count = state.evidence_count or _count_evidences(state.findings)
    risk_level = _score_risk(state.findings)
    confidence = _estimate_confidence(
        findings=state.findings,
        selected_skill_count=len(state.selected_skills),
        evidence_count=evidence_count,
        requires_context_review=state.requires_context_review,
    )
    manual_review_reasons = _collect_manual_review_reasons(
        findings=state.findings,
        risk_level=risk_level,
        confidence=confidence,
        evidence_count=evidence_count,
        requires_context_review=state.requires_context_review,
    )

    state.risk_level = risk_level
    state.confidence = confidence
    state.evidence_count = evidence_count
    state.manual_review_reasons = manual_review_reasons
    state.approval_required = bool(manual_review_reasons)

    if state.approval_required:
        state.status = TaskStatus.WAITING_APPROVAL
        state.approval_status = ApprovalStatus.PENDING
        state.waiting_reason = manual_review_reasons[0]
        state.next_action = "submit_approval"
        return state

    state.status = TaskStatus.RUNNING
    state.approval_status = ApprovalStatus.NOT_REQUIRED
    state.waiting_reason = None
    state.next_action = "generate_report"
    return state


async def resume_after_approval_node(state: AgentState) -> AgentState:
    """在审批结束后恢复执行。拒绝则终止，通过则继续生成报告。"""
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
    """根据最新状态生成结构化报告与 Markdown 报告。"""
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


def _merge_unique_values(values: Iterable[str]) -> list[str]:
    """保持原始顺序去重。"""
    unique_values: list[str] = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)
    return unique_values


def _select_priority_files(changed_files: list[ChangedFile], limit: int = 3) -> list[str]:
    """优先挑出高风险且影响面更大的文件，供后续评审策略使用。"""
    ranked_files = sorted(
        changed_files,
        key=lambda changed_file: (
            _priority_score(changed_file),
            changed_file.added_lines + changed_file.deleted_lines,
            changed_file.path,
        ),
        reverse=True,
    )
    return [changed_file.path for changed_file in ranked_files[:limit]]


def _priority_score(changed_file: ChangedFile) -> int:
    score = len(changed_file.risk_tags) * 3
    if changed_file.file_type in {"migration", "config"}:
        score += 4
    if changed_file.file_type == "code":
        score += 2
    if changed_file.language == "python":
        score += 1
    if any(tag in _HIGH_RISK_TAGS for tag in changed_file.risk_tags):
        score += 6
    return score


def _choose_analysis_depth(changed_files: list[ChangedFile], selected_skills: list[str]) -> str:
    """用轻量规则决定本轮评审深度。"""
    total_changed_lines = sum(
        changed_file.added_lines + changed_file.deleted_lines for changed_file in changed_files
    )
    has_high_risk = any(
        tag in _HIGH_RISK_TAGS for changed_file in changed_files for tag in changed_file.risk_tags
    )
    touches_core_code = any(
        changed_file.file_type in {"code", "migration"} for changed_file in changed_files
    )

    if has_high_risk or total_changed_lines >= 120 or len(selected_skills) >= 4:
        return "deep"
    if touches_core_code or len(changed_files) > 1:
        return "standard"
    return "light"


def _requires_context_review(changed_files: list[ChangedFile]) -> bool:
    """预留上下文复核开关，为后续接入 RAG / 仓库规则检索做准备。"""
    return any(
        changed_file.file_type in {"migration", "config"}
        or any(tag in _CONTEXT_REVIEW_TAGS for tag in changed_file.risk_tags)
        for changed_file in changed_files
    )


def _deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """按 dedupe_key 聚合 findings，优先保留更强证据的结果。"""
    deduplicated: dict[str, Finding] = {}

    for finding in findings:
        dedupe_key = finding.dedupe_key or (
            f"{finding.file_path}:{finding.start_line}:{finding.category}:{finding.title}"
        )
        existing = deduplicated.get(dedupe_key)
        if existing is None or _finding_rank(finding) > _finding_rank(existing):
            deduplicated[dedupe_key] = finding

    return list(deduplicated.values())


def _finding_rank(finding: Finding) -> tuple[int, float, int]:
    return (
        _SEVERITY_WEIGHTS[finding.severity],
        finding.confidence,
        len(finding.evidences),
    )


def _count_evidences(findings: list[Finding]) -> int:
    """聚合所有 findings 的证据数量。"""
    return sum(len(finding.evidences) for finding in findings)


def _score_risk(findings: list[Finding]) -> RiskLevel:
    """综合 findings 严重级别，给出整体风险等级。"""
    severities = [finding.severity for finding in findings]

    if FindingSeverity.CRITICAL in severities:
        return RiskLevel.CRITICAL
    if FindingSeverity.HIGH in severities:
        return RiskLevel.HIGH
    if FindingSeverity.MEDIUM in severities:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _estimate_confidence(
    *,
    findings: list[Finding],
    selected_skill_count: int,
    evidence_count: int,
    requires_context_review: bool,
) -> float:
    """基于 findings、证据数量和上下文需求估算整体置信度。"""
    if not findings:
        base_confidence = 0.68 + min(selected_skill_count, 4) * 0.04
        if requires_context_review:
            base_confidence -= 0.08
        return round(_clamp(base_confidence, lower=0.2, upper=0.95), 2)

    average_confidence = sum(finding.confidence for finding in findings) / len(findings)
    evidence_bonus = min(0.12, evidence_count * 0.02)
    coverage_bonus = min(0.08, selected_skill_count * 0.02)
    context_penalty = 0.08 if requires_context_review and evidence_count == 0 else 0.0
    evidence_penalty = 0.1 if _has_insufficient_evidence(findings, evidence_count) else 0.0
    conflict_penalty = 0.12 if _has_conflicting_signals(findings) else 0.0

    confidence = (
        average_confidence
        + evidence_bonus
        + coverage_bonus
        - context_penalty
        - evidence_penalty
        - conflict_penalty
    )
    return round(_clamp(confidence, lower=0.05, upper=0.99), 2)


def _collect_manual_review_reasons(
    *,
    findings: list[Finding],
    risk_level: RiskLevel,
    confidence: float,
    evidence_count: int,
    requires_context_review: bool,
) -> list[str]:
    """聚合需要人工复核的原因，兼顾高风险、低置信度和证据完整性。"""
    reasons: list[str] = []

    if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        reasons.append("存在高风险评审结论，需要人工确认处置策略。")

    if any(finding.needs_approval for finding in findings):
        reasons.append("存在显式要求审批的评审结论。")

    if _has_insufficient_evidence(findings, evidence_count):
        reasons.append("当前证据不足，建议人工补充上下文后复核。")

    if _has_conflicting_signals(findings):
        reasons.append("评审信号存在冲突，建议人工复核关键变更。")

    if confidence < 0.65:
        reasons.append("整体评审置信度偏低，建议人工复核。")

    if requires_context_review and evidence_count == 0:
        reasons.append("该变更依赖仓库上下文判断，当前尚未补足上下文证据。")

    return _merge_unique_values(reasons)


def _has_insufficient_evidence(findings: list[Finding], evidence_count: int) -> bool:
    """高风险或显式审批结论如果缺少证据，应转入人工复核。"""
    if not findings:
        return False

    needs_strong_evidence = any(
        finding.severity in {FindingSeverity.HIGH, FindingSeverity.CRITICAL}
        or finding.needs_approval
        for finding in findings
    )
    return needs_strong_evidence and evidence_count == 0


def _has_conflicting_signals(findings: list[Finding]) -> bool:
    """识别高风险低置信度与低风险高置信度并存的冲突信号。"""
    high_risk_low_confidence = any(
        finding.category != "summary"
        and finding.severity in {FindingSeverity.HIGH, FindingSeverity.CRITICAL}
        and finding.confidence < 0.7
        for finding in findings
    )
    low_risk_high_confidence = any(
        finding.category != "summary"
        and finding.severity in {FindingSeverity.LOW, FindingSeverity.MEDIUM}
        and finding.confidence >= 0.9
        for finding in findings
    )
    return high_risk_low_confidence and low_risk_high_confidence


def _clamp(value: float, *, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _infer_file_type(file: ChangedFile) -> str:
    """根据路径、语言和 symbols 推断文件类型。"""
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
    """根据文件特征推断风险标签，供规划与反思阶段使用。"""
    path_lower = file.path.lower()
    symbol_names = [symbol.lower() for symbol in file.symbols]
    hunk_headers = [hunk.header.lower() for hunk in file.hunks if hunk.header]
    haystacks = [path_lower, *symbol_names, *hunk_headers]
    tags: list[str] = []

    if file.file_type == "test":
        return ["test"]

    if file.file_type == "migration":
        tags.append("migration")

    if file.file_type == "config":
        tags.append("config")

    if any(
        _contains_keyword(text, {"auth", "login", "token", "session", "credential"})
        for text in haystacks
    ):
        tags.append("auth")

    if any(
        _contains_keyword(text, {"permission", "role", "policy", "scope"})
        for text in haystacks
    ):
        tags.append("permission")

    if any(
        _contains_keyword(text, {"repository", "model", "schema", "sql", "query"})
        for text in haystacks
    ):
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
    """判断文本中是否包含任一关键词。"""
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
        trace_id=state.trace_id or "trace_missing",
        retry_count=state.retry_count,
        last_error=state.last_error,
        errors=state.errors,
        created_at=now,
        updated_at=now,
    )
