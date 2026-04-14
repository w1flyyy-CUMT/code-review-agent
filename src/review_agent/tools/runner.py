"""外部工具运行器。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from review_agent.domain.models import ToolRunResult


class PythonModuleToolRunner:
    """通过当前 Python 解释器执行工具模块。"""

    def run(
        self,
        module_name: str,
        args: list[str],
        repo_path: Path,
        timeout_seconds: int,
    ) -> ToolRunResult:
        command = [sys.executable, "-m", module_name, *args]

        try:
            completed = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            return ToolRunResult(
                tool_name=module_name,
                command=command,
                success=False,
                skipped=True,
                summary=f"未找到工具模块：{module_name}",
                stderr=str(exc),
            )
        except subprocess.TimeoutExpired as exc:
            return ToolRunResult(
                tool_name=module_name,
                command=command,
                success=False,
                exit_code=None,
                summary=f"{module_name} 执行超时",
                stdout=_normalize_output(exc.stdout),
                stderr=_normalize_output(exc.stderr),
            )

        return ToolRunResult(
            tool_name=module_name,
            command=command,
            success=completed.returncode == 0,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            summary=_build_summary(module_name, completed.returncode),
        )


def collect_existing_targets(repo_path: Path, targets: list[str]) -> list[str]:
    """筛选仓库中实际存在的目标路径。"""
    existing_targets: list[str] = []
    for target in targets:
        if (repo_path / target).exists():
            existing_targets.append(target)
    return existing_targets


def has_test_directory(repo_path: Path) -> bool:
    """判断仓库是否包含常见测试目录。"""
    return any((repo_path / candidate).exists() for candidate in ("tests", "test"))


def _build_summary(module_name: str, return_code: int) -> str:
    if return_code == 0:
        return f"{module_name} 执行成功"
    return f"{module_name} 执行失败，退出码 {return_code}"


def _normalize_output(content: bytes | str | None) -> str:
    if content is None:
        return ""
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    return content
