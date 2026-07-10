from __future__ import annotations

from pydantic import BaseModel, Field


class Dimensions(BaseModel):
    width_mm: float = Field(ge=0, allow_inf_nan=False)
    depth_mm: float = Field(ge=0, allow_inf_nan=False)
    height_mm: float = Field(ge=0, allow_inf_nan=False)

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


class OperationResult(BaseModel):
    input_path: str
    output_path: str
    inspection: MeshInspection
    warnings: list[str] = Field(default_factory=list)


class PartsResult(BaseModel):
    input_path: str
    output_paths: list[str]
    parts: list[MeshInspection]
    warnings: list[str] = Field(default_factory=list)


class ScaleResult(BaseModel):
    input_path: str
    output_path: str
    original_dimensions: Dimensions
    new_dimensions: Dimensions
    scale_factor: float = Field(gt=0, allow_inf_nan=False)
    fits_build_volume: bool
    warnings: list[str] = Field(default_factory=list)


