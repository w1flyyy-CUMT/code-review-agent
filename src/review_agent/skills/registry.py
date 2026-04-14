"""Skill 注册表。"""

from review_agent.skills.base import ReviewSkill
from review_agent.skills.diff_summary import DiffSummarySkill
from review_agent.skills.python_static import PythonStaticSkill
from review_agent.skills.repo_policy_rag import RepoPolicyRagSkill
from review_agent.skills.risk_pattern import RiskPatternSkill
from review_agent.skills.test_impact import TestImpactSkill


class SkillRegistry:
    """维护所有可用的评审技能。"""

    def __init__(self) -> None:
        self._skills: dict[str, ReviewSkill] = {
            "diff_summary_skill": DiffSummarySkill(),
            "python_static_skill": PythonStaticSkill(),
            "risk_pattern_skill": RiskPatternSkill(),
            "test_impact_skill": TestImpactSkill(),
            "repo_policy_rag_skill": RepoPolicyRagSkill(),
        }

    def get(self, skill_name: str) -> ReviewSkill:
        """获取指定 skill。"""
        return self._skills[skill_name]
