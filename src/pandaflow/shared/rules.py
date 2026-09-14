"""Safe loading for versioned, local PandaFlow resource files."""

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

SOURCE_RESOURCE_DIRECTORY = Path(__file__).resolve().parents[3] / "resources"


class ResourceLoadError(OSError):
    """A packaged rule or data resource could not be loaded safely."""


def load_json_resource(filename: str) -> dict[str, Any]:
    """Load a named JSON resource without allowing callers to traverse paths."""

    if "/" in filename or "\\" in filename or Path(filename).suffix != ".json":
        raise ValueError("Only direct JSON resource files may be loaded.")

    packaged_resource = files("pandaflow").joinpath("resources", filename)
    resource = (
        packaged_resource
        if packaged_resource.is_file()
        else SOURCE_RESOURCE_DIRECTORY / filename
    )
    try:
        with resource.open(encoding="utf-8") as resource_file:
            content = json.load(resource_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ResourceLoadError("JSON resource is unavailable or invalid.") from exc

    if not isinstance(content, dict):
        raise ResourceLoadError("JSON resource must contain an object.")
    return content
