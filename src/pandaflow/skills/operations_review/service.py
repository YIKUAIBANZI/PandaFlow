"""Aggregate execution metadata without making causal or outcome claims."""

from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from pandaflow.shared.contracts import SkillResponse, SkillStatus
from pandaflow.shared.rules import load_json_resource
from pandaflow.skills.operations_review.schemas import ExecutionRecord, ReviewRequest


class _Rules(BaseModel):
    version: str
    classification: Literal["demo"]
    rule_id: str
    source_refs: list[str] = Field(min_length=1)
    status_actions: dict[str, str]


def review_operations(request: ReviewRequest) -> SkillResponse:
    """Reject the whole invalid batch before producing any statistics."""
    try:
        records = [ExecutionRecord.model_validate(record) for record in request.records]
        if len({record.record_id for record in records}) != len(records):
            raise ValueError("Duplicate record identifiers.")
    except (ValueError, ValidationError):
        return _empty(SkillStatus.REJECTED, "记录含未允许字段、无效元数据或重复编号；整批拒绝，未保留原始输入。")
    if not records:
        return _empty(SkillStatus.NEEDS_INPUT, "没有执行记录，无法形成观察。")
    try:
        resource = _Rules.model_validate(load_json_resource("review_rules.json"))
    except (OSError, ValueError, ValidationError):
        return _empty(SkillStatus.DEGRADED, "复盘规则不可用，本次未生成统计，请恢复资源后重试。")

    status_counts = Counter(record.status.value for record in records)
    rule_counts = Counter(ref for record in records for ref in set(record.rule_refs))
    observations = []
    candidates = []
    for status, action in resource.status_actions.items():
        matching = [record for record in records if record.status.value == status]
        if not matching:
            continue
        observations.append({
            "kind": status, "count": len(matching), "recommendation": action,
            "record_ids": [record.record_id for record in matching],
        })
        for ref in sorted({ref for record in matching for ref in record.rule_refs}):
            candidates.append({
                "rule_ref": ref, "trigger_status": status,
                "record_ids": [record.record_id for record in matching if ref in record.rule_refs],
                "recommendation": "人工检查规则与这些结果的适配性；命中不代表规则错误，不自动修改。",
            })

    return SkillResponse.create(
        skill="operations-review", status=SkillStatus.OK,
        data={
            "total_calls": len(records), "sample_size": len(records),
            "status_counts": dict(status_counts),
            "skill_counts": dict(Counter(record.skill for record in records)),
            "degraded_count": status_counts["degraded"],
            "rule_hit_counts": dict(sorted(rule_counts.items())),
            "event_counts": dict(Counter(record.incident_category for record in records if record.incident_category is not None)),
            "observations": observations, "rule_update_candidates": candidates,
            "record_ids": [record.record_id for record in records],
            "causal_claims": False, "rule_version": resource.version,
        },
        source_refs=resource.source_refs, rule_refs=[resource.rule_id],
        warnings=["演示复盘仅报告输入记录中的描述性观察，不证明处理成效、因果或真实通知。"],
        next_actions=[item["recommendation"] for item in observations], demo_data=True,
    )


def _empty(status: SkillStatus, warning: str) -> SkillResponse:
    return SkillResponse.create(
        skill="operations-review", status=status,
        data={"total_calls": 0, "sample_size": 0, "observations": [], "rule_update_candidates": [], "causal_claims": False},
        warnings=[warning], next_actions=["提供符合元数据白名单的脱敏执行记录并重试。"], demo_data=True,
    )
