"""Diff 解析工具。"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from src.review_agent.domain.models import ChangedFile, Hunk

_DIFF_HEADER_RE = re.compile(r"^diff --git a/(?P<old>.+) b/(?P<new>.+)$")
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?: (?P<header>.*))?$"
)
_PYTHON_DEF_RE = re.compile(r"^\s*def\s+(?P<name>[A-Za-z_]\w*)\s*\(")
_PYTHON_CLASS_RE = re.compile(r"^\s*class\s+(?P<name>[A-Za-z_]\w*)\b")
_PYTHON_FROM_IMPORT_RE = re.compile(r"^\s*from\s+(?P<module>[A-Za-z_][\w\.]*)\s+import\b")
_PYTHON_IMPORT_RE = re.compile(r"^\s*import\s+(?P<modules>[A-Za-z_][\w\.,\s]*)$")


class GitDiffTool:
    """解析 Git diff 文本。"""

    def parse(self, diff_text: str) -> list[ChangedFile]:
        """从 diff 文本中提取变更文件列表。"""
        files: list[ChangedFile] = []

        current_old_path: str | None = None
        current_new_path: str | None = None
        current_change_type = "modified"
        current_added_lines = 0
        current_deleted_lines = 0
        current_hunks: list[Hunk] = []
        current_symbols: list[str] = []
        seen_symbols: set[str] = set()

        def flush_current() -> None:
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

            current_old_path = None
            current_new_path = None
            current_change_type = "modified"
            current_added_lines = 0
            current_deleted_lines = 0
            current_hunks = []
            current_symbols = []
            seen_symbols = set()

        for line in diff_text.splitlines():
            diff_header_match = _DIFF_HEADER_RE.match(line)
            if diff_header_match is not None:
                flush_current()
                current_old_path = diff_header_match.group("old")
                current_new_path = diff_header_match.group("new")
                current_change_type = "modified"
                continue

            if line.startswith("new file mode "):
                current_change_type = "added"
                continue

            if line.startswith("deleted file mode "):
                current_change_type = "deleted"
                continue

            if line.startswith("--- "):
                marker_path = _parse_diff_path(line.removeprefix("--- ").strip())
                if marker_path is None:
                    current_change_type = "added"
                else:
                    current_old_path = marker_path
                continue

            if line.startswith("+++ "):
                marker_path = _parse_diff_path(line.removeprefix("+++ ").strip())
                if marker_path is None:
                    current_change_type = "deleted"
                else:
                    current_new_path = marker_path
                continue

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

            current_path = _resolve_current_path(current_old_path, current_new_path)
            if current_path is None:
                continue

            language = _guess_language(current_path)
            if line.startswith("+") and not line.startswith("+++"):
                current_added_lines += 1
                _collect_symbols(line[1:], language, current_symbols, seen_symbols)
            elif line.startswith("-") and not line.startswith("---"):
                current_deleted_lines += 1
                _collect_symbols(line[1:], language, current_symbols, seen_symbols)
            elif line.startswith(" "):
                _collect_symbols(line[1:], language, current_symbols, seen_symbols)

        flush_current()

        if files:
            return files

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
    if new_path is not None:
        return new_path
    return old_path


def _parse_diff_path(raw_path: str) -> str | None:
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

    for symbol in discovered:
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        symbols.append(symbol)


def _guess_language(path: str) -> str:
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
