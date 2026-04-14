"""风险模式识别 skill。"""

from review_agent.domain.enums import FindingSeverity
from review_agent.domain.models import Evidence, Finding
from review_agent.skills.base import SkillContext, SkillResult


class RiskPatternSkill:
    """识别高风险编码模式。"""

    skill_name = "risk_pattern_skill"

    async def run(self, ctx: SkillContext) -> SkillResult:
        findings: list[Finding] = []
        lowered_diff = ctx.diff_text.lower()

        if "except exception" in lowered_diff and "pass" in lowered_diff:
            findings.append(
                Finding(
                    title="异常被直接吞掉",
                    category="reliability",
                    severity=FindingSeverity.HIGH,
                    confidence=0.86,
                    file_path=_first_file_path(ctx),
                    summary="检测到 `except Exception: pass` 模式，可能掩盖真实错误。",
                    suggestion="建议记录日志并显式处理异常，避免静默失败。",
                    skill_name=self.skill_name,
                    dedupe_key=f"{_first_file_path(ctx)}:reliability:except-pass",
                    evidences=[
                        Evidence(
                            source_type="diff",
                            snippet="except Exception:\n    pass",
                            score=0.86,
                            reason="检测到高风险异常处理模式",
                        )
                    ],
                    needs_approval=True,
                )
            )

        return SkillResult(skill_name=self.skill_name, findings=findings)


def _first_file_path(ctx: SkillContext) -> str | None:
    return ctx.changed_files[0].path if ctx.changed_files else None
