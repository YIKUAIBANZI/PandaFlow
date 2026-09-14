"""Build the deterministic, public allowlisted PandaFlow source archive."""

import argparse
import os
import stat
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MANIFEST_NAME = "release-manifest.txt"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class PublicFile:
    """An immutable public-file snapshot ready for ZIP serialization."""

    relative: str
    data: bytes


def _project_version(project_root: Path) -> str:
    project_data = _read_public_bytes(project_root, project_root / "pyproject.toml")
    return tomllib.loads(project_data.decode("utf-8"))["project"]["version"]


def _validated_public_path(project_root: Path, path: Path) -> Path:
    """Reject symlinked or external paths before reading public release data."""

    if project_root.is_symlink():
        raise ValueError(
            f"Public release path must not be a symbolic link: {project_root}"
        )
    resolved_root = project_root.resolve(strict=True)
    try:
        relative = path.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"Public release path is outside the project: {path}") from exc

    current = project_root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(
                f"Public release path must not be a symbolic link: {current}"
            )

    resolved_path = path.resolve(strict=True)
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError(f"Public release path is outside the project: {path}")
    return path


def _read_public_bytes(project_root: Path, path: Path) -> bytes:
    """Read a regular file and reject link/path replacement around the open."""

    path = _validated_public_path(project_root, path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        current = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_ISLNK(current.st_mode)
            or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise ValueError(f"Public release path changed during read: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as public_file:
            data = public_file.read()
        _validated_public_path(project_root, path)
        current = path.stat(follow_symlinks=False)
        if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError(f"Public release path changed during read: {path}")
        return data
    finally:
        os.close(descriptor)


def _public_files(project_root: Path) -> list[PublicFile]:
    manifest_path = project_root / MANIFEST_NAME
    manifest_data = _read_public_bytes(project_root, manifest_path)
    entries = manifest_data.decode("utf-8").splitlines()
    if not entries or len(entries) != len(set(entries)):
        raise ValueError("Release manifest must contain unique public file paths.")

    public_files: list[PublicFile] = []
    for entry in entries:
        relative = PurePosixPath(entry)
        if (
            not entry
            or "\\" in entry
            or relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != entry
        ):
            raise ValueError(f"Release manifest path is invalid: {entry!r}")
        path = project_root.joinpath(*relative.parts)
        data = (
            manifest_data
            if entry == MANIFEST_NAME
            else _read_public_bytes(project_root, path)
        )
        public_files.append(PublicFile(relative=entry, data=data))
    return public_files


def build_archive(project_root: Path, output: Path) -> Path:
    """Write a byte-reproducible ZIP containing only public release files."""

    public_files = _public_files(project_root)
    project_data = next(
        public_file.data
        for public_file in public_files
        if public_file.relative == "pyproject.toml"
    )
    version = tomllib.loads(project_data.decode("utf-8"))["project"]["version"]
    archive_root = f"pandaflow-{version}"
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for public_file in public_files:
                info = zipfile.ZipInfo(
                    f"{archive_root}/{public_file.relative}", ZIP_TIMESTAMP
                )
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, public_file.data)
        os.chmod(temporary, 0o644)
        os.replace(temporary, output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    version = _project_version(project_root)
    output = (
        arguments.output or project_root / "dist" / f"pandaflow-{version}-source.zip"
    )
    print(build_archive(project_root, output))


if __name__ == "__main__":
    main()
