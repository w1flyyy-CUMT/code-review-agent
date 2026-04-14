"""pytest 工具封装。"""

from pathlib import Path

from review_agent.domain.models import ToolRunResult
from review_agent.tools.runner import PythonModuleToolRunner, has_test_directory


class PytestTool:
    """执行 pytest。"""

    def __init__(self) -> None:
        self._runner = PythonModuleToolRunner()

    def run(self, repo_path: Path, timeout_seconds: int = 60) -> ToolRunResult:
        if not has_test_directory(repo_path):
            return ToolRunResult(
                tool_name="pytest",
                command=[],
                success=True,
                skipped=True,
                summary="仓库中未找到测试目录，跳过 pytest",
            )

        return self._runner.run(
            module_name="pytest",
            args=["-q"],
            repo_path=repo_path,
            timeout_seconds=timeout_seconds,
        )
