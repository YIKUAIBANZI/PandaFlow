"""Security checks for local PandaFlow resource loading."""

import pytest

from pandaflow.shared.rules import load_json_resource


@pytest.mark.parametrize(
    "filename",
    ["../visitor_rules.json", "..\\visitor_rules.json"],
)
def test_resource_loader_rejects_cross_platform_path_traversal(filename: str) -> None:
    """Catch traversal that uses either POSIX or Windows separators."""

    with pytest.raises(ValueError, match="Only direct JSON"):
        load_json_resource(filename)
