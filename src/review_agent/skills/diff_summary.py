"""变更摘要 skill。"""

from review_agent.domain.enums import FindingSeverity
from review_agent.domain.models import Evidence, Finding
from review_agent.llm.bailian_client import BailianChatClient
from review_agent.skills.base import SkillContext, SkillResult


class DiffSummarySkill:
    """生成变更摘要与影响说明。"""

    skill_name = "diff_summary_skill"

    def __init__(self) -> None:
        self._llm_client = BailianChatClient()

    async def run(self, ctx: SkillContext) -> SkillResult:
        changed_count = len(ctx.changed_files)
        summary = (
            f"本次变更共涉及 {changed_count} 个文件，"
            "建议优先关注核心业务路径、异常分支和测试覆盖情况。"
        )
        suggestion = "建议先确认受影响模块，再结合测试结果评估是否存在回归风险。"
        summary_source = "fallback"
        warnings: list[str] = []

        if self._llm_client.enabled:
            try:
                llm_result = await self._llm_client.summarize_diff(
                    changed_files=ctx.changed_files,
                    diff_text=ctx.diff_text,
                )
            except RuntimeError as exc:
                warnings.append(str(exc))
            else:
                if llm_result is not None:
                    summary = llm_result.summary
                    suggestion = llm_result.suggestion
                    summary_source = f"bailian:{llm_result.model_name}"
        else:
            warnings.append("未配置百炼 API Key，已使用本地回退摘要。")

        finding = Finding(
            title="变更摘要",
            category="summary",
            severity=FindingSeverity.LOW,
            confidence=0.95 if summary_source != "fallback" else 0.8,
            summary=summary,
            suggestion=suggestion,
            skill_name=self.skill_name,
            dedupe_key=f"summary:{changed_count}",
            evidences=[
                Evidence(
                    source_type="diff",
                    snippet=ctx.diff_text[:200] or "未提供 diff 内容",
                    reason="来自原始代码变更内容",
                )
            ],
        )
        return SkillResult(
            skill_name=self.skill_name,
            findings=[finding],
            raw_outputs={"summary_source": summary_source},
            warnings=warnings,
        )
