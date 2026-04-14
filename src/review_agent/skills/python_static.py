"""Python 静态分析 skill。"""

from __future__ import annotations

from pathlib import Path

from anyio import Path as AsyncPath

from review_agent.domain.enums import FindingSeverity
from review_agent.domain.models import Evidence, Finding, ToolRunResult
from review_agent.skills.base import SkillContext, SkillResult
from review_agent.tools.mypy_tool import MypyTool
from review_agent.tools.pytest_tool import PytestTool
from review_agent.tools.ruff_tool import RuffTool


class PythonStaticSkill:
    """整合 Ruff、MyPy 和 pytest 的 Python 静态分析能力。"""

    skill_name = "python_static_skill"

    def __init__(self) -> None:
        self._ruff_tool = RuffTool()
        self._mypy_tool = MypyTool()
        self._pytest_tool = PytestTool()

    async def run(self, ctx: SkillContext) -> SkillResult:
        python_files = [
            changed_file.path
            for changed_file in ctx.changed_files
            if changed_file.language == "python"
        ]
        if not python_files:
            return SkillResult(skill_name=self.skill_name)

        repo_path = Path(ctx.repo_path)
        findings: list[Finding] = []
        tool_runs: list[ToolRunResult] = []

        if await AsyncPath(repo_path).exists():
            tool_runs.extend(self._run_real_tools(repo_path, python_files))
            findings.extend(self._build_tool_findings(ctx, tool_runs))
        else:
            tool_runs.append(
                ToolRunResult(
                    tool_name="python_static",
                    success=True,
                    skipped=True,
                    summary="仓库路径不存在，已降级为启发式分析",
                )
            )

        findings.extend(self._build_heuristic_findings(ctx))
        return SkillResult(
            skill_name=self.skill_name,
            findings=_deduplicate_findings(findings),
            tool_runs=tool_runs,
            raw_outputs={"python_files": python_files},
        )

    def _run_real_tools(self, repo_path: Path, python_files: list[str]) -> list[ToolRunResult]:
        return [
            self._ruff_tool.run(repo_path, python_files),
            self._mypy_tool.run(repo_path, python_files),
            self._pytest_tool.run(repo_path),
        ]

    def _build_tool_findings(
        self,
        ctx: SkillContext,
        tool_runs: list[ToolRunResult],
    ) -> list[Finding]:
        findings: list[Finding] = []
        first_python_file = _first_python_file(ctx)

        for tool_run in tool_runs:
            if tool_run.skipped or tool_run.success:
                continue

            if tool_run.tool_name == "ruff":
                findings.append(
                    Finding(
                        title="Ruff 检查未通过",
                        category="lint",
                        severity=FindingSeverity.MEDIUM,
                        confidence=0.91,
                        file_path=first_python_file,
                        summary=_truncate_output(tool_run.stdout or tool_run.stderr),
                        suggestion="建议根据 Ruff 输出修复代码规范或潜在问题。",
                        skill_name=self.skill_name,
                        dedupe_key=f"{first_python_file}:ruff",
                        evidences=[_tool_evidence(tool_run)],
                    )
                )
            elif tool_run.tool_name == "mypy":
                findings.append(
                    Finding(
                        title="MyPy 类型检查未通过",
                        category="typing",
                        severity=FindingSeverity.HIGH,
                        confidence=0.92,
                        file_path=first_python_file,
                        summary=_truncate_output(tool_run.stdout or tool_run.stderr),
                        suggestion="建议修正类型不一致问题，并补充必要的类型标注。",
                        skill_name=self.skill_name,
                        dedupe_key=f"{first_python_file}:mypy",
                        evidences=[_tool_evidence(tool_run)],
                    )
                )
            elif tool_run.tool_name == "pytest":
                findings.append(
                    Finding(
                        title="pytest 执行失败",
                        category="test",
                        severity=FindingSeverity.HIGH,
                        confidence=0.95,
                        file_path=first_python_file,
                        summary=_truncate_output(tool_run.stdout or tool_run.stderr),
                        suggestion="建议先修复失败测试，再评估本次代码变更是否可以合入。",
                        skill_name=self.skill_name,
                        dedupe_key=f"{first_python_file}:pytest",
                        evidences=[_tool_evidence(tool_run)],
                        needs_approval=True,
                    )
                )

        return findings

    def _build_heuristic_findings(self, ctx: SkillContext) -> list[Finding]:
        findings: list[Finding] = []
        lowered_diff = ctx.diff_text.lower()

        if "return x.name" in lowered_diff or ".name" in lowered_diff:
            first_python_file = _first_python_file(ctx)
            findings.append(
                Finding(
                    title="疑似缺少空值判断",
                    category="typing",
                    severity=FindingSeverity.MEDIUM,
                    confidence=0.72,
                    file_path=first_python_file,
                    summary="检测到新增属性访问，可能缺少 None 判断或类型约束。",
                    suggestion="建议补充显式空值判断，或通过类型标注限制输入类型。",
                    skill_name=self.skill_name,
                    dedupe_key=f"{first_python_file}:typing:none-handling",
                    evidences=[
                        Evidence(
                            source_type="heuristic",
                            source_id="python_static_rule",
                            snippet="发现新增属性访问表达式，且未见明显的前置判空逻辑。",
                            score=0.72,
                            reason="基于当前启发式规则判定",
                        )
                    ],
                )
            )

        return findings


def _first_python_file(ctx: SkillContext) -> str | None:
    for changed_file in ctx.changed_files:
        if changed_file.language == "python":
            return changed_file.path
    return None


def _tool_evidence(tool_run: ToolRunResult) -> Evidence:
    return Evidence(
        source_type="tool",
        source_id=tool_run.tool_name,
        snippet=_truncate_output(tool_run.stdout or tool_run.stderr),
        score=0.9 if not tool_run.skipped else 0.0,
        reason=tool_run.summary,
    )


def _truncate_output(content: str, limit: int = 240) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    unique: dict[tuple[str, str, str | None], Finding] = {}
    for finding in findings:
        key = (finding.title, finding.category, finding.file_path)
        unique.setdefault(key, finding)
    return list(unique.values())
