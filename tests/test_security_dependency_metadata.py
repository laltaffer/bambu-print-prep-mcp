"""Security floors must survive plain and wheel installs, without pip's -c option."""
from importlib.metadata import requires
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

CONSTRAINTS = [
    Requirement(line)
    for line in (Path(__file__).parents[1] / "security-constraints.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
]
DEV_ONLY = {"urllib3"}


@pytest.mark.parametrize("constraint", CONSTRAINTS, ids=lambda item: item.name)
def test_installed_metadata_enforces_security_floor(constraint: Requirement) -> None:
    name = canonicalize_name(constraint.name)
    metadata = [
        Requirement(item)
        for item in requires("bambu-print-prep-mcp") or []
        if canonicalize_name(Requirement(item).name) == name
    ]
    assert metadata, f"Missing {name} security floor in installed package metadata"
    floor = max(Version(item.version) for item in constraint.specifier if item.operator == ">=")
    candidates = [
        item
        for item in metadata
        if any(
            spec.operator in {">=", "=="} and Version(spec.version) >= floor
            for spec in item.specifier
        )
    ]
    assert candidates, f"Installed metadata permits {name} below {floor}"
    if name in DEV_ONLY:
        assert any(
            item.marker is not None
            and item.marker.evaluate({"extra": "dev"})
            and not item.marker.evaluate({"extra": ""})
            for item in candidates
        ), f"{name} belongs in the dev extra"
    else:
        assert any(item.marker is None for item in candidates), f"{name} is a runtime requirement"
