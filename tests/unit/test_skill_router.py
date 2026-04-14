"""SkillRouter 路由规则测试。"""

from review_agent.domain.models import ChangedFile
from review_agent.skills.router import SkillRouter


def test_skill_router_defaults_to_diff_summary() -> None:
    router = SkillRouter()

    selected = router.route([])

    assert selected == ["diff_summary_skill"]


def test_skill_router_selects_python_related_skills() -> None:
    router = SkillRouter()
    changed_files = [
        ChangedFile(
            path="app/service/user.py",
            language="python",
            change_type="modified",
            added_lines=12,
            deleted_lines=3,
        )
    ]

    selected = router.route(changed_files)

    assert selected == [
        "diff_summary_skill",
        "python_static_skill",
        "risk_pattern_skill",
        "test_impact_skill",
    ]


def test_skill_router_selects_test_and_high_risk_skills() -> None:
    router = SkillRouter()
    changed_files = [
        ChangedFile(
            path="tests/test_auth_flow.py",
            language="python",
            change_type="modified",
            added_lines=8,
            deleted_lines=1,
            risk_tags=["auth"],
        ),
        ChangedFile(
            path="docs/changelog.md",
            language="markdown",
            change_type="modified",
            added_lines=4,
            deleted_lines=0,
        ),
    ]

    selected = router.route(changed_files)

    assert selected == [
        "diff_summary_skill",
        "python_static_skill",
        "repo_policy_rag_skill",
        "risk_pattern_skill",
        "test_impact_skill",
    ]


def test_skill_router_uses_symbols_for_api_surface_routing() -> None:
    router = SkillRouter()
    changed_files = [
        ChangedFile(
            path="app/web/handlers.py",
            language="python",
            change_type="modified",
            symbols=["import:fastapi", "function:create_user"],
        )
    ]

    selected = router.route(changed_files)

    assert selected == [
        "diff_summary_skill",
        "python_static_skill",
        "repo_policy_rag_skill",
        "risk_pattern_skill",
        "test_impact_skill",
    ]
