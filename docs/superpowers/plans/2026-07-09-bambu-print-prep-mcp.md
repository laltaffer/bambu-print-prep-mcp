# Bambu Print Prep MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public-safe, local-first MCP server that inspects, repairs, scales, and recommends Bambu Studio print settings for STL files without printer credentials or network-dependent model handling.

**Architecture:** Create a small Python package with a thin MCP transport layer over testable core services. Keep mesh I/O, analysis, repair, scaling, recommendations, reporting, and security checks in separate modules so each can be tested without a live MCP client.

**Tech Stack:** Python 3.11+, `mcp>=1.27,<2` stable SDK, `trimesh`, `numpy`, `pydantic`, `pytest`, `ruff`, `detect-secrets`, GitHub Actions.

---

## References

- Design spec: `docs/superpowers/specs/2026-07-09-bambu-print-prep-mcp-design.md`
- MCP Python SDK v1 is the stable production line; v2 is pre-release as of 2026-07-09. Use `mcp>=1.27,<2`.
- MCP v1 FastMCP import path: `from mcp.server.fastmcp import FastMCP`

## Target File Structure

- `pyproject.toml`: package metadata, dependencies, console scripts, test/ruff config.
- `.gitignore`: public-safe ignore rules for model files, outputs, env files, caches, and local metadata.
- `.secrets.baseline`: detect-secrets baseline generated after source files exist.
- `README.md`: public usage guide with no personal paths or printer credentials.
- `SECURITY.md`: disclosure and privacy policy for local-first operation.
- `AGENTS.md`: sanitized public contributor/agent instructions, replacing local session metadata.
- `.github/workflows/ci.yml`: lint, tests, and secret scan.
- `src/bambu_print_prep_mcp/__init__.py`: package version.
- `src/bambu_print_prep_mcp/server.py`: MCP tool registrations.
- `src/bambu_print_prep_mcp/cli.py`: local CLI for smoke testing without MCP.
- `src/bambu_print_prep_mcp/models.py`: Pydantic domain models.
- `src/bambu_print_prep_mcp/mesh_io.py`: STL load/write helpers.
- `src/bambu_print_prep_mcp/analysis.py`: dimensions, triangle count, build-volume fit, warnings.
- `src/bambu_print_prep_mcp/repair.py`: local mesh repair attempts.
- `src/bambu_print_prep_mcp/transform.py`: scale normalization.
- `src/bambu_print_prep_mcp/recommendations.py`: Bambu setting recommendations.
- `src/bambu_print_prep_mcp/reporting.py`: Markdown and JSON report writing.
- `src/bambu_print_prep_mcp/prepare.py`: orchestration for `prepare_model_for_bambu`.
- `src/bambu_print_prep_mcp/security.py`: path and output safety helpers.
- `src/bambu_print_prep_mcp/profiles/printers.json`: Bambu printer profiles.
- `tests/conftest.py`: synthetic mesh fixtures.
- `tests/test_security.py`: public-safety/path tests.
- `tests/test_analysis.py`: inspection tests.
- `tests/test_transform.py`: scale tests.
- `tests/test_recommendations.py`: recommendation tests.
- `tests/test_prepare.py`: end-to-end local prepare tests.
- `tests/test_server.py`: MCP tool registration/response shape tests.

---

### Task 1: Public-Safe Repository Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `SECURITY.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Replace `AGENTS.md` with sanitized public instructions**

Write this exact content to `AGENTS.md`:

```markdown
# Agent Instructions

This repository builds a local-first MCP server for preparing STL files for Bambu Studio.

## Privacy Rules

- Do not commit personal STL/3MF files, screenshots, generated reports, printer credentials, access codes, serial numbers, cloud tokens, or local machine paths.
- Keep examples synthetic and use sample paths such as `/path/to/model.stl`.
- The MVP must not upload models to network services.
- Any future printer-control feature must require explicit user confirmation before changing printer state.

## Development Rules

- Prefer small, testable modules under `src/bambu_print_prep_mcp`.
- Keep MCP tool wrappers thin; put business logic in core services.
- Run tests, linting, and secret scanning before publishing.
```

- [ ] **Step 2: Create `.gitignore`**

Write this exact content to `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
.venv/
venv/
dist/
build/
*.egg-info/

# Local configuration and secrets
.env
.env.*
!.env.example
*.pem
*.key
*.crt
*.p12
*.mobileconfig

# Generated model/output data
models/
outputs/
reports/
*.stl
*.3mf
*.gcode
*.step
*.stp
*.obj

# OS/editor noise
.DS_Store
.idea/
.vscode/

# Local agent/session metadata
CLAUDE.local.md
AGENTS.local.md
*.local.json
```

- [ ] **Step 3: Create `pyproject.toml`**

Write this exact content:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bambu-print-prep-mcp"
version = "0.1.0"
description = "Local-first MCP server for preparing STL files for Bambu Studio."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Bambu Print Prep MCP Contributors" }]
dependencies = [
  "mcp[cli]>=1.27,<2",
  "numpy>=1.26",
  "pydantic>=2.7",
  "trimesh>=4.4",
]

[project.optional-dependencies]
dev = [
  "detect-secrets>=1.5",
  "pytest>=8.2",
  "ruff>=0.5",
]

[project.scripts]
bambu-print-prep = "bambu_print_prep_mcp.cli:main"
bambu-print-prep-mcp = "bambu_print_prep_mcp.server:main"

[tool.hatch.build.targets.wheel]
packages = ["src/bambu_print_prep_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
```

- [ ] **Step 4: Create `README.md`**

Write this exact initial README:

```markdown
# Bambu Print Prep MCP

Local-first MCP server for preparing STL files for Bambu Studio.

The MVP inspects STL files, repairs simple mesh problems, normalizes scale, recommends Bambu Studio settings, and writes safe local reports. It does not connect to Bambu cloud, upload models, store printer credentials, or send print jobs.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## CLI Smoke Test

```bash
bambu-print-prep inspect /path/to/model.stl
bambu-print-prep prepare /path/to/model.stl --target-height-mm 130 --output-dir outputs
```

## MCP Server

```bash
bambu-print-prep-mcp
```

## Privacy

Do not commit personal STL files, screenshots, generated reports, printer serials, access codes, Bambu account data, or local absolute paths. Generated output belongs in `outputs/`, which is ignored by git.
```

- [ ] **Step 5: Create `SECURITY.md`**

Write this exact content:

```markdown
# Security Policy

## Supported Versions

This project is pre-1.0. Security fixes are applied to the main branch.

## Privacy Model

The MVP is local-first. It does not upload models, contact Bambu cloud, read printer credentials, or send printer commands.

## Sensitive Data

Never commit:

- Personal STL, 3MF, G-code, screenshots, or generated reports
- Printer serial numbers, LAN access codes, or Bambu account tokens
- Local absolute paths from a real machine
- `.env` files or private keys

## Reporting Issues

Open a GitHub issue for non-sensitive bugs. For sensitive reports, use GitHub private vulnerability reporting if enabled by the repository owner.
```

- [ ] **Step 6: Run scaffold checks**

Run:

```bash
git status --short
git grep -n -E "localhost|/Users|Desktop|TemporaryItems|access code|serial number" -- \
  ':!docs/superpowers/plans/**'
```

Expected:

```text
No private local paths or session URLs should appear in tracked files.
```

- [ ] **Step 7: Commit scaffold**

```bash
git add AGENTS.md .gitignore README.md SECURITY.md pyproject.toml
git commit -m "chore: scaffold public-safe python project"
```

---

### Task 2: Domain Models And Printer Profiles

**Files:**
- Create: `src/bambu_print_prep_mcp/__init__.py`
- Create: `src/bambu_print_prep_mcp/models.py`
- Create: `src/bambu_print_prep_mcp/profiles/printers.json`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write model tests**

Create `tests/test_models.py`:

```python
from bambu_print_prep_mcp.models import Dimensions, PrinterProfile


def test_dimensions_max_axis_and_as_tuple() -> None:
    dims = Dimensions(width_mm=70.0, depth_mm=50.0, height_mm=130.0)

    assert dims.as_tuple() == (70.0, 50.0, 130.0)
    assert dims.max_axis_mm == 130.0


def test_printer_profile_contains_build_volume() -> None:
    profile = PrinterProfile(
        id="bambu_lab_p2s",
        display_name="Bambu Lab P2S",
        build_volume=Dimensions(width_mm=256.0, depth_mm=256.0, height_mm=256.0),
        default_nozzle_mm=0.4,
    )

    assert profile.build_volume.height_mm == 256.0
    assert profile.default_nozzle_mm == 0.4
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_models.py -v
```

Expected: fail because `bambu_print_prep_mcp.models` does not exist.

- [ ] **Step 3: Create package version**

Create `src/bambu_print_prep_mcp/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

- [ ] **Step 4: Implement domain models**

Create `src/bambu_print_prep_mcp/models.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class Dimensions(BaseModel):
    width_mm: float = Field(ge=0)
    depth_mm: float = Field(ge=0)
    height_mm: float = Field(ge=0)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.width_mm, self.depth_mm, self.height_mm)

    @property
    def max_axis_mm(self) -> float:
        return max(self.width_mm, self.depth_mm, self.height_mm)


class PrinterProfile(BaseModel):
    id: str
    display_name: str
    build_volume: Dimensions
    default_nozzle_mm: float = Field(gt=0)


class MeshInspection(BaseModel):
    file_path: str
    dimensions: Dimensions
    triangle_count: int = Field(ge=0)
    volume_mm3: float | None = None
    is_watertight: bool
    euler_number: int | None = None
    fits_build_volume: bool
    warnings: list[str] = Field(default_factory=list)
    summary: str


class RepairResult(BaseModel):
    input_path: str
    output_path: str
    before: MeshInspection
    after: MeshInspection
    actions: list[str]
    warnings: list[str] = Field(default_factory=list)


class ScaleResult(BaseModel):
    input_path: str
    output_path: str
    original_dimensions: Dimensions
    new_dimensions: Dimensions
    scale_factor: float
    fits_build_volume: bool
    warnings: list[str] = Field(default_factory=list)


class PrintSettingsRecommendation(BaseModel):
    printer: str
    material: str
    intent: str
    layer_height_mm: float
    support_type: str
    support_style: str
    support_placement: str
    threshold_angle_degrees: int
    top_z_distance_mm: float
    top_interface_layers: int
    brim_enabled: bool
    brim_width_mm: float
    wall_loops: int
    infill_percent: int
    notes: list[str]
    bambu_studio_steps: list[str]


class PrepareResult(BaseModel):
    input_path: str
    final_model_path: str
    markdown_report_path: str
    json_report_path: str
    initial_inspection: MeshInspection
    final_inspection: MeshInspection
    recommendation: PrintSettingsRecommendation
    warnings: list[str] = Field(default_factory=list)


def path_to_public_string(path: Path) -> str:
    return str(path.expanduser().resolve())
```

- [ ] **Step 5: Add printer profile data**

Create `src/bambu_print_prep_mcp/profiles/printers.json`:

```json
{
  "bambu_lab_p2s": {
    "id": "bambu_lab_p2s",
    "display_name": "Bambu Lab P2S",
    "build_volume": {
      "width_mm": 256.0,
      "depth_mm": 256.0,
      "height_mm": 256.0
    },
    "default_nozzle_mm": 0.4
  }
}
```

- [ ] **Step 6: Verify models pass**

Run:

```bash
pytest tests/test_models.py -v
```

Expected: pass.

- [ ] **Step 7: Commit models**

```bash
git add src/bambu_print_prep_mcp tests/test_models.py
git commit -m "feat: add domain models and printer profile"
```

---

### Task 3: Security Utilities

**Files:**
- Create: `src/bambu_print_prep_mcp/security.py`
- Create: `tests/test_security.py`

- [ ] **Step 1: Write security tests**

Create `tests/test_security.py`:

```python
from pathlib import Path

import pytest

from bambu_print_prep_mcp.security import ensure_supported_input, safe_output_path


def test_ensure_supported_input_accepts_stl(tmp_path: Path) -> None:
    model = tmp_path / "part.stl"
    model.write_text("solid empty\nendsolid empty\n", encoding="utf-8")

    assert ensure_supported_input(model) == model.resolve()


def test_ensure_supported_input_rejects_non_stl(tmp_path: Path) -> None:
    model = tmp_path / "part.obj"
    model.write_text("not an stl", encoding="utf-8")

    with pytest.raises(ValueError, match="Only STL files"):
        ensure_supported_input(model)


def test_safe_output_path_defaults_to_output_dir(tmp_path: Path) -> None:
    input_file = tmp_path / "model.stl"
    input_file.write_text("solid empty\nendsolid empty\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    result = safe_output_path(input_file, output_dir, suffix="_fixed", extension=".stl")

    assert result == output_dir / "model_fixed.stl"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_security.py -v
```

Expected: fail because `security.py` does not exist.

- [ ] **Step 3: Implement security utilities**

Create `src/bambu_print_prep_mcp/security.py`:

```python
from __future__ import annotations

from pathlib import Path


def ensure_supported_input(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Model file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Model path is not a file: {path}")
    if path.suffix.lower() != ".stl":
        raise ValueError("Only STL files are supported in the MVP.")
    return path


def ensure_output_dir(output_dir: str | Path | None, input_path: Path) -> Path:
    if output_dir is None:
        directory = input_path.parent / "outputs"
    else:
        directory = Path(output_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory.resolve()


def safe_output_path(
    input_path: str | Path,
    output_dir: str | Path | None,
    suffix: str,
    extension: str,
) -> Path:
    input_resolved = Path(input_path).expanduser().resolve()
    directory = ensure_output_dir(output_dir, input_resolved)
    return directory / f"{input_resolved.stem}{suffix}{extension}"


def refuse_overwrite_input(input_path: Path, output_path: Path) -> None:
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Refusing to overwrite the original input model.")
```

- [ ] **Step 4: Verify security tests pass**

Run:

```bash
pytest tests/test_security.py -v
```

Expected: pass.

- [ ] **Step 5: Commit security utilities**

```bash
git add src/bambu_print_prep_mcp/security.py tests/test_security.py
git commit -m "feat: add local path safety utilities"
```

---

### Task 4: Mesh I/O And Analysis

**Files:**
- Create: `src/bambu_print_prep_mcp/mesh_io.py`
- Create: `src/bambu_print_prep_mcp/analysis.py`
- Create: `tests/conftest.py`
- Create: `tests/test_analysis.py`

- [ ] **Step 1: Write synthetic mesh fixtures**

Create `tests/conftest.py`:

```python
from pathlib import Path

import pytest
import trimesh


@pytest.fixture
def cube_stl(tmp_path: Path) -> Path:
    mesh = trimesh.creation.box(extents=(20.0, 30.0, 40.0))
    path = tmp_path / "cube.stl"
    mesh.export(path)
    return path


@pytest.fixture
def oversized_stl(tmp_path: Path) -> Path:
    mesh = trimesh.creation.box(extents=(7000.0, 9000.0, 17000.0))
    path = tmp_path / "oversized.stl"
    mesh.export(path)
    return path
```

- [ ] **Step 2: Write analysis tests**

Create `tests/test_analysis.py`:

```python
from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model, load_printer_profile


def test_inspect_model_reports_dimensions(cube_stl: Path) -> None:
    result = inspect_model(cube_stl)

    assert result.dimensions.width_mm == 20.0
    assert result.dimensions.depth_mm == 30.0
    assert result.dimensions.height_mm == 40.0
    assert result.triangle_count == 12
    assert result.is_watertight is True
    assert result.fits_build_volume is True


def test_inspect_model_warns_for_oversized_model(oversized_stl: Path) -> None:
    result = inspect_model(oversized_stl)

    assert result.fits_build_volume is False
    assert any("larger than the Bambu Lab P2S build volume" in warning for warning in result.warnings)
    assert any("wrong units" in warning for warning in result.warnings)


def test_load_printer_profile() -> None:
    profile = load_printer_profile("bambu_lab_p2s")

    assert profile.display_name == "Bambu Lab P2S"
    assert profile.build_volume.height_mm == 256.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
pytest tests/test_analysis.py -v
```

Expected: fail because `analysis.py` and `mesh_io.py` do not exist.

- [ ] **Step 4: Implement mesh I/O**

Create `src/bambu_print_prep_mcp/mesh_io.py`:

```python
from __future__ import annotations

from pathlib import Path

import trimesh


def load_mesh(file_path: str | Path) -> trimesh.Trimesh:
    loaded = trimesh.load_mesh(Path(file_path), force="mesh")
    if not isinstance(loaded, trimesh.Trimesh):
        raise ValueError("Unable to load STL as a single mesh.")
    if loaded.vertices.size == 0 or loaded.faces.size == 0:
        raise ValueError("Mesh has no vertices or faces.")
    return loaded


def write_mesh(mesh: trimesh.Trimesh, output_path: str | Path) -> Path:
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(path)
    return path
```

- [ ] **Step 5: Implement analysis service**

Create `src/bambu_print_prep_mcp/analysis.py`:

```python
from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from bambu_print_prep_mcp.mesh_io import load_mesh
from bambu_print_prep_mcp.models import Dimensions, MeshInspection, PrinterProfile
from bambu_print_prep_mcp.security import ensure_supported_input


def load_printer_profile(printer: str = "bambu_lab_p2s") -> PrinterProfile:
    profile_path = files("bambu_print_prep_mcp").joinpath("profiles/printers.json")
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    if printer not in data:
        raise ValueError(f"Unknown printer profile: {printer}")
    return PrinterProfile.model_validate(data[printer])


def dimensions_from_bounds(bounds: list[list[float]]) -> Dimensions:
    min_corner, max_corner = bounds
    return Dimensions(
        width_mm=round(float(max_corner[0] - min_corner[0]), 4),
        depth_mm=round(float(max_corner[1] - min_corner[1]), 4),
        height_mm=round(float(max_corner[2] - min_corner[2]), 4),
    )


def fits_build_volume(dimensions: Dimensions, profile: PrinterProfile) -> bool:
    return (
        dimensions.width_mm <= profile.build_volume.width_mm
        and dimensions.depth_mm <= profile.build_volume.depth_mm
        and dimensions.height_mm <= profile.build_volume.height_mm
    )


def scale_warnings(dimensions: Dimensions, profile: PrinterProfile) -> list[str]:
    warnings: list[str] = []
    if not fits_build_volume(dimensions, profile):
        warnings.append(
            f"Model is larger than the {profile.display_name} build volume "
            f"({profile.build_volume.width_mm:g} x {profile.build_volume.depth_mm:g} "
            f"x {profile.build_volume.height_mm:g} mm)."
        )
    if dimensions.max_axis_mm > profile.build_volume.max_axis_mm * 10:
        warnings.append(
            "Model is extremely large and may have wrong units, such as meters or inches "
            "being interpreted as millimeters."
        )
    return warnings


def inspect_model(file_path: str | Path, printer: str = "bambu_lab_p2s") -> MeshInspection:
    path = ensure_supported_input(file_path)
    profile = load_printer_profile(printer)
    mesh = load_mesh(path)
    dimensions = dimensions_from_bounds(mesh.bounds.tolist())
    fit = fits_build_volume(dimensions, profile)
    warnings = scale_warnings(dimensions, profile)
    if not mesh.is_watertight:
        warnings.append("Mesh is not watertight and may need repair before slicing.")
    summary = (
        f"{path.name}: {dimensions.width_mm:g} x {dimensions.depth_mm:g} x "
        f"{dimensions.height_mm:g} mm, {len(mesh.faces)} triangles."
    )
    return MeshInspection(
        file_path=str(path),
        dimensions=dimensions,
        triangle_count=len(mesh.faces),
        volume_mm3=round(float(mesh.volume), 4) if mesh.is_volume else None,
        is_watertight=bool(mesh.is_watertight),
        euler_number=int(mesh.euler_number) if mesh.euler_number is not None else None,
        fits_build_volume=fit,
        warnings=warnings,
        summary=summary,
    )
```

- [ ] **Step 6: Verify analysis tests pass**

Run:

```bash
pytest tests/test_analysis.py -v
```

Expected: pass.

- [ ] **Step 7: Commit analysis**

```bash
git add src/bambu_print_prep_mcp/mesh_io.py src/bambu_print_prep_mcp/analysis.py tests/conftest.py tests/test_analysis.py
git commit -m "feat: inspect STL geometry and printer fit"
```

---

### Task 5: Scale Normalization

**Files:**
- Create: `src/bambu_print_prep_mcp/transform.py`
- Create: `tests/test_transform.py`

- [ ] **Step 1: Write transform tests**

Create `tests/test_transform.py`:

```python
from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.transform import normalize_scale


def test_normalize_scale_to_target_height(cube_stl: Path, tmp_path: Path) -> None:
    result = normalize_scale(cube_stl, output_path=tmp_path / "scaled.stl", target_height_mm=100.0)

    assert result.scale_factor == 2.5
    assert result.new_dimensions.height_mm == 100.0
    assert Path(result.output_path).exists()

    inspection = inspect_model(result.output_path)
    assert inspection.dimensions.height_mm == 100.0


def test_normalize_scale_refuses_missing_target(cube_stl: Path, tmp_path: Path) -> None:
    try:
        normalize_scale(cube_stl, output_path=tmp_path / "scaled.stl")
    except ValueError as exc:
        assert "Provide exactly one" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_transform.py -v
```

Expected: fail because `transform.py` does not exist.

- [ ] **Step 3: Implement transform service**

Create `src/bambu_print_prep_mcp/transform.py`:

```python
from __future__ import annotations

from pathlib import Path

from bambu_print_prep_mcp.analysis import fits_build_volume, inspect_model, load_printer_profile
from bambu_print_prep_mcp.mesh_io import load_mesh, write_mesh
from bambu_print_prep_mcp.models import ScaleResult
from bambu_print_prep_mcp.security import refuse_overwrite_input, safe_output_path


def _chosen_scale_factor(
    current_width: float,
    current_depth: float,
    current_height: float,
    target_width_mm: float | None,
    target_depth_mm: float | None,
    target_height_mm: float | None,
    scale_factor: float | None,
) -> float:
    provided = [
        target_width_mm is not None,
        target_depth_mm is not None,
        target_height_mm is not None,
        scale_factor is not None,
    ]
    if sum(provided) != 1:
        raise ValueError(
            "Provide exactly one of target_width_mm, target_depth_mm, "
            "target_height_mm, or scale_factor."
        )
    if target_width_mm is not None:
        return target_width_mm / current_width
    if target_depth_mm is not None:
        return target_depth_mm / current_depth
    if target_height_mm is not None:
        return target_height_mm / current_height
    assert scale_factor is not None
    return scale_factor


def normalize_scale(
    file_path: str | Path,
    output_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    target_height_mm: float | None = None,
    target_width_mm: float | None = None,
    target_depth_mm: float | None = None,
    scale_factor: float | None = None,
    printer: str = "bambu_lab_p2s",
) -> ScaleResult:
    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    chosen_output = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else safe_output_path(input_path, output_dir, "_scaled", ".stl")
    )
    refuse_overwrite_input(input_path, chosen_output)
    factor = _chosen_scale_factor(
        before.dimensions.width_mm,
        before.dimensions.depth_mm,
        before.dimensions.height_mm,
        target_width_mm,
        target_depth_mm,
        target_height_mm,
        scale_factor,
    )
    if factor <= 0:
        raise ValueError("Scale factor must be greater than zero.")
    mesh = load_mesh(input_path)
    mesh.apply_scale(factor)
    write_mesh(mesh, chosen_output)
    after = inspect_model(chosen_output, printer=printer)
    profile = load_printer_profile(printer)
    warnings = after.warnings.copy()
    return ScaleResult(
        input_path=str(input_path),
        output_path=str(chosen_output),
        original_dimensions=before.dimensions,
        new_dimensions=after.dimensions,
        scale_factor=round(float(factor), 6),
        fits_build_volume=fits_build_volume(after.dimensions, profile),
        warnings=warnings,
    )
```

- [ ] **Step 4: Verify transform tests pass**

Run:

```bash
pytest tests/test_transform.py -v
```

Expected: pass.

- [ ] **Step 5: Commit transform service**

```bash
git add src/bambu_print_prep_mcp/transform.py tests/test_transform.py
git commit -m "feat: normalize STL scale"
```

---

### Task 6: Mesh Repair

**Files:**
- Create: `src/bambu_print_prep_mcp/repair.py`
- Create: `tests/test_repair.py`

- [ ] **Step 1: Write repair tests**

Create `tests/test_repair.py`:

```python
from pathlib import Path

from bambu_print_prep_mcp.repair import repair_model


def test_repair_model_writes_new_file(cube_stl: Path, tmp_path: Path) -> None:
    output = tmp_path / "cube_repaired.stl"

    result = repair_model(cube_stl, output_path=output)

    assert Path(result.output_path).exists()
    assert result.before.triangle_count == result.after.triangle_count
    assert "fix_normals" in result.actions


def test_repair_model_refuses_overwrite(cube_stl: Path) -> None:
    try:
        repair_model(cube_stl, output_path=cube_stl)
    except ValueError as exc:
        assert "Refusing to overwrite" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_repair.py -v
```

Expected: fail because `repair.py` does not exist.

- [ ] **Step 3: Implement repair service**

Create `src/bambu_print_prep_mcp/repair.py`:

```python
from __future__ import annotations

from pathlib import Path

import trimesh

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.mesh_io import load_mesh, write_mesh
from bambu_print_prep_mcp.models import RepairResult
from bambu_print_prep_mcp.security import refuse_overwrite_input, safe_output_path


def repair_model(
    file_path: str | Path,
    output_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    preserve_scale: bool = True,
    printer: str = "bambu_lab_p2s",
) -> RepairResult:
    before = inspect_model(file_path, printer=printer)
    input_path = Path(before.file_path)
    chosen_output = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else safe_output_path(input_path, output_dir, "_repaired", ".stl")
    )
    refuse_overwrite_input(input_path, chosen_output)

    mesh = load_mesh(input_path)
    original_bounds = mesh.bounds.copy()
    actions: list[str] = []

    trimesh.repair.fix_normals(mesh)
    actions.append("fix_normals")
    trimesh.repair.fix_winding(mesh)
    actions.append("fix_winding")
    trimesh.repair.fill_holes(mesh)
    actions.append("fill_holes")
    mesh.remove_duplicate_faces()
    actions.append("remove_duplicate_faces")
    mesh.remove_degenerate_faces()
    actions.append("remove_degenerate_faces")
    mesh.remove_unreferenced_vertices()
    actions.append("remove_unreferenced_vertices")

    if preserve_scale and mesh.bounds.shape == original_bounds.shape:
        # Trimesh repair operations above should not rescale; this guards future edits.
        repaired_size = mesh.bounds[1] - mesh.bounds[0]
        original_size = original_bounds[1] - original_bounds[0]
        if not (abs(repaired_size - original_size) < 0.001).all():
            raise ValueError("Repair changed model scale; refusing to write output.")

    write_mesh(mesh, chosen_output)
    after = inspect_model(chosen_output, printer=printer)
    warnings = after.warnings.copy()
    if not after.is_watertight:
        warnings.append("Repair completed, but the model is still not watertight.")
    return RepairResult(
        input_path=str(input_path),
        output_path=str(chosen_output),
        before=before,
        after=after,
        actions=actions,
        warnings=warnings,
    )
```

- [ ] **Step 4: Verify repair tests pass**

Run:

```bash
pytest tests/test_repair.py -v
```

Expected: pass.

- [ ] **Step 5: Commit repair service**

```bash
git add src/bambu_print_prep_mcp/repair.py tests/test_repair.py
git commit -m "feat: repair STL meshes locally"
```

---

### Task 7: Bambu Setting Recommendations

**Files:**
- Create: `src/bambu_print_prep_mcp/recommendations.py`
- Create: `tests/test_recommendations.py`

- [ ] **Step 1: Write recommendation tests**

Create `tests/test_recommendations.py`:

```python
from pathlib import Path

from bambu_print_prep_mcp.recommendations import recommend_print_settings


def test_recommend_statue_uses_tree_supports(cube_stl: Path) -> None:
    result = recommend_print_settings(cube_stl, intent="statue", material="PLA")

    assert result.layer_height_mm == 0.16
    assert result.support_type == "Tree"
    assert result.support_style == "Slim"
    assert result.brim_enabled is True
    assert any("Support tab" in step for step in result.bambu_studio_steps)


def test_recommend_functional_part_uses_more_walls(cube_stl: Path) -> None:
    result = recommend_print_settings(cube_stl, intent="functional", material="PLA")

    assert result.wall_loops == 4
    assert result.infill_percent == 25
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_recommendations.py -v
```

Expected: fail because `recommendations.py` does not exist.

- [ ] **Step 3: Implement recommendations**

Create `src/bambu_print_prep_mcp/recommendations.py`:

```python
from __future__ import annotations

from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.models import PrintSettingsRecommendation


def recommend_print_settings(
    file_path: str | Path,
    printer: str = "bambu_lab_p2s",
    material: str = "PLA",
    intent: str = "statue",
) -> PrintSettingsRecommendation:
    inspection = inspect_model(file_path, printer=printer)
    normalized_intent = intent.lower().strip()
    notes = inspection.warnings.copy()

    if normalized_intent in {"functional", "bracket", "mount"}:
        layer_height = 0.2
        support_style = "Default"
        wall_loops = 4
        infill = 25
        notes.append("Functional intent favors more walls and infill over fine surface detail.")
    else:
        layer_height = 0.16
        support_style = "Slim"
        wall_loops = 2
        infill = 12
        notes.append("Statue/miniature intent favors finer layers and easier support removal.")

    if inspection.dimensions.height_mm > 120:
        notes.append("Tall model: enable brim and verify bed contact in Preview before printing.")

    steps = [
        "Open the model in Bambu Studio.",
        "In the Quality tab, set layer height to "
        f"{layer_height:.2f} mm for this print intent.",
        "In the Support tab, enable support and choose Tree supports.",
        f"Set tree support style to {support_style}.",
        "Set support placement to Everywhere for detailed figures with arms, horns, or deep overhangs.",
        "Set threshold angle to 30 degrees.",
        "Set top Z distance to 0.20 mm and top interface layers to 2.",
        "Enable brim with 5-8 mm width, then slice and inspect Preview.",
    ]

    return PrintSettingsRecommendation(
        printer=printer,
        material=material,
        intent=normalized_intent,
        layer_height_mm=layer_height,
        support_type="Tree",
        support_style=support_style,
        support_placement="Everywhere",
        threshold_angle_degrees=30,
        top_z_distance_mm=0.2,
        top_interface_layers=2,
        brim_enabled=True,
        brim_width_mm=6.0,
        wall_loops=wall_loops,
        infill_percent=infill,
        notes=notes,
        bambu_studio_steps=steps,
    )
```

- [ ] **Step 4: Verify recommendation tests pass**

Run:

```bash
pytest tests/test_recommendations.py -v
```

Expected: pass.

- [ ] **Step 5: Commit recommendations**

```bash
git add src/bambu_print_prep_mcp/recommendations.py tests/test_recommendations.py
git commit -m "feat: recommend Bambu Studio print settings"
```

---

### Task 8: Reporting And Prepare Orchestration

**Files:**
- Create: `src/bambu_print_prep_mcp/reporting.py`
- Create: `src/bambu_print_prep_mcp/prepare.py`
- Create: `tests/test_prepare.py`

- [ ] **Step 1: Write prepare tests**

Create `tests/test_prepare.py`:

```python
from pathlib import Path

from bambu_print_prep_mcp.prepare import prepare_model_for_bambu


def test_prepare_model_for_bambu_writes_outputs(cube_stl: Path, tmp_path: Path) -> None:
    result = prepare_model_for_bambu(
        cube_stl,
        output_dir=tmp_path / "prepared",
        target_height_mm=80.0,
        intent="statue",
    )

    assert Path(result.final_model_path).exists()
    assert Path(result.markdown_report_path).exists()
    assert Path(result.json_report_path).exists()
    assert result.final_inspection.dimensions.height_mm == 80.0
    assert result.recommendation.support_type == "Tree"


def test_prepare_without_target_keeps_model_size(cube_stl: Path, tmp_path: Path) -> None:
    result = prepare_model_for_bambu(cube_stl, output_dir=tmp_path / "prepared")

    assert result.final_inspection.dimensions.height_mm == 40.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_prepare.py -v
```

Expected: fail because reporting and prepare modules do not exist.

- [ ] **Step 3: Implement reporting**

Create `src/bambu_print_prep_mcp/reporting.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from bambu_print_prep_mcp.models import PrepareResult


def write_json_report(result: BaseModel, output_path: str | Path) -> Path:
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def write_markdown_report(result: PrepareResult, output_path: str | Path) -> Path:
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(result.model_dump_json())
    recommendation = data["recommendation"]
    steps = "\n".join(f"{index + 1}. {step}" for index, step in enumerate(recommendation["bambu_studio_steps"]))
    warnings = result.warnings or result.final_inspection.warnings
    warning_text = "\n".join(f"- {warning}" for warning in warnings) if warnings else "- No remaining warnings."
    body = f"""# Bambu Print Prep Report

## Final Model

`{result.final_model_path}`

## Final Dimensions

- Width: {result.final_inspection.dimensions.width_mm:g} mm
- Depth: {result.final_inspection.dimensions.depth_mm:g} mm
- Height: {result.final_inspection.dimensions.height_mm:g} mm
- Triangles: {result.final_inspection.triangle_count}

## Recommended Bambu Studio Settings

- Layer height: {recommendation["layer_height_mm"]} mm
- Support type: {recommendation["support_type"]}
- Support style: {recommendation["support_style"]}
- Support placement: {recommendation["support_placement"]}
- Threshold angle: {recommendation["threshold_angle_degrees"]} degrees
- Top Z distance: {recommendation["top_z_distance_mm"]} mm
- Top interface layers: {recommendation["top_interface_layers"]}
- Brim: {"on" if recommendation["brim_enabled"] else "off"}
- Brim width: {recommendation["brim_width_mm"]} mm
- Wall loops: {recommendation["wall_loops"]}
- Infill: {recommendation["infill_percent"]}%

## Steps

{steps}

## Warnings

{warning_text}
"""
    path.write_text(body, encoding="utf-8")
    return path
```

- [ ] **Step 4: Implement prepare orchestration**

Create `src/bambu_print_prep_mcp/prepare.py`:

```python
from __future__ import annotations

from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.models import PrepareResult
from bambu_print_prep_mcp.recommendations import recommend_print_settings
from bambu_print_prep_mcp.repair import repair_model
from bambu_print_prep_mcp.reporting import write_json_report, write_markdown_report
from bambu_print_prep_mcp.security import ensure_output_dir, ensure_supported_input
from bambu_print_prep_mcp.transform import normalize_scale


def prepare_model_for_bambu(
    file_path: str | Path,
    output_dir: str | Path | None = None,
    printer: str = "bambu_lab_p2s",
    material: str = "PLA",
    target_height_mm: float | None = None,
    intent: str = "statue",
) -> PrepareResult:
    input_path = ensure_supported_input(file_path)
    directory = ensure_output_dir(output_dir, input_path)
    initial = inspect_model(input_path, printer=printer)

    repaired = repair_model(input_path, output_path=directory / f"{input_path.stem}_repaired.stl", printer=printer)
    current_model = Path(repaired.output_path)

    if target_height_mm is not None:
        scaled = normalize_scale(
            current_model,
            output_path=directory / f"{input_path.stem}_prepared.stl",
            target_height_mm=target_height_mm,
            printer=printer,
        )
        current_model = Path(scaled.output_path)
        warnings = repaired.warnings + scaled.warnings
    else:
        final_path = directory / f"{input_path.stem}_prepared.stl"
        current_model.replace(final_path)
        current_model = final_path
        warnings = repaired.warnings

    final = inspect_model(current_model, printer=printer)
    recommendation = recommend_print_settings(current_model, printer=printer, material=material, intent=intent)

    partial = PrepareResult(
        input_path=str(input_path),
        final_model_path=str(current_model),
        markdown_report_path=str(directory / f"{input_path.stem}_report.md"),
        json_report_path=str(directory / f"{input_path.stem}_report.json"),
        initial_inspection=initial,
        final_inspection=final,
        recommendation=recommendation,
        warnings=warnings + final.warnings,
    )
    markdown_path = write_markdown_report(partial, partial.markdown_report_path)
    json_path = write_json_report(partial, partial.json_report_path)
    return partial.model_copy(
        update={
            "markdown_report_path": str(markdown_path),
            "json_report_path": str(json_path),
        }
    )
```

- [ ] **Step 5: Verify prepare tests pass**

Run:

```bash
pytest tests/test_prepare.py -v
```

Expected: pass.

- [ ] **Step 6: Commit prepare workflow**

```bash
git add src/bambu_print_prep_mcp/reporting.py src/bambu_print_prep_mcp/prepare.py tests/test_prepare.py
git commit -m "feat: prepare STL outputs and reports"
```

---

### Task 9: MCP Server Tools

**Files:**
- Create: `src/bambu_print_prep_mcp/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write server tests**

Create `tests/test_server.py`:

```python
from bambu_print_prep_mcp.server import mcp


def test_mcp_server_is_named() -> None:
    assert mcp.name == "Bambu Print Prep MCP"
```

- [ ] **Step 2: Run server test to verify it fails**

Run:

```bash
pytest tests/test_server.py -v
```

Expected: fail because `server.py` does not exist.

- [ ] **Step 3: Implement MCP server**

Create `src/bambu_print_prep_mcp/server.py`:

```python
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from bambu_print_prep_mcp.analysis import inspect_model as inspect_model_core
from bambu_print_prep_mcp.prepare import prepare_model_for_bambu as prepare_model_for_bambu_core
from bambu_print_prep_mcp.recommendations import recommend_print_settings as recommend_print_settings_core
from bambu_print_prep_mcp.repair import repair_model as repair_model_core
from bambu_print_prep_mcp.transform import normalize_scale as normalize_scale_core

mcp = FastMCP("Bambu Print Prep MCP", json_response=True)


@mcp.tool()
def inspect_model(file_path: str, printer: str = "bambu_lab_p2s") -> dict:
    """Inspect an STL file for dimensions, mesh health, and Bambu printer fit."""
    return inspect_model_core(file_path, printer=printer).model_dump()


@mcp.tool()
def repair_model(
    file_path: str,
    output_path: str | None = None,
    preserve_scale: bool = True,
    printer: str = "bambu_lab_p2s",
) -> dict:
    """Repair an STL locally without overwriting the original."""
    return repair_model_core(
        file_path,
        output_path=output_path,
        preserve_scale=preserve_scale,
        printer=printer,
    ).model_dump()


@mcp.tool()
def normalize_scale(
    file_path: str,
    output_path: str | None = None,
    target_height_mm: float | None = None,
    target_width_mm: float | None = None,
    target_depth_mm: float | None = None,
    scale_factor: float | None = None,
    printer: str = "bambu_lab_p2s",
) -> dict:
    """Scale an STL to a target dimension or explicit scale factor."""
    return normalize_scale_core(
        file_path,
        output_path=output_path,
        target_height_mm=target_height_mm,
        target_width_mm=target_width_mm,
        target_depth_mm=target_depth_mm,
        scale_factor=scale_factor,
        printer=printer,
    ).model_dump()


@mcp.tool()
def recommend_print_settings(
    file_path: str,
    printer: str = "bambu_lab_p2s",
    material: str = "PLA",
    intent: str = "statue",
) -> dict:
    """Recommend Bambu Studio settings for a local STL file."""
    return recommend_print_settings_core(
        file_path,
        printer=printer,
        material=material,
        intent=intent,
    ).model_dump()


@mcp.tool()
def prepare_model_for_bambu(
    file_path: str,
    output_dir: str | None = None,
    printer: str = "bambu_lab_p2s",
    material: str = "PLA",
    target_height_mm: float | None = None,
    intent: str = "statue",
) -> dict:
    """Inspect, repair, optionally scale, and report Bambu Studio settings."""
    return prepare_model_for_bambu_core(
        file_path,
        output_dir=output_dir,
        printer=printer,
        material=material,
        target_height_mm=target_height_mm,
        intent=intent,
    ).model_dump()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify server tests pass**

Run:

```bash
pytest tests/test_server.py -v
```

Expected: pass.

- [ ] **Step 5: Commit MCP tools**

```bash
git add src/bambu_print_prep_mcp/server.py tests/test_server.py
git commit -m "feat: expose print prep MCP tools"
```

---

### Task 10: CLI Smoke-Test Interface

**Files:**
- Create: `src/bambu_print_prep_mcp/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write CLI tests**

Create `tests/test_cli.py`:

```python
from pathlib import Path

from bambu_print_prep_mcp.cli import main


def test_cli_inspect_returns_zero(cube_stl: Path, capsys) -> None:
    code = main(["inspect", str(cube_stl)])

    captured = capsys.readouterr()
    assert code == 0
    assert "cube.stl" in captured.out
```

- [ ] **Step 2: Run CLI test to verify it fails**

Run:

```bash
pytest tests/test_cli.py -v
```

Expected: fail because `cli.py` does not exist.

- [ ] **Step 3: Implement CLI**

Create `src/bambu_print_prep_mcp/cli.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.prepare import prepare_model_for_bambu


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bambu-print-prep")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("file_path")
    inspect_parser.add_argument("--printer", default="bambu_lab_p2s")

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("file_path")
    prepare_parser.add_argument("--output-dir", default=None)
    prepare_parser.add_argument("--printer", default="bambu_lab_p2s")
    prepare_parser.add_argument("--material", default="PLA")
    prepare_parser.add_argument("--target-height-mm", type=float, default=None)
    prepare_parser.add_argument("--intent", default="statue")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inspect":
        result = inspect_model(args.file_path, printer=args.printer)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "prepare":
        result = prepare_model_for_bambu(
            Path(args.file_path),
            output_dir=args.output_dir,
            printer=args.printer,
            material=args.material,
            target_height_mm=args.target_height_mm,
            intent=args.intent,
        )
        print(json.dumps(result.model_dump(), indent=2))
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verify CLI tests pass**

Run:

```bash
pytest tests/test_cli.py -v
```

Expected: pass.

- [ ] **Step 5: Commit CLI**

```bash
git add src/bambu_print_prep_mcp/cli.py tests/test_cli.py
git commit -m "feat: add local CLI smoke interface"
```

---

### Task 11: CI, Secret Scanning, And Public Push Readiness

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.secrets.baseline`
- Modify: `README.md`

- [ ] **Step 1: Create GitHub Actions workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - name: Lint
        run: ruff check .
      - name: Test
        run: pytest -v
      - name: Secret scan
        run: detect-secrets scan --baseline .secrets.baseline
```

- [ ] **Step 2: Run local quality checks**

Run:

```bash
ruff check .
pytest -v
detect-secrets scan > .secrets.baseline
detect-secrets audit .secrets.baseline
```

Expected:

```text
Ruff passes.
Pytest passes.
Secret baseline contains no real secrets.
```

- [ ] **Step 3: Expand README public safety section**

Append this to `README.md`:

```markdown
## Public Repository Safety Checklist

Before pushing publicly:

- Run `git status --short` and review every tracked file.
- Search tracked source files for local machine paths, personal identifiers, credentials, and generated-file metadata.
- Run `detect-secrets scan --baseline .secrets.baseline`.
- Confirm no personal model files, screenshots, reports, printer identifiers, or local paths are staged.
- Confirm generated outputs remain under ignored directories such as `outputs/`.
```

- [ ] **Step 4: Re-run checks**

Run:

```bash
ruff check .
pytest -v
detect-secrets scan --baseline .secrets.baseline
git grep -n -E "localhost|/Users|Desktop|TemporaryItems|access code|serial number" -- \
  ':!docs/superpowers/plans/**' ':!README.md'
```

Expected:

```text
No lint failures.
All tests pass.
No secrets detected.
No private local metadata appears in tracked source/docs.
```

- [ ] **Step 5: Commit CI and safety docs**

```bash
git add .github/workflows/ci.yml .secrets.baseline README.md
git commit -m "chore: add CI and public safety checks"
```

---

### Task 12: Final Local Verification And GitHub Publication Prep

**Files:**
- No source changes expected unless verification reveals an issue.

- [ ] **Step 1: Run full local verification**

Run:

```bash
ruff check .
pytest -v
detect-secrets scan --baseline .secrets.baseline
git status --short
```

Expected:

```text
Ruff passes.
All tests pass.
Secret scan passes.
Only intentional untracked local artifacts, if any, remain.
```

- [ ] **Step 2: Review tracked files**

Run:

```bash
git ls-files
```

Expected tracked files include source, tests, docs, config, and public-safe project docs. Expected tracked files do not include STL, 3MF, screenshots, reports, `.env`, local absolute-path fixtures, or generated output.

- [ ] **Step 3: Create public GitHub repository**

After the user confirms the repository name, run one of:

```bash
gh repo create bambu-print-prep-mcp --public --source . --remote origin --push
```

or, if the remote already exists:

```bash
git remote add origin git@github.com:<owner>/bambu-print-prep-mcp.git
git push -u origin main
```

Expected: public repo exists and `main` is pushed.

- [ ] **Step 4: Verify remote does not expose private data**

Run:

```bash
gh repo view --web
```

Manually inspect the GitHub file list and README. Confirm no private local files or model assets are present.
