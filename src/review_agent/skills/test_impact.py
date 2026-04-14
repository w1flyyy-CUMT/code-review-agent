"""测试影响分析 skill。"""

from review_agent.domain.enums import FindingSeverity
from review_agent.domain.models import Evidence, Finding
from review_agent.skills.base import SkillContext, SkillResult


class TestImpactSkill:
    """判断本次变更是否可能需要补充测试。"""

    skill_name = "test_impact_skill"

    async def run(self, ctx: SkillContext) -> SkillResult:
        has_python_code_change = any(
            changed_file.language == "python" for changed_file in ctx.changed_files
        )
        touches_tests = any(
            "test" in changed_file.path.lower() for changed_file in ctx.changed_files
        )

        if not has_python_code_change or touches_tests:
            return SkillResult(skill_name=self.skill_name)

        finding = Finding(
            title="核心代码变更未见测试文件改动",
            category="test",
            severity=FindingSeverity.MEDIUM,
            confidence=0.68,
            file_path=ctx.changed_files[0].path if ctx.changed_files else None,
            summary="当前 diff 涉及 Python 代码，但未检测到测试文件同步修改。",
            suggestion="建议确认现有测试是否覆盖新增分支，必要时补充针对性用例。",
            skill_name=self.skill_name,
            dedupe_key=(
                f"{ctx.changed_files[0].path if ctx.changed_files else 'unknown'}:test-impact"
            ),
            evidences=[
                Evidence(
                    source_type="diff_summary",
                    snippet="变更中未匹配到 tests/ 或 test_*.py 文件。",
                    score=0.68,
                    reason="基于文件路径启发式判断测试影响",
                )
            ],
        )
        return SkillResult(skill_name=self.skill_name, findings=[finding])
