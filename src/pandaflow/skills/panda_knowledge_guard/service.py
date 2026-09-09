"""Deterministic retrieval that refuses unsupported or medical claims."""

from pandaflow.shared.contracts import SkillResponse, SkillStatus
from pandaflow.shared.rules import load_json_resource
from pandaflow.skills.panda_knowledge_guard.schemas import KnowledgeRequest


MEDICAL_TERMS = ("生病", "诊断", "治疗", "disease", "diagnose", "treatment")


def answer_question(request: KnowledgeRequest) -> SkillResponse:
    cards = load_json_resource("knowledge_cards.json")
    question = request.question.lower()
    if any(term in question for term in MEDICAL_TERMS):
        return _response(
            cards, SkillStatus.REJECTED, None, [],
            "Medical or animal-health questions require qualified human staff.",
        )
    for card in cards["cards"]:
        if any(keyword.lower() in question for keyword in card["keywords"]):
            answer = card["answer_zh"] if request.language == "zh" else card["answer_en"]
            return _response(cards, SkillStatus.OK, answer, [card["source_ref"]], None)
    return _response(
        cards, SkillStatus.NEEDS_INPUT, None, [],
        "No registered evidence supports this question; ask staff or provide a supported topic.",
    )


def _response(cards, status, answer, source_refs, warning):
    return SkillResponse.create(
        skill="panda-knowledge-guard",
        status=status,
        data={"answer": answer},
        source_refs=source_refs,
        rule_refs=["rule_registered_knowledge_only"],
        warnings=[warning] if warning else [],
        next_actions=[],
        demo_data=cards["classification"] == "demo",
    )
