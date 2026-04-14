"""Diff 解析工具。"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from review_agent.domain.models import ChangedFile, Hunk

# 匹配 Git diff 的文件头，例如：
# diff --git a/src/foo.py b/src/foo.py
_DIFF_HEADER_RE = re.compile(r"^diff --git a/(?P<old>.+) b/(?P<new>.+)$")

# 匹配 hunk 头，例如：
# @@ -10,3 +10,5 @@ def parse():
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?: (?P<header>.*))?$"
)

# 以下正则仅用于 Python 文件的简单 symbol 提取
_PYTHON_DEF_RE = re.compile(r"^\s*def\s+(?P<name>[A-Za-z_]\w*)\s*\(")
_PYTHON_CLASS_RE = re.compile(r"^\s*class\s+(?P<name>[A-Za-z_]\w*)\b")
_PYTHON_FROM_IMPORT_RE = re.compile(r"^\s*from\s+(?P<module>[A-Za-z_][\w\.]*)\s+import\b")
_PYTHON_IMPORT_RE = re.compile(r"^\s*import\s+(?P<modules>[A-Za-z_][\w\.,\s]*)$")


class GitDiffTool:
    """解析 Git diff 文本。"""

    def parse(self, diff_text: str) -> list[ChangedFile]:
        """从 diff 文本中提取变更文件列表。"""
        files: list[ChangedFile] = []

        # 当前正在解析的文件状态。
        # 整个 parse 的实现本质上是“逐行扫描 + 维护当前文件上下文”。
        current_old_path: str | None = None
        current_new_path: str | None = None
        current_change_type = "modified"
        current_added_lines = 0
        current_deleted_lines = 0
        current_hunks: list[Hunk] = []
        current_symbols: list[str] = []
        seen_symbols: set[str] = set()

        def flush_current() -> None:
            """将当前累计的文件状态写入结果列表，并重置状态。

            每当遇到下一个 `diff --git` 文件头，或者循环结束时，
            都需要调用一次该函数，把“当前文件”落盘到 files 中。
            """
            nonlocal current_old_path, current_new_path, current_change_type
            nonlocal current_added_lines, current_deleted_lines, current_hunks
            nonlocal current_symbols, seen_symbols

            current_path = _resolve_current_path(current_old_path, current_new_path)
            if current_path is None:
                return

            files.append(
                ChangedFile(
                    path=current_path,
                    language=_guess_language(current_path),
                    change_type=current_change_type,
                    added_lines=current_added_lines,
                    deleted_lines=current_deleted_lines,
                    hunks=list(current_hunks),
                    symbols=list(current_symbols),
                )
            )

            # 重置当前文件状态，准备解析下一个文件
            current_old_path = None
            current_new_path = None
            current_change_type = "modified"
            current_added_lines = 0
            current_deleted_lines = 0
            current_hunks = []
            current_symbols = []
            seen_symbols = set()

        for line in diff_text.splitlines():
            # 1) 新文件 diff 开始：
            # 先把上一个文件刷入结果，再初始化当前文件路径。
            diff_header_match = _DIFF_HEADER_RE.match(line)
            if diff_header_match is not None:
                flush_current()
                current_old_path = diff_header_match.group("old")
                current_new_path = diff_header_match.group("new")
                current_change_type = "modified"
                continue

            # 2) Git diff 元信息：新增/删除文件
            if line.startswith("new file mode "):
                current_change_type = "added"
                continue

            if line.startswith("deleted file mode "):
                current_change_type = "deleted"
                continue

            # 3) 解析旧路径标记：
            # --- /dev/null 代表旧文件不存在，说明这是新增文件
            if line.startswith("--- "):
                marker_path = _parse_diff_path(line.removeprefix("--- ").strip())
                if marker_path is None:
                    current_change_type = "added"
                else:
                    current_old_path = marker_path
                continue

            # 4) 解析新路径标记：
            # +++ /dev/null 代表新文件不存在，说明这是删除文件
            if line.startswith("+++ "):
                marker_path = _parse_diff_path(line.removeprefix("+++ ").strip())
                if marker_path is None:
                    current_change_type = "deleted"
                else:
                    current_new_path = marker_path
                continue

            # 5) 解析 hunk 头，记录该文件的 diff 片段范围
            hunk_match = _HUNK_HEADER_RE.match(line)
            if hunk_match is not None:
                current_hunks.append(
                    Hunk(
                        old_start=int(hunk_match.group("old_start")),
                        old_count=int(hunk_match.group("old_count") or "1"),
                        new_start=int(hunk_match.group("new_start")),
                        new_count=int(hunk_match.group("new_count") or "1"),
                        header=hunk_match.group("header") or None,
                    )
                )
                continue

            # 还没解析出文件路径时，无法继续统计语言和 symbols
            current_path = _resolve_current_path(current_old_path, current_new_path)
            if current_path is None:
                continue

            language = _guess_language(current_path)

            # 6) 统计新增/删除行，并尝试提取 symbols
            # 注意排除 +++ / --- 这种路径标记行
            if line.startswith("+") and not line.startswith("+++"):
                current_added_lines += 1
                _collect_symbols(line[1:], language, current_symbols, seen_symbols)
            elif line.startswith("-") and not line.startswith("---"):
                current_deleted_lines += 1
                _collect_symbols(line[1:], language, current_symbols, seen_symbols)
            elif line.startswith(" "):
                # 上下文行虽然不计入增删统计，但仍可能包含函数/类定义，
                # 因此也尝试提取 symbol，帮助后续路由和风险分析。
                _collect_symbols(line[1:], language, current_symbols, seen_symbols)

        # 循环结束后，别漏掉最后一个文件
        flush_current()

        if files:
            return files

        # 兜底逻辑：
        # 当 diff 文本不是标准的 `diff --git` 格式时，至少返回一个伪文件对象，
        # 让后续流程还能拿到基础的增删行统计，不至于整个链路报错。
        return [
            ChangedFile(
                path="unknown.patch",
                language="unknown",
                change_type="modified",
                added_lines=sum(
                    1
                    for line in diff_text.splitlines()
                    if line.startswith("+") and not line.startswith("+++")
                ),
                deleted_lines=sum(
                    1
                    for line in diff_text.splitlines()
                    if line.startswith("-") and not line.startswith("---")
                ),
            )
        ]


def _resolve_current_path(old_path: str | None, new_path: str | None) -> str | None:
    """解析当前文件路径。

    优先返回 new_path：
    - 修改文件：通常新旧路径一致
    - 重命名/移动文件：新路径更符合“当前文件”语义
    - 新增文件：只有新路径
    - 删除文件：没有新路径时回退到旧路径
    """
    if new_path is not None:
        return new_path
    return old_path


def _parse_diff_path(raw_path: str) -> str | None:
    """规范化 diff 中的路径表示。

    - /dev/null 表示文件不存在
    - a/xxx 或 b/xxx 是 Git diff 的展示前缀，去掉后返回真实相对路径
    """
    if raw_path == "/dev/null":
        return None
    if raw_path.startswith("a/") or raw_path.startswith("b/"):
        return raw_path[2:]
    return raw_path


def _collect_symbols(
    line: str,
    language: str,
    symbols: list[str],
    seen_symbols: set[str],
) -> None:
    """从单行代码中提取简化后的 symbol 信息。

    当前仅支持 Python，提取内容包括：
    - class: 类定义
    - function: 函数定义
    - import: 导入模块

    这里用正则而不是 AST，是为了在 diff 场景下保持实现轻量、鲁棒。
    """
    if language != "python":
        return

    normalized_line = line.rstrip()
    discovered: list[str] = []

    class_match = _PYTHON_CLASS_RE.match(normalized_line)
    if class_match is not None:
        discovered.append(f"class:{class_match.group('name')}")

    function_match = _PYTHON_DEF_RE.match(normalized_line)
    if function_match is not None:
        discovered.append(f"function:{function_match.group('name')}")

    from_import_match = _PYTHON_FROM_IMPORT_RE.match(normalized_line)
    if from_import_match is not None:
        discovered.append(f"import:{from_import_match.group('module')}")

    import_match = _PYTHON_IMPORT_RE.match(normalized_line)
    if import_match is not None:
        modules = [
            module.strip()
            for module in import_match.group("modules").split(",")
            if module.strip()
        ]
        discovered.extend(f"import:{module}" for module in modules)

    # 去重后保留发现顺序，便于后续展示和路由使用
    for symbol in discovered:
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        symbols.append(symbol)


def _guess_language(path: str) -> str:
    """根据文件后缀猜测语言类型。"""
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix in {".yml", ".yaml"}:
        return "yaml"
    if suffix == ".md":
        return "markdown"
    if suffix == ".toml":
        return "toml"
    if suffix == ".json":
        return "json"
    if suffix in {".sql"}:
        return "sql"
    return "unknown"
