"""仓库规范检索 skill。"""

from review_agent.skills.base import SkillContext, SkillResult


class RepoPolicyRagSkill:
    """按需补充仓库规范依据。

    当前阶段先作为占位 skill，后续再接入真实 RAG。
    """

    skill_name = "repo_policy_rag_skill"

    async def run(self, ctx: SkillContext) -> SkillResult:
        warnings = []
        if ctx.changed_files:
            warnings.append("当前 RAG 能力尚未接入真实知识库，已跳过规范检索。")

        return SkillResult(
            skill_name=self.skill_name,
            findings=[],
            warnings=warnings,
            raw_outputs={"reason": "rag_not_enabled"},
        )
