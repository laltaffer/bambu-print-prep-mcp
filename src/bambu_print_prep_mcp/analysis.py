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
