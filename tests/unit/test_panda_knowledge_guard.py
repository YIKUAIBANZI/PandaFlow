from pandaflow.shared.contracts import SkillStatus
from pandaflow.skills.panda_knowledge_guard.schemas import KnowledgeRequest
from pandaflow.skills.panda_knowledge_guard.service import answer_question


def test_registered_fact_returns_a_source_bound_answer():
    result = answer_question(KnowledgeRequest(question="大熊猫主要吃什么？", language="zh"))

    assert result.status is SkillStatus.OK
    assert "竹" in result.data["answer"]
    assert result.source_refs == ["source_demo_knowledge_card"]


def test_unsupported_rumour_returns_no_evidence_instead_of_inventing_an_answer():
    result = answer_question(KnowledgeRequest(question="今天哪只熊猫在户外？", language="zh"))

    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data["answer"] is None


def test_medical_question_is_rejected_without_diagnosis():
    result = answer_question(KnowledgeRequest(question="这只熊猫是不是生病了？", language="zh"))

    assert result.status is SkillStatus.REJECTED
    assert result.data["answer"] is None
