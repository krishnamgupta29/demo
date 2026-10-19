"""Base Pydantic schema enforcing immutable clinical regulatory disclaimers."""

from pydantic import BaseModel, ConfigDict, Field


class ClinicalBaseModel(BaseModel):
  """Base schema for all DENTRACE clinical data models.

  Enforces:
  1. Immutable regulatory disclaimer present on all payloads.
  2. Strict validation and population by name.
  3. JSON schema serialization compatibility.
  """

  model_config = ConfigDict(
      populate_by_name=True,
      validate_assignment=True,
      str_strip_whitespace=True,
  )

  disclaimer: str = Field(
      default="Draft for dentist review. Not a diagnosis.",
      description=(
          "Mandatory regulatory notice. Must be preserved in all API outputs,"
          " screens, and exports."
      ),
      frozen=True,
  )
