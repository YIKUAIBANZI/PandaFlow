"""Conservative deterministic triage against a demo rule matrix."""

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal

from pandaflow.shared.contracts import SkillResponse, SkillStatus
from pandaflow.shared.rules import load_json_resource
from pandaflow.skills.incident_triage_dispatch.schemas import IncidentRequest


class _Rule(BaseModel):
    rule_id: str
    category: Literal["medical", "missing_person", "lost_property", "ticketing", "order", "facility", "unknown"]
    priority: Literal["P0", "P1", "P2"]
    keywords: list[str] = Field(min_length=1)
    role: str


class _Rules(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    classification: Literal["demo"]
    source_refs: list[str] = Field(min_length=1)
    rules: list[_Rule] = Field(min_length=1)


def triage_incident(request: IncidentRequest) -> SkillResponse:
    """Return a routing draft; never diagnose, notify or confirm resolution."""
    missing = [name for name in ("description", "area") if not getattr(request, name)]
    if request.is_ongoing is None:
        missing.append("is_ongoing")
    try:
        resource = _Rules.model_validate(load_json_resource("incident_rules.json"))
    except (OSError, ValueError, ValidationError):
        return _response(
            "unknown", "P1", SkillStatus.ESCALATED, "现场人工核验岗位", missing,
            warnings=["事件规则不可用，按潜在风险转人工核验。"],
        )

    text = request.description.casefold()
    safety_text = "\n".join([request.description, request.area, *request.measures_taken]).casefold()
    matches = [
        rule for rule in resource.rules
        if any(word.casefold() in (safety_text if rule.priority in {"P0", "P1"} else text) for word in rule.keywords)
    ]
    if request.category_hint:
        matches.extend(rule for rule in resource.rules if rule.category == request.category_hint and rule.priority != "P0")
    if not matches:
        return _response(
            "unknown", None, SkillStatus.NEEDS_INPUT, "游客服务岗位", missing or ["description"],
            source_refs=resource.source_refs, version=resource.version,
        )
    selected = min(matches, key=lambda rule: rule.priority)
    urgent = selected.priority in {"P0", "P1"}
    priority = selected.priority if urgent or request.is_ongoing is not False else "P3"
    return _response(
        selected.category, priority, SkillStatus.ESCALATED if urgent else SkillStatus.OK,
        selected.role, missing, source_refs=resource.source_refs,
        rule_refs=list(dict.fromkeys(rule.rule_id for rule in matches)), version=resource.version,
    )


def _response(category, priority, status, role, missing, *, source_refs=None, rule_refs=None, version=None, warnings=None):
    actions = [f"请由{role}人工核实情况。"]
    if status is SkillStatus.ESCALATED:
        actions.insert(0, "暂停普通游览安排，立即寻求现场工作人员协助。")
    if missing:
        actions.append("补充事件位置、当前情况及是否仍在持续；潜在高风险事件的求助不应等待信息补齐。")
    return SkillResponse.create(
        skill="incident-triage-dispatch", status=status,
        data={
            "category": category, "priority": priority, "responsible_role": role,
            "immediate_actions": actions,
            "prohibited_actions": ["不得将草稿视为已派单或已通知。", "不得根据本结果作出诊断、治疗或事件已解决的判断。", "不要提交姓名、证件号、手机号等个人信息。"],
            "reply_template": f"此处仅生成处置建议，请联系{role}确认接手；尚未通知任何人员。",
            "dispatch_status": "draft", "sent": False, "missing_fields": missing,
            "rule_version": version,
        },
        source_refs=source_refs, rule_refs=rule_refs,
        warnings=["仅使用演示分诊矩阵，不代表园区正式流程；未发送工单。", *(warnings or [])],
        next_actions=actions, demo_data=True,
    )
