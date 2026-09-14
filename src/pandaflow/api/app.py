"""FastAPI application exposing the PandaFlow prototype."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pandaflow.api.demo_scenarios import load_demo_scenarios
from pandaflow.api.response_models import (
    DemoResponse,
    IncidentResponse,
    ItineraryResponse,
    KnowledgeResponse,
    OperationsReviewResponse,
    RiskDispatchResponse,
    VisitorPolicyResponse,
)
from pandaflow.skills.incident_triage_dispatch.schemas import IncidentRequest
from pandaflow.skills.incident_triage_dispatch.service import triage_incident
from pandaflow.skills.operations_review.schemas import ReviewRequest
from pandaflow.skills.operations_review.service import review_operations

from pandaflow.shared.contracts import SkillResponse
from pandaflow.orchestrator.service import DemoRequest, run_demo
from pandaflow.skills.panda_knowledge_guard.schemas import KnowledgeRequest
from pandaflow.skills.panda_knowledge_guard.service import answer_question
from pandaflow.skills.accessible_itinerary_planner.schemas import ItineraryRequest
from pandaflow.skills.accessible_itinerary_planner.service import plan_itinerary
from pandaflow.skills.visitor_policy_check.schemas import VisitorPolicyRequest
from pandaflow.skills.visitor_policy_check.service import evaluate_policy
from pandaflow.skills.welfare_risk_dispatcher.schemas import RiskDispatchRequest
from pandaflow.skills.welfare_risk_dispatcher.service import dispatch_risk
from pandaflow.shared.rules import ResourceLoadError, load_json_resource


app = FastAPI(title="PandaFlow", version="0.1.0")
WEB_DIRECTORY = Path(__file__).resolve().parents[1] / "web"
REQUIRED_RESOURCE_FILES = (
    "demo_scenarios.json",
    "incident_rules.json",
    "knowledge_cards.json",
    "park_graph.json",
    "review_rules.json",
    "source_registry.json",
    "visitor_rules.json",
    "weather_config.json",
    "welfare_rules.json",
)
REQUIRED_WEB_FILES = ("index.html", "app.js", "styles.css", "view-model.js")
app.mount(
    "/demo/assets",
    StaticFiles(directory=WEB_DIRECTORY),
    name="demo-assets",
)


@app.exception_handler(RequestValidationError)
async def private_validation_error(_request, exc: RequestValidationError) -> JSONResponse:
    """Do not reflect submitted values or user-controlled field names."""
    return JSONResponse(
        status_code=422,
        content={"detail": [
            {"type": error["type"], "msg": "请求字段不符合输入约束，请参阅接口文档。"}
            for error in exc.errors()
        ]},
    )


@app.exception_handler(OSError)
@app.exception_handler(ResourceLoadError)
async def resource_unavailable_error(_request, _exc) -> JSONResponse:
    """Return a stable error without exposing resource paths or contents."""

    return JSONResponse(
        status_code=503,
        content={"detail": "运行资源暂时不可用。"},
    )


@app.get("/demo", include_in_schema=False)
def demo_page() -> FileResponse:
    """Serve the judge-facing demonstration shell."""

    return FileResponse(WEB_DIRECTORY / "index.html")


@app.get("/api/v1/demo/scenarios")
def demo_scenarios() -> dict:
    """Return the allowlisted demo catalog without leaking resource errors."""

    try:
        return load_demo_scenarios()
    except (OSError, ResourceLoadError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="演示场景暂时不可用。",
        ) from exc


@app.post(
    "/api/v1/skills/operations-review",
    response_model=OperationsReviewResponse,
    response_model_exclude_unset=True,
)
def operations_review(request: ReviewRequest) -> SkillResponse:
    """Aggregate allowlisted execution metadata with record-level evidence."""
    return review_operations(request)


@app.post(
    "/api/v1/skills/incident-triage-dispatch",
    response_model=IncidentResponse,
    response_model_exclude_unset=True,
)
def incident_triage_dispatch(request: IncidentRequest) -> SkillResponse:
    """Produce an unsent incident-routing draft."""
    return triage_incident(request)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a dependency-free availability response."""

    return {"status": "ok"}


@app.get("/ready")
def readiness() -> dict[str, str]:
    """Check that packaged rules and judge-facing assets are readable."""

    try:
        for filename in REQUIRED_RESOURCE_FILES:
            load_json_resource(filename)
        if not all((WEB_DIRECTORY / filename).is_file() for filename in REQUIRED_WEB_FILES):
            raise FileNotFoundError("required Web asset is unavailable")
    except (OSError, ResourceLoadError, ValueError, TypeError):
        raise HTTPException(
            status_code=503,
            detail="运行资源暂时不可用。",
        ) from None
    return {"status": "ready"}


@app.post(
    "/api/v1/skills/visitor-policy-check",
    response_model=VisitorPolicyResponse,
    response_model_exclude_unset=True,
)
def visitor_policy_check(request: VisitorPolicyRequest) -> SkillResponse:
    """Expose the deterministic pre-visit policy Skill over HTTP."""

    return evaluate_policy(request)


@app.post(
    "/api/v1/skills/accessible-itinerary-planner",
    response_model=ItineraryResponse,
    response_model_exclude_unset=True,
)
def accessible_itinerary_planner(request: ItineraryRequest) -> SkillResponse:
    """Expose the deterministic accessibility-aware itinerary Skill over HTTP."""

    return plan_itinerary(request)


@app.post(
    "/api/v1/skills/welfare-risk-dispatcher",
    response_model=RiskDispatchResponse,
    response_model_exclude_unset=True,
)
def welfare_risk_dispatcher(request: RiskDispatchRequest) -> SkillResponse:
    """Expose deterministic demo-weather risk dispatch over HTTP."""

    return dispatch_risk(request)


@app.post(
    "/api/v1/demo/run",
    response_model=DemoResponse,
    response_model_exclude_unset=True,
)
def demo_run(request: DemoRequest) -> SkillResponse:
    """Run the fixed PandaFlow dynamic-demo workflow."""

    return run_demo(request)


@app.post(
    "/api/v1/skills/panda-knowledge-guard",
    response_model=KnowledgeResponse,
    response_model_exclude_unset=True,
)
def panda_knowledge_guard(request: KnowledgeRequest) -> SkillResponse:
    """Expose source-bound panda knowledge retrieval over HTTP."""

    return answer_question(request)
