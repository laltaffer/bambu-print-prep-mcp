from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class Dimensions(BaseModel):
    width_mm: float = Field(ge=0, allow_inf_nan=False)
    depth_mm: float = Field(ge=0, allow_inf_nan=False)
    height_mm: float = Field(ge=0, allow_inf_nan=False)

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
    scale_factor: float = Field(gt=0, allow_inf_nan=False)
    fits_build_volume: bool
    warnings: list[str] = Field(default_factory=list)


class PrintSettingsRecommendation(BaseModel):
    printer: str
    material: str
    intent: str
    layer_height_mm: float = Field(gt=0, allow_inf_nan=False)
    support_type: str
    support_style: str
    support_placement: str
    threshold_angle_degrees: int = Field(ge=0, le=90)
    top_z_distance_mm: float = Field(ge=0, allow_inf_nan=False)
    top_interface_layers: int = Field(ge=0)
    brim_enabled: bool
    brim_width_mm: float = Field(ge=0, allow_inf_nan=False)
    wall_loops: int = Field(ge=0)
    infill_percent: int = Field(ge=0, le=100)
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
