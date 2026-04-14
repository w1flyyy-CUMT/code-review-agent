"""评审接口集成测试。"""

from fastapi.testclient import TestClient

from review_agent.agent.graph import build_resume_graph, build_review_graph
from review_agent.api.deps import get_approval_service, get_review_service
from review_agent.application.approval_service import ApprovalService
from review_agent.application.review_service import ReviewService
from review_agent.main import app
from review_agent.repository.review_task_repo import InMemoryReviewTaskRepository


def _create_test_client() -> TestClient:
    repository = InMemoryReviewTaskRepository()
    review_service = ReviewService(repository=repository, graph=build_review_graph())
    approval_service = ApprovalService(repository=repository, resume_graph=build_resume_graph())

    app.dependency_overrides[get_review_service] = lambda: review_service
    app.dependency_overrides[get_approval_service] = lambda: approval_service
    return TestClient(app)


def test_create_review_returns_structured_report() -> None:
    client = _create_test_client()

    try:
        response = client.post(
            "/reviews",
            json={
                "repo_path": "D:/demo/repo",
                "diff_text": (
                    "diff --git a/app/service/user.py b/app/service/user.py\n"
                    "--- a/app/service/user.py\n"
                    "+++ b/app/service/user.py\n"
                    "@@ -1,1 +1,3 @@\n"
                    "+def load_user_name(user):\n"
                    "+    return user.name\n"
                ),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["task_id"].startswith("rvw_")
    assert payload["status"] == "completed"
    assert payload["approval_required"] is False
    assert payload["approval_status"] == "not_required"
    assert payload["trace_id"].startswith("trc_")
    assert "代码评审报告" in payload["report_markdown"]
    assert isinstance(payload["findings"], list)


def test_submit_approval_can_resume_review() -> None:
    client = _create_test_client()

    try:
        create_response = client.post(
            "/reviews",
            json={
                "repo_path": "D:/demo/repo",
                "diff_text": (
                    "diff --git a/app/service/user.py b/app/service/user.py\n"
                    "--- a/app/service/user.py\n"
                    "+++ b/app/service/user.py\n"
                    "@@ -1,1 +1,4 @@\n"
                    "+try:\n"
                    "+    work()\n"
                    "+except Exception:\n"
                    "+    pass\n"
                ),
            },
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["status"] == "waiting_approval"
        assert created["approval_required"] is True
        assert created["approval_status"] == "pending"
        assert created["current_node"] == "approval_gate"
        assert created["next_action"] == "submit_approval"
        assert created["waiting_reason"] == "存在高风险问题，需要人工审批"
        assert created["trace_id"].startswith("trc_")

        approve_response = client.post(
            f"/reviews/{created['task_id']}/approvals",
            json={"decision": "approve", "comment": "确认发布该高风险提示"},
        )
    finally:
        app.dependency_overrides.clear()

    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["status"] == "completed"
    assert approved["approval_required"] is True
    assert approved["approval_status"] == "approved"
    assert approved["trace_id"].startswith("trc_")
    assert "代码评审报告" in approved["report_markdown"]
