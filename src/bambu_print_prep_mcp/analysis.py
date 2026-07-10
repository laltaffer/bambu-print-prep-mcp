from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from pathlib import Path

from bambu_print_prep_mcp.mesh_io import load_mesh
from bambu_print_prep_mcp.models import Dimensions, MeshInspection, PrinterProfile
from bambu_print_prep_mcp.security import ensure_supported_input
from bambu_print_prep_mcp.validation import advisory_warnings, fits_build_volume

DEFAULT_PRINTER = "bambu_lab_p2s"


@cache
def load_printer_profile(printer: str = DEFAULT_PRINTER) -> PrinterProfile:
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


def inspect_model(file_path: str | Path, printer: str = DEFAULT_PRINTER) -> MeshInspection:
    path = ensure_supported_input(file_path)
    profile = load_printer_profile(printer)
    mesh = load_mesh(path)
    dimensions = dimensions_from_bounds(mesh.bounds.tolist())
    warnings = advisory_warnings(mesh, dimensions, profile)
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
        fits_build_volume=fits_build_volume(dimensions, profile),
        warnings=warnings,
        summary=summary,
    )
