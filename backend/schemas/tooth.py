"""FDI two-digit tooth notation and tooth boundary schemas."""

from typing import Annotated, Any, Optional
from pydantic import Field, field_validator
from .base import ClinicalBaseModel

VALID_FDI_TEETH = {
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,  # Upper Right
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,  # Upper Left
    31,
    32,
    33,
    34,
    35,
    36,
    37,
    38,  # Lower Left
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,  # Lower Right
}

# Complete horizontal flip swap mapping across the vertical facial midline
FDI_HORIZONTAL_FLIP_MAP: dict[int, int] = {
    # Maxilla: Q1 (Upper Right) <-> Q2 (Upper Left)
    11: 21, 12: 22, 13: 23, 14: 24, 15: 25, 16: 26, 17: 27, 18: 28,
    21: 11, 22: 12, 23: 13, 24: 14, 25: 15, 26: 16, 27: 17, 28: 18,
    # Mandible: Q4 (Lower Right) <-> Q3 (Lower Left)
    41: 31, 42: 32, 43: 33, 44: 34, 45: 35, 46: 36, 47: 37, 48: 38,
    31: 41, 32: 42, 33: 43, 34: 44, 35: 45, 36: 46, 37: 47, 38: 48,
}


def swap_fdi_horizontal_flip(fdi_number: Optional[int]) -> Optional[int]:
  """Swaps FDI tooth number across the vertical facial midline under horizontal flip augmentation."""
  if fdi_number is None:
    return None
  return FDI_HORIZONTAL_FLIP_MAP.get(fdi_number, fdi_number)


class ToothBox(ClinicalBaseModel):
  """Bounding box localization of a single permanent tooth in FDI notation."""

  fdi_number: Optional[int] = Field(
      default=None,
      description=(
          "Two-digit FDI permanent tooth number (11-18, 21-28, 31-38, 41-48), "
          "or None if ambiguous/uncertain"
      ),
      examples=[16, 21, 38, 46],
  )
  x_min: float = Field(..., ge=0.0, description="Minimum X coordinate in pixels")
  y_min: float = Field(..., ge=0.0, description="Minimum Y coordinate in pixels")
  x_max: float = Field(..., gt=0.0, description="Maximum X coordinate in pixels")
  y_max: float = Field(..., gt=0.0, description="Maximum Y coordinate in pixels")
  confidence: float = Field(
      ..., ge=0.0, le=1.0, description="Detection confidence score"
  )
  uncertain_tooth: bool = Field(
      default=False,
      description="True when tooth numbering is ambiguous or marginal"
  )

  @field_validator("fdi_number")
  @classmethod
  def validate_fdi(cls, v: Optional[int]) -> Optional[int]:
    if v is not None and v not in VALID_FDI_TEETH:
      raise ValueError(
          f"Invalid FDI permanent tooth number: {v}. Must be in {sorted(VALID_FDI_TEETH)}"
      )
    return v

  @field_validator("x_max")
  @classmethod
  def validate_x_bounds(cls, v: float, info) -> float:
    if "x_min" in info.data and v <= info.data["x_min"]:
      raise ValueError(f"x_max ({v}) must be strictly greater than x_min")
    return v

  @field_validator("y_max")
  @classmethod
  def validate_y_bounds(cls, v: float, info) -> float:
    if "y_min" in info.data and v <= info.data["y_min"]:
      raise ValueError(f"y_max ({v}) must be strictly greater than y_min")
    return v

  @property
  def quadrant(self) -> Optional[int]:
    return (self.fdi_number // 10) if self.fdi_number else None

  @property
  def position(self) -> Optional[int]:
    return (self.fdi_number % 10) if self.fdi_number else None

  @property
  def area(self) -> float:
    return (self.x_max - self.x_min) * (self.y_max - self.y_min)


class ToothSegmentationPolygon(ClinicalBaseModel):
  """True pixel polygon contour of an individual permanent tooth."""

  fdi_number: int = Field(
      ...,
      description="Two-digit FDI permanent tooth number",
      examples=[16, 26, 36, 46],
  )
  points: list[list[float]] = Field(
      ...,
      min_length=3,
      description="Ordered list of [x, y] polygon vertices tracing tooth boundary",
  )
  confidence: float = Field(
      default=1.0, ge=0.0, le=1.0, description="Segmentation confidence"
  )

  @field_validator("fdi_number")
  @classmethod
  def validate_fdi(cls, v: int) -> int:
    if v not in VALID_FDI_TEETH:
      raise ValueError(f"Invalid FDI permanent tooth number: {v}")
    return v

  @field_validator("points")
  @classmethod
  def validate_polygon_points(
      cls, pts: list[list[float]]
  ) -> list[list[float]]:
    for pt in pts:
      if len(pt) != 2:
        raise ValueError(
            f"Polygon vertex must be [x, y] pair, got {pt} of length {len(pt)}"
        )
      if pt[0] < 0 or pt[1] < 0:
        raise ValueError(f"Polygon coordinates must be non-negative, got {pt}")
    return pts
