"""ADA CDT Demonstrative Coding Layer for Academic Decision Support.

LEGAL & CLINICAL BOUNDARIES:
- Current Dental Terminology (CDT) is copyright American Dental Association (ADA).
- This module implements a limited, illustrative academic subset for college demonstration.
- CDT codes do NOT guarantee insurance pre-authorization or payment.
- The system NEVER autonomously selects or bills procedure codes from AI detections.
- Candidate code suggestions are strictly unverified proposals requiring explicit dentist review and attestation.
"""

from typing import Optional
from pydantic import Field
from ..schemas.base import ClinicalBaseModel
from ..schemas.finding import PathologyClass


CDT_CATALOG_VERSION = "2026-Academic-Demo"
CDT_CATALOG_SOURCE = "ADA CDT Demonstrative Academic Subset (College Project)"
CDT_EFFECTIVE_DATE = "2026-01-01"


class CDTCodeMetadata(ClinicalBaseModel):
  """Strongly typed demonstrative CDT code specification with licensing and version metadata."""

  cdt_code: str = Field(..., description="CDT procedure code (e.g. 'D2391')")
  display_name: str = Field(..., description="Official clinical nomenclature title")
  category: str = Field(..., description="Specialty: Restorative, Endodontics, Oral Surgery, Periodontics, Diagnostic")
  version: str = Field(default=CDT_CATALOG_VERSION, frozen=True)
  source: str = Field(default=CDT_CATALOG_SOURCE, frozen=True)
  effective_date: str = Field(default=CDT_EFFECTIVE_DATE, frozen=True)
  description: str = Field(...)
  documentation_requirements: list[str] = Field(
      default_factory=list,
      description="List of clinical evidence prerequisites required for claim submission",
  )
  coverage_guarantee_notice: str = Field(
      default="Code inclusion does not guarantee payer coverage, pre-authorization, or reimbursement.",
      frozen=True,
  )


# Demonstrative subset for academic evaluation only
DEMO_CDT_CATALOG: dict[str, CDTCodeMetadata] = {
    "D0140": CDTCodeMetadata(
        cdt_code="D0140",
        display_name="Limited Oral Evaluation - Problem Focused",
        category="Diagnostic",
        description="Evaluation limited to a specific dental health problem or complaint.",
        documentation_requirements=["chief_complaint", "clinical_findings"],
    ),
    "D0220": CDTCodeMetadata(
        cdt_code="D0220",
        display_name="Intraoral - Periapical First Radiographic Image",
        category="Diagnostic",
        description="Periapical radiograph centered on tooth apex and surrounding bone.",
        documentation_requirements=["radiograph_attachment", "clinical_indication"],
    ),
    "D2140": CDTCodeMetadata(
        cdt_code="D2140",
        display_name="Amalgam - One Surface, Primary or Permanent",
        category="Restorative",
        description="Direct restorative restoration involving one surface.",
        documentation_requirements=["radiographic_caries", "tooth_fdi", "surface_specified"],
    ),
    "D2391": CDTCodeMetadata(
        cdt_code="D2391",
        display_name="Resin-Based Composite - One Surface, Posterior",
        category="Restorative",
        description="Direct composite restoration on a single posterior surface.",
        documentation_requirements=["radiographic_caries", "tooth_fdi", "surface_specified"],
    ),
    "D2392": CDTCodeMetadata(
        cdt_code="D2392",
        display_name="Resin-Based Composite - Two Surfaces, Posterior",
        category="Restorative",
        description="Direct composite restoration involving two posterior surfaces (e.g., MO, DO).",
        documentation_requirements=["radiographic_caries", "tooth_fdi", "surfaces_specified"],
    ),
    "D3330": CDTCodeMetadata(
        cdt_code="D3330",
        display_name="Endodontic Therapy - Molar Tooth (Excluding Final Restoration)",
        category="Endodontics",
        description="Complete root canal treatment on permanent molar tooth.",
        documentation_requirements=[
            "periapical_radiograph",
            "pulp_vitality_test",
            "percussion_sensitivity",
            "tooth_fdi",
            "clinician_rationale",
        ],
    ),
    "D3320": CDTCodeMetadata(
        cdt_code="D3320",
        display_name="Endodontic Therapy - Premolar Tooth (Excluding Final Restoration)",
        category="Endodontics",
        description="Complete root canal treatment on permanent premolar tooth.",
        documentation_requirements=[
            "periapical_radiograph",
            "pulp_vitality_test",
            "percussion_sensitivity",
            "tooth_fdi",
            "clinician_rationale",
        ],
    ),
    "D7140": CDTCodeMetadata(
        cdt_code="D7140",
        display_name="Extraction, Erupted Tooth or Exposed Root",
        category="Oral Surgery",
        description="Extraction of erupted tooth including elevation and forceps removal.",
        documentation_requirements=["radiograph_attachment", "tooth_fdi", "clinical_indication"],
    ),
    "D7210": CDTCodeMetadata(
        cdt_code="D7210",
        display_name="Extraction, Erupted Tooth Requiring Removal of Bone and/or Sectioning",
        category="Oral Surgery",
        description="Surgical extraction requiring bone removal, sectioning of tooth, or elevation of flap.",
        documentation_requirements=["radiograph_attachment", "tooth_fdi", "surgical_rationale"],
    ),
    "D7230": CDTCodeMetadata(
        cdt_code="D7230",
        display_name="Removal of Impacted Tooth - Partially Bony",
        category="Oral Surgery",
        description="Surgical removal of partially impacted tooth requiring flap and bone removal.",
        documentation_requirements=["radiograph_attachment", "tooth_fdi", "impaction_classification"],
    ),
    "D7240": CDTCodeMetadata(
        cdt_code="D7240",
        display_name="Removal of Impacted Tooth - Completely Bony",
        category="Oral Surgery",
        description="Surgical removal of completely bony impacted tooth.",
        documentation_requirements=["radiograph_attachment", "tooth_fdi", "impaction_classification"],
    ),
    "D4341": CDTCodeMetadata(
        cdt_code="D4341",
        display_name="Periodontal Scaling and Root Planing - Four or More Teeth per Quadrant",
        category="Periodontics",
        description="Therapeutic instrumentation of crown and root surfaces.",
        documentation_requirements=["probing_depth_chart", "radiographic_bone_loss", "quadrant_specified"],
    ),
}


class CDTCodingService:
  """Deterministic CDT code helper verifying consistency and documentation requirements."""

  @classmethod
  def get_code_metadata(cls, cdt_code: str) -> Optional[CDTCodeMetadata]:
    """Retrieves metadata for a known CDT code, or None if unrecognized."""
    return DEMO_CDT_CATALOG.get(cdt_code.upper().strip())

  @classmethod
  def suggest_candidate_codes(
      cls,
      pathology: PathologyClass,
      tooth_fdi: Optional[int] = None,
      is_deep: bool = False,
  ) -> list[CDTCodeMetadata]:
    """Generates non-authoritative candidate codes for clinician consideration.

    CRITICAL RULE: Returned candidates must be flagged as unverified and suppressed
    if insufficient clinical information exists.
    """
    candidates = []
    if pathology in (PathologyClass.CARIES, PathologyClass.DEEP_CARIES):
      candidates.append(DEMO_CDT_CATALOG["D2391"])
      candidates.append(DEMO_CDT_CATALOG["D2392"])
      if is_deep and tooth_fdi is not None:
        # If tooth is molar (16-18, 26-28, 36-38, 46-48)
        if tooth_fdi % 10 in (6, 7, 8):
          candidates.append(DEMO_CDT_CATALOG["D3330"])
        elif tooth_fdi % 10 in (4, 5):
          candidates.append(DEMO_CDT_CATALOG["D3320"])
    elif pathology == PathologyClass.PERIAPICAL_LESION:
      if tooth_fdi is not None:
        if tooth_fdi % 10 in (6, 7, 8):
          candidates.append(DEMO_CDT_CATALOG["D3330"])
        elif tooth_fdi % 10 in (4, 5):
          candidates.append(DEMO_CDT_CATALOG["D3320"])
        candidates.append(DEMO_CDT_CATALOG["D7140"])
    elif pathology == PathologyClass.IMPACTED_TOOTH:
      candidates.append(DEMO_CDT_CATALOG["D7230"])
      candidates.append(DEMO_CDT_CATALOG["D7240"])
    elif pathology == PathologyClass.ALVEOLAR_BONE_LOSS:
      candidates.append(DEMO_CDT_CATALOG["D4341"])

    return candidates

  @classmethod
  def validate_code_consistency(
      cls,
      cdt_code: str,
      proposed_procedure: str,
      tooth_fdi: Optional[int],
  ) -> tuple[bool, Optional[str]]:
    """Checks rule-based consistency between CDT code and proposed procedure."""
    meta = cls.get_code_metadata(cdt_code)
    if not meta:
      return False, f"CDT code '{cdt_code}' is not in the recognized demonstrative academic catalog."

    proc_lower = proposed_procedure.lower()

    # Molar vs premolar check for endodontics
    if cdt_code == "D3330" and tooth_fdi is not None:
      pos = tooth_fdi % 10
      if pos not in (6, 7, 8):
        return False, f"Code D3330 is specific to molar teeth (positions 6-8), but target tooth FDI is {tooth_fdi}."

    if cdt_code == "D3320" and tooth_fdi is not None:
      pos = tooth_fdi % 10
      if pos not in (4, 5):
        return False, f"Code D3320 is specific to premolar teeth (positions 4-5), but target tooth FDI is {tooth_fdi}."

    # Surgical extraction vs simple extraction
    if cdt_code in ("D7230", "D7240") and "impact" not in proc_lower and "surgical" not in proc_lower:
      return False, f"CDT code {cdt_code} indicates impacted tooth removal, but proposed procedure '{proposed_procedure}' does not specify impaction surgery."

    return True, None
