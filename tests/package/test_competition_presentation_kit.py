import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "docs" / "competition-presentation-kit.md"


def _content() -> str:
    return KIT.read_text(encoding="utf-8")


def _seconds(value: str) -> int:
    minutes, seconds = value.split(":")
    return int(minutes) * 60 + int(seconds)


def test_submission_intro_is_bounded_and_truthful():
    content = _content()
    match = re.search(
        r"<!-- INTRO_START -->\s*>\s*(.+?)\s*<!-- INTRO_END -->",
        content,
        re.DOTALL,
    )
    assert match is not None
    intro = re.sub(r"\s+", "", match.group(1))

    assert 120 <= len(intro) <= 200
    assert "六个" in intro
    assert "安全" in intro
    assert "动物福利" in intro
    assert "演示" in intro or "原型" in intro
    assert all(claim not in intro for claim in ("官方合作", "已落地", "已上架", "已接入WorkHub"))


def test_demo_timeline_is_contiguous_and_under_five_minutes():
    content = _content()
    ranges = re.findall(r"^###\s+(\d{2}:\d{2})[–-](\d{2}:\d{2})", content, re.MULTILINE)
    assert ranges

    seconds = [(_seconds(start), _seconds(end)) for start, end in ranges]
    assert seconds[0][0] == 0
    assert all(start < end for start, end in seconds)
    assert all(left[1] == right[0] for left, right in zip(seconds, seconds[1:]))
    assert seconds[-1][1] <= 300


def test_script_covers_six_skills_four_scenarios_and_evidence_boundaries():
    content = _content()

    for skill in (
        "visitor-policy-check",
        "accessible-itinerary-planner",
        "panda-knowledge-guard",
        "welfare-risk-dispatcher",
        "incident-triage-dispatch",
        "operations-review",
    ):
        assert f"`{skill}`" in content

    for scenario in (
        "normal_all_skills",
        "heat_replan",
        "human_escalation",
        "live_current_weather",
    ):
        assert f"`{scenario}`" in content

    for evidence in (
        "Prototype",
        "Demo Data",
        "No Real Dispatch",
        "source_refs",
        "rule_refs",
        "sent=false",
        "WorkHub 尚未完成真实联调",
    ):
        assert evidence in content

    for false_claim in ("已接入 WorkHub", "已上架能力超市", "平台验收通过"):
        assert false_claim not in content
