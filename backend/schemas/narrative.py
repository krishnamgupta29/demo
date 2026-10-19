"""Pre-authorization narrative and procedure selection schemas."""

from typing import Optional
from pydantic import Field
from .base import ClinicalBaseModel
from .finding import UrgencyLevel


class CDTCodeReference(ClinicalBaseModel):
  """Demo reference to American Dental Association (ADA) Code on Dental Procedures and Nomenclature."""

  cdt_code: str = Field(
      ..., description="CDT procedure code (e.g., 'D2391')", examples=["D2391"]
  )
  display_name: str = Field(
      ..., description="Procedure terminology description"
  )
  category: str = Field(
      ...,
      description="Clinical category: Restorative, Endodontics, Periodontics, Oral Surgery",
  )
  disclaimer: str = Field(
      default="Demo code only; verify against current official ADA CDT code set.",
      frozen=True,
  )


class ProcedureSelection(ClinicalBaseModel):
  """Procedure proposed for a specific tooth with clinical rationale."""

  tooth_fdi: int = Field(..., description="Target tooth FDI number")
  procedure_name: str = Field(..., description="Proposed clinical procedure")
  cdt_reference: Optional[CDTCodeReference] = Field(
      default=None, description="Illustrative CDT code"
  )
  urgency: UrgencyLevel = Field(
      default=UrgencyLevel.ROUTINE, description="Procedural urgency"
  )
  clinical_justification: str = Field(
      ..., description="Objective clinical rationale grounded in observed facts"
  )


class PreAuthNarrativeDraft(ClinicalBaseModel):
  """Structured pre-authorization narrative grounded strictly in verified clinical facts."""

  draft_id: str = Field(..., description="Draft UUID: NARR-[UUID8]")
  study_id: str = Field(..., description="Associated study UUID")
  patient_anonymous_id: str = Field(..., description="Anonymous patient code")
  clinical_summary: str = Field(
      ...,
      description="Objective overview of panoramic radiograph findings and dental condition",
  )
  procedures: list[ProcedureSelection] = Field(
      default_factory=list,
      description="Itemized procedure justifications with demo CDT codes",
  )
  medical_necessity_statement: str = Field(
      ...,
      description="Synthesized medical necessity narrative for payer pre-authorization",
  )
  clinician_editable: bool = Field(
      default=True,
      description="Flag indicating narrative is in draft state and subject to clinician edit",
  )
  faithfulness_validated: bool = Field(
      default=False,
      description="Asserts narrative was verified against deterministic facts with 0 hallucinations",
  )
