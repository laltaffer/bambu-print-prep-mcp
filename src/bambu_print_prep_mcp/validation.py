from __future__ import annotations

import numpy as np
import trimesh

from bambu_print_prep_mcp.models import Dimensions, PrinterProfile

WRONG_UNITS_LARGE_FACTOR = 10.0
IMPLAUSIBLY_SMALL_MAX_AXIS_MM = 5.0
TINY_PART_MAX_AXIS_MM = 2.0


def ensure_usable_geometry(mesh: trimesh.Trimesh) -> None:
    bounds = mesh.bounds
    if (
        mesh.faces.size == 0
        or bounds is None
        or bounds.shape != (2, 3)
        or not np.isfinite(bounds).all()
    ):
        raise ValueError("Operation removed all usable geometry; refusing to write output.")


def fits_build_volume(dimensions: Dimensions, profile: PrinterProfile) -> bool:
    return (
        dimensions.width_mm <= profile.build_volume.width_mm
        and dimensions.depth_mm <= profile.build_volume.depth_mm
        and dimensions.height_mm <= profile.build_volume.height_mm
    )


def advisory_warnings(
    mesh: trimesh.Trimesh, dimensions: Dimensions, profile: PrinterProfile
) -> list[str]:
    warnings: list[str] = []
    if not fits_build_volume(dimensions, profile):
        warnings.append(
            f"Model is larger than the {profile.display_name} build volume "
            f"({profile.build_volume.width_mm:g} x {profile.build_volume.depth_mm:g} "
            f"x {profile.build_volume.height_mm:g} mm)."
        )
    if dimensions.max_axis_mm > profile.build_volume.max_axis_mm * WRONG_UNITS_LARGE_FACTOR:
        warnings.append(
            "Model is extremely large and may have wrong units — a unit smaller than "
            "a millimeter (such as micrometers) interpreted as millimeters."
        )
    elif 0 < dimensions.max_axis_mm < IMPLAUSIBLY_SMALL_MAX_AXIS_MM:
        warnings.append(
            "Model is implausibly small and may have wrong units — inches or meters "
            "interpreted as millimeters; consider scaling by 25.4 (inches) or "
            "1000 (meters)."
        )
    if not mesh.is_watertight:
        warnings.append("Mesh is not watertight and may need repair before slicing.")
    return warnings
