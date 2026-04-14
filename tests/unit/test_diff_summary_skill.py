"""变更摘要 skill 测试。"""

from review_agent.domain.models import ChangedFile
from review_agent.skills.base import SkillContext
from review_agent.skills.diff_summary import DiffSummarySkill


async def test_diff_summary_skill_falls_back_when_bailian_not_configured() -> None:
    skill = DiffSummarySkill()
    skill._llm_client._client = None
    context = SkillContext(
        task_id="rvw_summary",
        repo_path="D:/demo/repo",
        diff_text=(
            "diff --git a/app/service/user.py b/app/service/user.py\n"
            "--- a/app/service/user.py\n"
            "+++ b/app/service/user.py\n"
            "@@ -1,1 +1,3 @@\n"
            "+def load_user_name(user):\n"
            "+    return user.name\n"
        ),
        changed_files=[
            ChangedFile(
                path="app/service/user.py",
                language="python",
                change_type="modified",
                added_lines=2,
                deleted_lines=0,
            )
        ],
    )

    result = await skill.run(context)

    assert result.findings
    assert result.raw_outputs["summary_source"] == "fallback"
    assert result.warnings
