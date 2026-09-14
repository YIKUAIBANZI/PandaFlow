"""Black-box checks for the installable PandaFlow wheel."""

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_WHEEL_FILES = {
    "pandaflow/resources/demo_scenarios.json",
    "pandaflow/resources/incident_rules.json",
    "pandaflow/resources/knowledge_cards.json",
    "pandaflow/resources/park_graph.json",
    "pandaflow/resources/review_rules.json",
    "pandaflow/resources/source_registry.json",
    "pandaflow/resources/visitor_rules.json",
    "pandaflow/resources/weather_config.json",
    "pandaflow/resources/welfare_rules.json",
    "pandaflow/skill_docs/accessible-itinerary-planner/SKILL.md",
    "pandaflow/skill_docs/incident-triage-dispatch/SKILL.md",
    "pandaflow/skill_docs/operations-review/SKILL.md",
    "pandaflow/skill_docs/panda-knowledge-guard/SKILL.md",
    "pandaflow/skill_docs/visitor-policy-check/SKILL.md",
    "pandaflow/skill_docs/welfare-risk-dispatcher/SKILL.md",
    "pandaflow/web/app.js",
    "pandaflow/web/index.html",
    "pandaflow/web/styles.css",
    "pandaflow/web/view-model.js",
}


def _environment_python(environment_directory: Path) -> Path:
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    return environment_directory / relative


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_directory = tmp_path_factory.mktemp("wheel")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(output_directory)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(output_directory.glob("pandaflow-*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def test_wheel_contains_runtime_and_skill_assets(built_wheel: Path) -> None:
    """Catch a wheel that drops rules, scenario data, Skill docs, or Web assets."""

    with zipfile.ZipFile(built_wheel) as archive:
        wheel_files = set(archive.namelist())

    assert EXPECTED_WHEEL_FILES <= wheel_files


def test_installed_wheel_loads_rules_without_checkout(
    built_wheel: Path,
    tmp_path: Path,
) -> None:
    """Catch resource loading that accidentally depends on the repository layout."""

    environment_directory = tmp_path / "installed"
    subprocess.run(
        ["uv", "venv", str(environment_directory)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(_environment_python(environment_directory)),
            "--no-deps",
            str(built_wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    clean_environment = os.environ.copy()
    clean_environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            str(_environment_python(environment_directory)),
            "-I",
            "-c",
            (
                "from pandaflow.shared.rules import load_json_resource; "
                "print(load_json_resource('demo_scenarios.json')['classification'])"
            ),
        ],
        cwd=tmp_path,
        env=clean_environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "demo"


def test_installed_wheel_serves_demo_api_without_checkout(
    built_wheel: Path,
    tmp_path: Path,
) -> None:
    """Catch an installed API or Web mount that still relies on checkout files."""

    target = tmp_path / "site-packages"
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--target",
            str(target),
            "--no-deps",
            str(built_wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    script = f"""
import asyncio
import sys

sys.path.insert(0, {str(target)!r})

import httpx
from pandaflow.api.app import app

async def main():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        health = await client.get("/health")
        demo = await client.get("/demo")
        catalog = await client.get("/api/v1/demo/scenarios")
    assert health.json() == {{"status": "ok"}}
    assert demo.status_code == 200
    assert catalog.status_code == 200
    assert len(catalog.json()["scenarios"]) == 4

asyncio.run(main())
"""
    clean_environment = os.environ.copy()
    clean_environment.pop("PYTHONPATH", None)
    subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        env=clean_environment,
        check=True,
        capture_output=True,
        text=True,
    )
