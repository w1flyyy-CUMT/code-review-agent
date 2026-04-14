"""MyPy 工具封装。"""

from pathlib import Path

from review_agent.domain.models import ToolRunResult
from review_agent.tools.runner import PythonModuleToolRunner, collect_existing_targets


class MypyTool:
    """执行 MyPy 检查。"""

    def __init__(self) -> None:
        self._runner = PythonModuleToolRunner()

    def run(self, repo_path: Path, targets: list[str], timeout_seconds: int = 30) -> ToolRunResult:
        existing_targets = collect_existing_targets(repo_path, targets)
        if not existing_targets:
            return ToolRunResult(
                tool_name="mypy",
                command=[],
                success=True,
                skipped=True,
                summary="未找到可执行 MyPy 检查的 Python 文件",
            )

        return self._runner.run(
            module_name="mypy",
            args=existing_targets,
            repo_path=repo_path,
            timeout_seconds=timeout_seconds,
        )
