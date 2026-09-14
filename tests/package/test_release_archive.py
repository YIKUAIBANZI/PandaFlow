"""Black-box checks for the public source ZIP."""

import importlib.util
import re
import stat
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path
from urllib.parse import unquote

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
ARCHIVE_ROOT = f"pandaflow-{PROJECT['project']['version']}"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "build_release_archive.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "build_release_archive", SCRIPT_PATH
)
assert SCRIPT_SPEC is not None and SCRIPT_SPEC.loader is not None
SCRIPT_MODULE = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(SCRIPT_MODULE)
build_archive = SCRIPT_MODULE.build_archive


def _minimal_project(project_root: Path) -> None:
    (project_root / "LICENSE").write_text("MIT", encoding="utf-8")
    (project_root / "README.md").write_text("public", encoding="utf-8")
    (project_root / "pyproject.toml").write_text(
        '[project]\nname = "pandaflow"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (project_root / "uv.lock").write_text("version = 1", encoding="utf-8")
    for directory in ("resources", "scripts", "skills", "src/pandaflow", "tests"):
        (project_root / directory).mkdir(parents=True, exist_ok=True)
    (project_root / "resources" / "public.txt").write_text("public", encoding="utf-8")
    (project_root / "release-manifest.txt").write_text(
        "LICENSE\n"
        "README.md\n"
        "pyproject.toml\n"
        "release-manifest.txt\n"
        "resources/public.txt\n"
        "uv.lock",
        encoding="utf-8",
    )


def test_source_zip_is_reproducible_and_uses_a_public_allowlist(tmp_path: Path) -> None:
    """Catch missing runtime assets, internal files, and unstable archive metadata."""

    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    for output in (first, second):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--output", str(output)],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    assert first.read_bytes() == second.read_bytes()
    assert stat.S_IMODE(first.stat().st_mode) == 0o644
    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())

    assert {
        f"{ARCHIVE_ROOT}/LICENSE",
        f"{ARCHIVE_ROOT}/README.md",
        f"{ARCHIVE_ROOT}/docs/PandaFlow-API接口文档.md",
        f"{ARCHIVE_ROOT}/docs/competition-presentation-kit.md",
        f"{ARCHIVE_ROOT}/docs/workhub-integration-runbook.md",
        f"{ARCHIVE_ROOT}/evidence/api-documentation-test-report.md",
        f"{ARCHIVE_ROOT}/evidence/competition-presentation-kit-test-report.md",
        f"{ARCHIVE_ROOT}/evidence/workhub-research-2026-09-12.md",
        f"{ARCHIVE_ROOT}/output/pdf/PandaFlow-API接口文档.pdf",
        f"{ARCHIVE_ROOT}/pyproject.toml",
        f"{ARCHIVE_ROOT}/release-manifest.txt",
        f"{ARCHIVE_ROOT}/uv.lock",
        f"{ARCHIVE_ROOT}/resources/demo_scenarios.json",
        f"{ARCHIVE_ROOT}/resources/visitor_rules.json",
        f"{ARCHIVE_ROOT}/scripts/build_release_archive.py",
        f"{ARCHIVE_ROOT}/scripts/build_api_pdf.py",
        f"{ARCHIVE_ROOT}/skills/visitor-policy-check/SKILL.md",
        f"{ARCHIVE_ROOT}/src/pandaflow/api/response_models.py",
        f"{ARCHIVE_ROOT}/src/pandaflow/web/index.html",
        f"{ARCHIVE_ROOT}/src/pandaflow/web/styles.css",
        f"{ARCHIVE_ROOT}/src/pandaflow/web/app.js",
        f"{ARCHIVE_ROOT}/src/pandaflow/web/view-model.js",
        f"{ARCHIVE_ROOT}/tests/api/test_openapi_response_models.py",
    } <= names
    assert not any(
        name.endswith(("AGENTS.md", "mmr.md", ".env", ".pyc"))
        or "/__pycache__/" in name
        for name in names
    )


def test_source_zip_preserves_readme_local_links(tmp_path: Path) -> None:
    """Catch a source archive whose README points to files left out of the ZIP."""

    output = build_archive(PROJECT_ROOT, tmp_path / "release.zip")
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        readme = archive.read(f"{ARCHIVE_ROOT}/README.md").decode("utf-8")

    local_links = re.findall(r"\]\((?!https?://)([^)#]+)", readme)
    missing = [
        link for link in local_links if f"{ARCHIVE_ROOT}/{unquote(link)}" not in names
    ]
    assert missing == []


def test_source_zip_rejects_allowlisted_file_symlink_to_outside(
    tmp_path: Path,
) -> None:
    """Catch a top-level public file that would leak content outside the checkout."""

    project_root = tmp_path / "project"
    project_root.mkdir()
    _minimal_project(project_root)
    outside = tmp_path / "private.md"
    outside.write_text("private", encoding="utf-8")
    (project_root / "README.md").unlink()
    try:
        (project_root / "README.md").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    output = tmp_path / "release.zip"
    with pytest.raises(ValueError, match="symbolic link"):
        build_archive(project_root, output)
    assert not output.exists()


def test_source_zip_rejects_allowlisted_directory_symlink_to_outside(
    tmp_path: Path,
) -> None:
    """Catch an allowlisted directory that would expose an external tree."""

    project_root = tmp_path / "project"
    project_root.mkdir()
    _minimal_project(project_root)
    (project_root / "resources" / "public.txt").unlink()
    (project_root / "resources").rmdir()
    outside = tmp_path / "private-resources"
    outside.mkdir()
    (outside / "public.txt").write_text("private", encoding="utf-8")
    try:
        (project_root / "resources").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    output = tmp_path / "release.zip"
    with pytest.raises(ValueError, match="symbolic link"):
        build_archive(project_root, output)
    assert not output.exists()


def test_source_zip_cannot_leak_file_swapped_after_public_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch a validated public file being replaced before ZIP serialization."""

    project_root = tmp_path / "project"
    project_root.mkdir()
    _minimal_project(project_root)
    outside = tmp_path / "private.md"
    outside.write_text("TOP-SECRET-OUTSIDE-WHITELIST", encoding="utf-8")
    original_public_files = SCRIPT_MODULE._public_files

    def swap_after_snapshot(root: Path):
        public_files = original_public_files(root)
        (root / "README.md").unlink()
        try:
            (root / "README.md").symlink_to(outside)
        except OSError as exc:
            pytest.skip(f"symlinks are unavailable: {exc}")
        return public_files

    monkeypatch.setattr(SCRIPT_MODULE, "_public_files", swap_after_snapshot)
    output = build_archive(project_root, tmp_path / "release.zip")

    with zipfile.ZipFile(output) as archive:
        archived_readme = archive.read("pandaflow-0.1.0/README.md")
    assert archived_readme == b"public"
    assert b"TOP-SECRET-OUTSIDE-WHITELIST" not in output.read_bytes()


def test_source_zip_failure_does_not_leave_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch a failed build leaving a valid-looking but incomplete final ZIP."""

    project_root = tmp_path / "project"
    project_root.mkdir()
    _minimal_project(project_root)
    output = tmp_path / "release.zip"
    original_writestr = zipfile.ZipFile.writestr
    calls = 0

    def fail_during_write(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated archive write failure")
        return original_writestr(self, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "writestr", fail_during_write)
    with pytest.raises(OSError, match="simulated archive write failure"):
        build_archive(project_root, output)
    assert not output.exists()


def test_source_zip_fixes_unix_metadata_on_a_windows_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch host defaults changing otherwise identical ZIP bytes on Windows."""

    project_root = tmp_path / "project"
    project_root.mkdir()
    _minimal_project(project_root)
    original_zip_info = zipfile.ZipInfo

    class WindowsDefaultZipInfo(original_zip_info):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.create_system = 0

    monkeypatch.setattr(zipfile, "ZipInfo", WindowsDefaultZipInfo)
    output = build_archive(project_root, tmp_path / "release.zip")

    with zipfile.ZipFile(output) as archive:
        assert {info.create_system for info in archive.infolist()} == {3}


def test_source_zip_ignores_files_not_listed_in_release_manifest(
    tmp_path: Path,
) -> None:
    """Catch a new debug or secret file being swept into a public directory."""

    project_root = tmp_path / "project"
    project_root.mkdir()
    _minimal_project(project_root)
    private_file = project_root / "src" / "pandaflow" / "private.txt"
    private_file.write_text("private", encoding="utf-8")

    output = build_archive(project_root, tmp_path / "release.zip")
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())

    assert "pandaflow-0.1.0/src/pandaflow/private.txt" not in names
