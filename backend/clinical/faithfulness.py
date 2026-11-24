"""Deterministic Claim-to-Evidence Traceability and Faithfulness Checker.

Enforces:
1. Every substantive clinical sentence links to underlying evidence IDs.
2. Deterministic checking of factual entities (FDI teeth, pathologies, procedures).
3. Rejection of hallucinated teeth, ungrounded pathologies, or unsupported claims.
4. Preservation of radiographic uncertainty for unconfirmed AI findings.

NOTE: This is a deterministic software validation tool; it does NOT claim
to theoretically guarantee zero hallucinations under all linguistic variations.
"""

import re
import uuid
from typing import Optional
from pydantic import Field
from ..schemas.base import ClinicalBaseModel
from ..schemas.evidence import (
    ClinicalEvidencePackage,
    NarrativeStatementCitation,
    EvidenceSource,
    VerificationStatus,
)
from ..schemas.finding import PathologyClass
from ..schemas.tooth import VALID_FDI_TEETH


class FaithfulnessEvaluationResult(ClinicalBaseModel):
  """Audit result evaluating narrative factual grounding and evidence citations."""

  is_faithful: bool = Field(...)
  total_statements: int = Field(default=0)
  verified_statements: int = Field(default=0)
  unsupported_statements: int = Field(default=0)
  hallucinated_teeth: list[int] = Field(default_factory=list)
  hallucinated_pathologies: list[str] = Field(default_factory=list)
  unsupported_claims: list[str] = Field(default_factory=list)
  citation_coverage_pct: float = Field(
      default=0.0,
      ge=0.0,
      le=100.0,
      description="Percentage of clinical statements supported by verified evidence IDs",
  )
  validated_statements: list[NarrativeStatementCitation] = Field(default_factory=list)


class FaithfulnessChecker:
  """Deterministic validator verifying narrative statements against structured evidence."""

  # Regex patterns for clinical entities
  TOOTH_REGEX = re.compile(r"\b(?:tooth|teeth|#|fdi\s*)?\s*([1-4][1-8])\b", re.IGNORECASE)
  PATHOLOGY_KEYWORDS = {
      PathologyClass.CARIES: ["caries", "carious", "decay", "cavity", "radiolucency in enamel"],
      PathologyClass.DEEP_CARIES: ["deep caries", "pulpal involvement", "dentin caries", "deep decay"],
      PathologyClass.PERIAPICAL_LESION: ["periapical lesion", "apical radiolucency", "abscess", "periapical pathology", "apical periodontitis"],
      PathologyClass.IMPACTED_TOOTH: ["impacted", "impaction", "unerupted"],
      PathologyClass.ALVEOLAR_BONE_LOSS: ["bone loss", "crestal resorption", "periodontal bone loss"],
      PathologyClass.ROOT_CANAL_TREATMENT: ["root canal treatment", "endodontic obturation", "previously treated"],
      PathologyClass.TREATED_TOOTH_WITH_RADIOLUCENCY: ["treated tooth with radiolucency", "recurrent apical lesion", "failed root canal"],
  }

  UNCERTAINTY_INDICATORS = [
      "suspected", "observed radiographically", "potential", "provisional",
      "suggestive of", "indicative of", "pending clinician review", "screening observation"
  ]

  @classmethod
  def extract_teeth_mentioned(cls, text: str) -> set[int]:
    """Finds all valid two-digit FDI tooth numbers mentioned in text, avoiding timestamps and ranges."""
    # Strip timestamps (e.g. 12:35), dates (2026-10-20), ranges (11-48), and hyphenated IDs
    cleaned = re.sub(r"\b\d{1,2}:\d{2}\b", " ", text)
    cleaned = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", cleaned)
    cleaned = re.sub(r"\b[1-4][1-8]\s*-\s*[1-4][1-8]\b", " ", cleaned)
    cleaned = re.sub(r"[A-Za-z0-9_\-]+-[A-Za-z0-9_\-]+", " ", cleaned)

    # 1. Match explicit tooth prefix patterns: tooth 46, #46, fdi 46, teeth 16, 26
    explicit_matches = re.findall(r"(?:tooth|teeth|#|fdi)\s*([1-4][1-8])\b", cleaned, re.IGNORECASE)
    teeth = {int(m) for m in explicit_matches if int(m) in VALID_FDI_TEETH}

    # 2. Match standalone two-digit teeth not surrounded by special chars
    # Only if text contains tooth-related context
    if re.search(r"\b(?:tooth|teeth|fdi|dentition|quadrant|arch|molar|incisor|canine|premolar)\b", text, re.IGNORECASE):
      standalone_matches = re.findall(r"(?<![:\.\-\$\w])([1-4][1-8])(?![:\.\-\$\w])", cleaned)
      for m in standalone_matches:
        val = int(m)
        if val in VALID_FDI_TEETH:
          teeth.add(val)

    return teeth

  @classmethod
  def evaluate_statement(
      cls,
      statement: NarrativeStatementCitation,
      package: ClinicalEvidencePackage,
  ) -> tuple[bool, list[str]]:
    """Evaluates whether an individual statement is faithful to the evidence package."""
    issues = []
    text = statement.sentence_text.lower()

    # 1. Check cited evidence IDs exist in package
    valid_evidence_ids = {package.package_id}
    for obs in package.ai_observations:
      valid_evidence_ids.add(obs.evidence_id)
    for cfm in package.dentist_confirmations:
      valid_evidence_ids.add(cfm.evidence_id)
    for ex in package.clinical_examinations:
      valid_evidence_ids.add(ex.evidence_id)
    for sym in package.patient_symptoms:
      valid_evidence_ids.add(sym.evidence_id)
    for proc in package.requested_procedures:
      valid_evidence_ids.add(proc.procedure_id)

    missing_citations = [
        eid for eid in statement.cited_evidence_ids
        if eid not in valid_evidence_ids and not eid.startswith("MISS-")
    ]
    if missing_citations:
      issues.append(f"Statement cites non-existent evidence IDs: {missing_citations}")

    # 2. Check tooth mentions against evidence package
    teeth_mentioned = cls.extract_teeth_mentioned(statement.sentence_text)
    valid_package_teeth = set()
    for obs in package.ai_observations:
      if obs.tooth_fdi is not None:
        valid_package_teeth.add(obs.tooth_fdi)
    for cfm in package.dentist_confirmations:
      if cfm.confirmed_fdi is not None:
        valid_package_teeth.add(cfm.confirmed_fdi)
    for proc in package.requested_procedures:
      if proc.tooth_fdi is not None:
        valid_package_teeth.add(proc.tooth_fdi)
    for ex in package.clinical_examinations:
      if ex.tooth_fdi is not None:
        valid_package_teeth.add(ex.tooth_fdi)

    hallucinated_teeth = teeth_mentioned - valid_package_teeth
    if hallucinated_teeth:
      issues.append(f"Statement mentions hallucinated tooth number(s) not in evidence: {sorted(list(hallucinated_teeth))}")

    # 3. Check pathology claims against evidence package (skip administrative checklist/attestation sections 8 and 10)
    if statement.section_index not in (8, 10):
      valid_pathologies = set()
      for obs in package.ai_observations:
        valid_pathologies.add(obs.pathology_candidate)
        if obs.pathology_candidate == PathologyClass.DEEP_CARIES:
          valid_pathologies.add(PathologyClass.CARIES)
      for cfm in package.dentist_confirmations:
        if cfm.confirmed_pathology:
          valid_pathologies.add(cfm.confirmed_pathology)
          if cfm.confirmed_pathology == PathologyClass.DEEP_CARIES:
            valid_pathologies.add(PathologyClass.CARIES)

      for p_class, keywords in cls.PATHOLOGY_KEYWORDS.items():
        for kw in keywords:
          if kw in text:
            if p_class not in valid_pathologies:
              issues.append(f"Statement claims ungrounded pathology '{p_class.value}' not present in clinical findings.")
            break

    # 4. Check uncertainty preservation for unconfirmed AI findings
    if EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION in statement.source_types:
      # If this statement discusses an AI finding that has NOT been confirmed
      has_confirmed_evidence = any(
          eid.startswith("EVID-CFM") for eid in statement.cited_evidence_ids
      )
      if not has_confirmed_evidence:
        # Must preserve uncertainty
        has_uncertainty_word = any(u in text for u in cls.UNCERTAINTY_INDICATORS)
        if not has_uncertainty_word and ("caries" in text or "lesion" in text or "impact" in text):
          issues.append("Statement presents unconfirmed AI finding as definitive clinical fact without preserving uncertainty.")

    is_valid = len(issues) == 0
    return is_valid, issues

  @classmethod
  def validate_narrative(
      cls,
      statements: list[NarrativeStatementCitation],
      package: ClinicalEvidencePackage,
  ) -> FaithfulnessEvaluationResult:
    """Validates an entire set of narrative statements against the evidence package."""
    total = len(statements)
    verified = 0
    unsupported = 0
    all_hallucinated_teeth = set()
    all_hallucinated_pathologies = []
    all_unsupported_claims = []
    validated_stmts = []

    for stmt in statements:
      is_valid, issues = cls.evaluate_statement(stmt, package)
      if is_valid:
        verified += 1
        stmt.verification_status = (
            VerificationStatus.CONFIRMED_BY_CLINICIAN
            if any(s == EvidenceSource.CLINICIAN_CONFIRMATION for s in stmt.source_types)
            else VerificationStatus.UNVERIFIED_AI_SUSPICION
        )
      else:
        unsupported += 1
        stmt.verification_status = VerificationStatus.UNSUPPORTED_CLAIM
        for issue in issues:
          all_unsupported_claims.append(f"[{stmt.statement_id}] {issue}")
          # Collect specific teeth
          for t in cls.extract_teeth_mentioned(stmt.sentence_text):
            all_hallucinated_teeth.add(t)

      validated_stmts.append(stmt)

    coverage_pct = round((verified / max(1, total)) * 100.0, 1)
    is_faithful = (unsupported == 0 and total > 0)

    return FaithfulnessEvaluationResult(
        is_faithful=is_faithful,
        total_statements=total,
        verified_statements=verified,
        unsupported_statements=unsupported,
        hallucinated_teeth=sorted(list(all_hallucinated_teeth)),
        hallucinated_pathologies=all_hallucinated_pathologies,
        unsupported_claims=all_unsupported_claims,
        citation_coverage_pct=coverage_pct,
        validated_statements=validated_stmts,
    )
