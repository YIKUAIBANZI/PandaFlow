from pathlib import Path

from pandaflow.api.app import app


ROOT = Path(__file__).resolve().parents[2]
API_DOCUMENT = ROOT / "docs" / "PandaFlow-API接口文档.md"
WORKHUB_RUNBOOK = ROOT / "docs" / "workhub-integration-runbook.md"


def test_api_document_covers_every_openapi_operation_and_workhub_boundary():
    content = API_DOCUMENT.read_text(encoding="utf-8")
    openapi = app.openapi()

    for path, operations in openapi["paths"].items():
        for method in operations:
            assert f"`{method.upper()} {path}`" in content

    for required_topic in (
        "统一响应包络",
        "状态语义",
        "校验错误",
        "安全降级",
        "WorkHub 字段映射",
        "未完成边界",
        "demo_data",
    ):
        assert required_topic in content


def test_api_document_names_all_six_independent_skills():
    content = API_DOCUMENT.read_text(encoding="utf-8")

    skill_names = (
        "visitor-policy-check",
        "accessible-itinerary-planner",
        "panda-knowledge-guard",
        "welfare-risk-dispatcher",
        "incident-triage-dispatch",
        "operations-review",
    )
    assert all(f"`{skill}`" in content for skill in skill_names)


def test_public_docs_use_the_typed_openapi_contract_and_real_route_field():
    api_document = API_DOCUMENT.read_text(encoding="utf-8")
    workhub_runbook = WORKHUB_RUNBOOK.read_text(encoding="utf-8")

    assert "七类精确响应模型" in api_document
    assert "仍是通用 object" not in api_document
    assert "`data.itinerary`" in workhub_runbook
    assert "`data.route`" not in workhub_runbook
