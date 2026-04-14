"""文件分类节点测试。"""

from review_agent.agent.nodes import classify_files_node
from review_agent.agent.state import AgentState
from review_agent.domain.models import ChangedFile, Hunk


async def test_classify_files_node_uses_symbols_and_hunks_to_add_tags() -> None:
    state = AgentState(
        task_id="rvw_classify",
        repo_path="D:/demo/repo",
        diff_text="diff --git a/app/api/user.py b/app/api/user.py",
        changed_files=[
            ChangedFile(
                path="app/api/user.py",
                language="python",
                change_type="modified",
                hunks=[
                    Hunk(
                        old_start=10,
                        old_count=2,
                        new_start=10,
                        new_count=4,
                        header="def delete_user",
                    )
                ],
                symbols=[
                    "import:fastapi",
                    "import:sqlalchemy",
                    "function:delete_user",
                ],
            )
        ],
    )

    result = await classify_files_node(state)

    changed_file = result.changed_files[0]
    assert changed_file.file_type == "code"
    assert changed_file.risk_tags == ["database", "api", "public_api", "delete"]


async def test_classify_files_node_marks_test_file_by_symbol_name() -> None:
    state = AgentState(
        task_id="rvw_classify_test",
        repo_path="D:/demo/repo",
        diff_text="diff --git a/app/checks.py b/app/checks.py",
        changed_files=[
            ChangedFile(
                path="app/checks.py",
                language="python",
                change_type="modified",
                symbols=["function:test_login_flow"],
            )
        ],
    )

    result = await classify_files_node(state)

    changed_file = result.changed_files[0]
    assert changed_file.file_type == "test"
    assert changed_file.risk_tags == ["test"]
