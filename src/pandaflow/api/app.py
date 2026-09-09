"""FastAPI application exposing the PandaFlow prototype."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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


app = FastAPI(title="PandaFlow", version="0.1.0")


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


@app.post("/api/v1/skills/operations-review")
def operations_review(request: ReviewRequest) -> SkillResponse:
    """Aggregate allowlisted execution metadata with record-level evidence."""
    return review_operations(request)


@app.post("/api/v1/skills/incident-triage-dispatch")
def incident_triage_dispatch(request: IncidentRequest) -> SkillResponse:
    """Produce an unsent incident-routing draft."""
    return triage_incident(request)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a dependency-free availability response."""

    return {"status": "ok"}


@app.post("/api/v1/skills/visitor-policy-check")
def visitor_policy_check(request: VisitorPolicyRequest) -> SkillResponse:
    """Expose the deterministic pre-visit policy Skill over HTTP."""

    return evaluate_policy(request)


@app.post("/api/v1/skills/accessible-itinerary-planner")
def accessible_itinerary_planner(request: ItineraryRequest) -> SkillResponse:
    """Expose the deterministic accessibility-aware itinerary Skill over HTTP."""

    return plan_itinerary(request)


@app.post("/api/v1/skills/welfare-risk-dispatcher")
def welfare_risk_dispatcher(request: RiskDispatchRequest) -> SkillResponse:
    """Expose deterministic demo-weather risk dispatch over HTTP."""

    return dispatch_risk(request)


@app.post("/api/v1/demo/run")
def demo_run(request: DemoRequest) -> SkillResponse:
    """Run the fixed PandaFlow dynamic-demo workflow."""

    return run_demo(request)


@app.post("/api/v1/skills/panda-knowledge-guard")
def panda_knowledge_guard(request: KnowledgeRequest) -> SkillResponse:
    """Expose source-bound panda knowledge retrieval over HTTP."""

    return answer_question(request)
