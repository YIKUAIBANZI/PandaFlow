"""Safe loading for versioned, local PandaFlow resource files."""

import json
from pathlib import Path
from typing import Any


RESOURCE_DIRECTORY = Path(__file__).resolve().parents[3] / "resources"


def load_json_resource(filename: str) -> dict[str, Any]:
    """Load a named JSON resource without allowing callers to traverse paths."""

    path = (RESOURCE_DIRECTORY / filename).resolve()
    if path.parent != RESOURCE_DIRECTORY.resolve() or path.suffix != ".json":
        raise ValueError("Only direct JSON resource files may be loaded.")

    with path.open(encoding="utf-8") as resource_file:
        content = json.load(resource_file)

    if not isinstance(content, dict):
        raise ValueError(f"Resource {filename} must contain a JSON object.")
    return content
