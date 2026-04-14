"""Skill 路由逻辑。"""

from review_agent.domain.models import ChangedFile


class SkillRouter:
    """根据变更特征选择需要执行的技能。"""

    def route(self, changed_files: list[ChangedFile]) -> list[str]:
        """返回本次任务应执行的技能列表。"""
        selected = {"diff_summary_skill"}

        has_python = any(changed_file.language == "python" for changed_file in changed_files)
        has_test_related = any(
            changed_file.file_type == "test"
            or "test" in changed_file.path.lower()
            or any(symbol.lower().startswith("function:test_") for symbol in changed_file.symbols)
            for changed_file in changed_files
        )
        has_high_risk = any(
            tag in {"auth", "permission", "migration", "delete", "database", "config"}
            for changed_file in changed_files
            for tag in changed_file.risk_tags
        )
        has_api_surface = any(
            "api" in changed_file.risk_tags
            or "public_api" in changed_file.risk_tags
            or any(symbol.lower().startswith("import:fastapi") for symbol in changed_file.symbols)
            for changed_file in changed_files
        )
        has_python_symbols = any(
            changed_file.language == "python" and bool(changed_file.symbols)
            for changed_file in changed_files
        )

        if has_python:
            selected.add("python_static_skill")

        if has_python or has_python_symbols or has_high_risk:
            selected.add("risk_pattern_skill")

        if has_test_related or has_python or has_high_risk or has_api_surface:
            selected.add("test_impact_skill")

        if has_high_risk or has_api_surface:
            selected.add("repo_policy_rag_skill")

        return sorted(selected)
