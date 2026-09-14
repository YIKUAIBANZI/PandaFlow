import pytest

from pandaflow.shared.rules import load_json_resource
from pandaflow.shared.contracts import SkillStatus
from pandaflow.skills.panda_knowledge_guard.schemas import KnowledgeRequest
from pandaflow.skills.panda_knowledge_guard.service import answer_question


def test_registered_fact_returns_a_source_bound_answer():
    result = answer_question(KnowledgeRequest(question="大熊猫主要吃什么？", language="zh"))

    assert result.status is SkillStatus.OK
    assert "竹" in result.data["answer"]
    assert result.source_refs == ["source_panda_base_diet"]


def test_registered_diet_topic_is_retrievable_in_english():
    result = answer_question(
        KnowledgeRequest(question="What do giant pandas eat?", language="en")
    )

    assert result.status is SkillStatus.OK
    assert "bamboo" in result.data["answer"].lower()
    assert result.source_refs == ["source_panda_base_diet"]


def test_unsupported_rumour_returns_no_evidence_instead_of_inventing_an_answer():
    result = answer_question(KnowledgeRequest(question="今天哪只熊猫在户外？", language="zh"))

    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data["answer"] is None


def test_current_location_question_is_refused_before_broad_topic_matching():
    result = answer_question(
        KnowledgeRequest(question="今天竹林里是哪只熊猫？", language="zh")
    )

    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data["answer"] is None
    assert result.source_refs == []


def test_english_current_location_question_is_not_answered_as_diet():
    result = answer_question(
        KnowledgeRequest(
            question="Which giant panda is eating bamboo in the grove today?",
            language="en",
        )
    )

    assert result.status is SkillStatus.NEEDS_INPUT
    assert result.data["answer"] is None


def test_medical_question_is_rejected_without_diagnosis():
    result = answer_question(KnowledgeRequest(question="这只熊猫是不是生病了？", language="zh"))

    assert result.status is SkillStatus.REJECTED
    assert result.data["answer"] is None


@pytest.mark.parametrize("question, language, expected", [
    ("大熊猫为什么有伪拇指？", "zh", "握竹"),
    ("How do giant pandas grip bamboo?", "en", "pseudo-thumb"),
    ("大熊猫为什么花那么长时间进食？", "zh", "消化"),
    ("Why do pandas spend so much time eating?", "en", "digest"),
])
def test_additional_registered_topics_return_their_verified_source(question, language, expected):
    result = answer_question(KnowledgeRequest(question=question, language=language))
    assert result.status is SkillStatus.OK
    assert expected in result.data["answer"]
    assert result.source_refs == ["source_panda_base_diet"]
    assert result.demo_data is False


@pytest.mark.parametrize("question, language, status", [
    ("今天哪只熊猫在用伪拇指握竹？", "zh", SkillStatus.NEEDS_INPUT),
    ("How do giant pandas grip bamboo right now?", "en", SkillStatus.NEEDS_INPUT),
    ("伪拇指生病怎么治疗？", "zh", SkillStatus.REJECTED),
    ("Does grip bamboo difficulty require treatment?", "en", SkillStatus.REJECTED),
])
def test_new_topics_do_not_override_live_or_medical_refusal(question, language, status):
    result = answer_question(KnowledgeRequest(question=question, language=language))
    assert result.status is status
    assert result.data["answer"] is None
    assert result.source_refs == []


def test_every_knowledge_card_is_retrievable_in_both_languages_and_source_registered():
    cards = load_json_resource("knowledge_cards.json")["cards"]
    sources = {s["source_id"]: s for s in load_json_resource("source_registry.json")["sources"]}
    for card in cards:
        source = sources[card["source_ref"]]
        assert source["classification"] == "public"
        assert source["url"].startswith("https://www.panda.org.cn/")
        for language in ("zh", "en"):
            for question in card[f"question_patterns_{language}"]:
                result = answer_question(KnowledgeRequest(question=question, language=language))
                assert result.status is SkillStatus.OK
                assert result.data["answer"] == card[f"answer_{language}"]
                assert result.source_refs == [card["source_ref"]]
