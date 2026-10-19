"""FDI two-digit tooth notation and tooth boundary schemas."""

from typing import Annotated, Any
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


class ToothBox(ClinicalBaseModel):
  """Bounding box localization of a single permanent tooth in FDI notation."""

  fdi_number: int = Field(
      ...,
      description=(
          "Two-digit FDI permanent tooth number (11-18, 21-28, 31-38, 41-48)"
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

  @field_validator("fdi_number")
  @classmethod
  def validate_fdi(cls, v: int) -> int:
    if v not in VALID_FDI_TEETH:
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
  def quadrant(self) -> int:
    return self.fdi_number // 10

  @property
  def position(self) -> int:
    return self.fdi_number % 10

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
