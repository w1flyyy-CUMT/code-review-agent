"""Diff 解析工具测试。"""

from review_agent.tools.git_diff_tool import GitDiffTool


def test_git_diff_tool_parse_python_file() -> None:
    diff_text = """diff --git a/app/demo.py b/app/demo.py
--- a/app/demo.py
+++ b/app/demo.py
@@ -1,1 +1,2 @@
+print("hello")
-print("world")
"""
    tool = GitDiffTool()

    changed_files = tool.parse(diff_text)

    assert len(changed_files) == 1
    assert changed_files[0].path == "app/demo.py"
    assert changed_files[0].language == "python"
    assert changed_files[0].added_lines == 1
    assert changed_files[0].deleted_lines == 1
    assert len(changed_files[0].hunks) == 1
    assert changed_files[0].hunks[0].old_start == 1
    assert changed_files[0].hunks[0].new_start == 1


def test_git_diff_tool_extracts_python_symbols_and_multiple_hunks() -> None:
    diff_text = """diff --git a/app/api/user.py b/app/api/user.py
--- a/app/api/user.py
+++ b/app/api/user.py
@@ -1,3 +1,7 @@ def build_router
 import fastapi
+from app.auth.service import AuthService
+
+class UserRouter:
+    pass
@@ -10,2 +14,4 @@ def load_user
-def old_handler():
-    return None
+def load_user(user_id: str) -> str:
+    return user_id
 """
    tool = GitDiffTool()

    changed_files = tool.parse(diff_text)

    assert len(changed_files) == 1
    changed_file = changed_files[0]
    assert changed_file.path == "app/api/user.py"
    assert changed_file.change_type == "modified"
    assert len(changed_file.hunks) == 2
    assert changed_file.hunks[0].header == "def build_router"
    assert changed_file.hunks[1].header == "def load_user"
    assert changed_file.symbols == [
        "import:fastapi",
        "import:app.auth.service",
        "class:UserRouter",
        "function:old_handler",
        "function:load_user",
    ]
