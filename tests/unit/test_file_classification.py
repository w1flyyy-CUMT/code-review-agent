"""parse_input 节点测试。"""

from review_agent.agent.nodes import parse_input_node
from review_agent.agent.state import AgentState


async def test_parse_input_node_parses_changed_files_and_infers_tags() -> None:
    state = AgentState(
        task_id="rvw_parse_input",
        repo_path="D:/demo/repo",
        diff_text=(
            "diff --git a/app/api/user.py b/app/api/user.py\n"
            "--- a/app/api/user.py\n"
            "+++ b/app/api/user.py\n"
            "@@ -10,2 +10,4 @@ def delete_user\n"
            "+from sqlalchemy import select\n"
            "+from fastapi import APIRouter\n"
            "+def delete_user(user_id: str) -> None:\n"
            "+    return None\n"
        ),
    )

    result = await parse_input_node(state)

    assert result.current_node == "parse_input"
    assert len(result.changed_files) == 1

    changed_file = result.changed_files[0]
    assert changed_file.path == "app/api/user.py"
    assert changed_file.language == "python"
    assert changed_file.file_type == "code"
    assert changed_file.hunks[0].header == "def delete_user"
    assert changed_file.risk_tags == ["database", "api", "public_api", "delete"]


async def test_parse_input_node_marks_test_file_by_symbol_name() -> None:
    state = AgentState(
        task_id="rvw_parse_input_test",
        repo_path="D:/demo/repo",
        diff_text=(
            "diff --git a/app/checks.py b/app/checks.py\n"
            "--- a/app/checks.py\n"
            "+++ b/app/checks.py\n"
            "@@ -1,0 +1,2 @@\n"
            "+def test_login_flow():\n"
            "+    assert True\n"
        ),
    )

    result = await parse_input_node(state)

    changed_file = result.changed_files[0]
    assert changed_file.file_type == "test"
    assert changed_file.risk_tags == ["test"]
