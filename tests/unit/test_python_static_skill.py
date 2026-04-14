"""Python 静态分析 skill 测试。"""

from review_agent.domain.models import ChangedFile
from review_agent.skills.base import SkillContext
from review_agent.skills.python_static import PythonStaticSkill


async def test_python_static_skill_falls_back_when_repo_missing() -> None:
    skill = PythonStaticSkill()
    context = SkillContext(
        task_id="rvw_test",
        repo_path="D:/not-exists-repo",
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

    assert result.tool_runs
    assert result.tool_runs[0].skipped is True
    assert "降级" in result.tool_runs[0].summary
    assert any(finding.title == "疑似缺少空值判断" for finding in result.findings)
