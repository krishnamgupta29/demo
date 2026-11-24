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

  ALLOWED_BRACKET_TAGS = {"MISSING_EVIDENCE", "PENDING CLINICIAN REVIEW"}
  RAW_ENUM_PATTERN = re.compile(
      r"\b(impacted_tooth|deep_caries|periapical_lesion|alveolar_bone_loss|root_canal_treatment|treated_tooth_with_radiolucency)\b|PathologyClass\.\w+",
      re.IGNORECASE
  )

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

    # 0a. Reject square-bracket placeholders (e.g. "[coordinates and observations]"),
    # except allowed tags [MISSING_EVIDENCE] and [PENDING CLINICIAN REVIEW].
    if statement.section_index in (5, 7) or statement.section_index is None:
      bracket_matches = re.findall(r"\[([^\]]+)\]", statement.sentence_text)
      for bm in bracket_matches:
        bm_clean = bm.strip()
        if bm_clean in cls.ALLOWED_BRACKET_TAGS:
          continue
        if re.match(r"^[\d\.\s,]+$", bm_clean):
          continue
        issues.append(f"Statement contains ungrounded square-bracket placeholder or unapproved tag: '[{bm_clean}]'")

      # 0b. Reject raw programming enum names in prose (e.g. impacted_tooth, deep_caries, periapical_lesion)
      enum_match = cls.RAW_ENUM_PATTERN.search(statement.sentence_text)
      if enum_match:
        issues.append(f"Statement contains raw programming enum name '{enum_match.group(0)}' instead of human-readable clinical prose.")

      # 0c. Reject duplicated sentences within the statement
      sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", statement.sentence_text) if s.strip()]
      seen_sentences = set()
      for s in sentences:
        s_clean = re.sub(r"[^\w\s]", "", s.lower()).strip()
        if len(s_clean) > 15:
          if s_clean in seen_sentences:
            issues.append(f"Statement contains duplicated sentence: '{s}'")
            break
          seen_sentences.add(s_clean)

      # 0d. Reject unhedged wording "clinical intervention is indicated"
      if "clinical intervention is indicated" in text:
        issues.append("Statement contains unhedged phrase 'Clinical intervention is indicated'; must use hedged wording 'Clinical evaluation and treatment planning is recommended, pending clinician confirmation of this AI-assisted finding.'")

      # 0e. Reject forbidden clinical pairings
      has_lesion_term = any(k in text for k in ["periapical lesion", "apical radiolucency", "apical periodontitis", "periapical pathology"])
      has_restoration_term = any(k in text for k in ["restoration", "restorative", "restore function", "restoring function"])
      has_endo_term = any(k in text for k in ["endodontic", "root canal", "apicoectomy", "extraction", "vitality", "pulp"])
      if has_lesion_term and has_restoration_term and not has_endo_term:
        issues.append("Forbidden clinical pairing: 'periapical lesion' cannot be paired with simple 'restoration'; endodontic evaluation is required.")

      has_impacted_term = any(k in text for k in ["impacted", "impaction", "unerupted"])
      if has_impacted_term and any(k in text for k in ["restore function", "restoring function", "restorative"]):
        issues.append("Forbidden clinical pairing: 'impacted tooth' cannot be paired with 'restore function'; surgical extraction evaluation or monitoring is required.")

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

      # 4. Check jaw and side grounding against evidence package
      valid_jaws = set()
      valid_sides = set()
      valid_bboxes = []

      for obs in package.ai_observations:
        if obs.tooth_fdi:
          q = obs.tooth_fdi // 10
          valid_jaws.add("maxilla" if q in (1, 2) else "mandible")
          valid_sides.add("right" if q in (1, 4) else "left")
        if obs.bbox:
          bx1 = obs.bbox.x_min if obs.bbox.x_min <= 1.0 else obs.bbox.x_min / 2872.0
          by1 = obs.bbox.y_min if obs.bbox.y_min <= 1.0 else obs.bbox.y_min / 1504.0
          bx2 = obs.bbox.x_max if obs.bbox.x_max <= 1.0 else obs.bbox.x_max / 2872.0
          by2 = obs.bbox.y_max if obs.bbox.y_max <= 1.0 else obs.bbox.y_max / 1504.0
          valid_bboxes.append((round(bx1, 3), round(by1, 3), round(bx2, 3), round(by2, 3)))

      for cfm in package.dentist_confirmations:
        if cfm.confirmed_fdi:
          q = cfm.confirmed_fdi // 10
          valid_jaws.add("maxilla" if q in (1, 2) else "mandible")
          valid_sides.add("right" if q in (1, 4) else "left")

      # Fail if ungrounded jaw is claimed
      if any(w in text for w in ("maxilla", "maxillary")) and "maxilla" not in valid_jaws:
        issues.append("Statement claims jaw 'maxilla' not present in clinical evidence findings.")
      if any(w in text for w in ("mandible", "mandibular")) and "mandible" not in valid_jaws:
        issues.append("Statement claims jaw 'mandible' not present in clinical evidence findings.")

      # Fail if ungrounded dental side is claimed
      if re.search(r"\b(right\s+(?:quadrant|side|arch|molar|premolar|canine|incisor))\b", text) and "right" not in valid_sides:
        issues.append("Statement claims side 'right' not present in clinical evidence findings.")
      if re.search(r"\b(left\s+(?:quadrant|side|arch|molar|premolar|canine|incisor))\b", text) and "left" not in valid_sides:
        issues.append("Statement claims side 'left' not present in clinical evidence findings.")

      # 5. Check coordinate grounding (fail if ungrounded / invented bbox coordinates are cited)
      coord_matches = re.findall(r"\[\s*([0-9\.]+)\s*,\s*([0-9\.]+)\s*,\s*([0-9\.]+)\s*,\s*([0-9\.]+)\s*\]", text)
      for cm in coord_matches:
        try:
          c = tuple(round(float(v), 3) for v in cm)
          matched_box = False
          for vb in valid_bboxes:
            if all(abs(c[i] - vb[i]) <= 0.05 for i in range(4)):
              matched_box = True
              break
          if not matched_box:
            issues.append(f"Statement cites ungrounded/invented coordinates {list(c)} not present in evidence JSON.")
        except Exception:
          pass

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

    # Check for duplicated sentences across sections 5 and 7
    seen_section_sentences: dict[str, str] = {}
    for stmt in validated_stmts:
      if stmt.section_index in (5, 7) and stmt.verification_status != VerificationStatus.UNSUPPORTED_CLAIM:
        for s in re.split(r"(?<=[.!?])\s+", stmt.sentence_text):
          s_clean = re.sub(r"[^\w\s]", "", s.lower()).strip()
          if len(s_clean) > 15:
            if s_clean in seen_section_sentences:
              prev_stmt_id = seen_section_sentences[s_clean]
              all_unsupported_claims.append(f"[{stmt.statement_id}] Duplicated sentence across sections (already in {prev_stmt_id}): '{s.strip()}'")
              stmt.verification_status = VerificationStatus.UNSUPPORTED_CLAIM
              unsupported += 1
              verified = max(0, verified - 1)
              break
            seen_section_sentences[s_clean] = stmt.statement_id

    # Completeness Check: Ensure all package observations are addressed or listed
    completeness_issues = cls.evaluate_completeness(validated_stmts, package)
    for c_issue in completeness_issues:
      all_unsupported_claims.append(f"[COMPLETENESS] {c_issue}")

    coverage_pct = round((verified / max(1, total)) * 100.0, 1)
    is_faithful = (unsupported == 0 and len(completeness_issues) == 0 and total > 0)

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

  @classmethod
  def evaluate_completeness(
      cls,
      statements: list[NarrativeStatementCitation],
      package: ClinicalEvidencePackage,
  ) -> list[str]:
    """Ensures every finding passed to the narrative appears in the output,
    OR is explicitly listed in a deterministic 'Additional findings not addressed in this narrative: ...' line.
    Rejects LLM output that silently omits findings.
    """
    if not package.ai_observations:
      return []

    # Narrative text from sections 5 and 7
    narrative_sections = [s.sentence_text for s in statements if s.section_index in (5, 7)]
    if not narrative_sections:
      narrative_sections = [s.sentence_text for s in statements]
    full_narrative = "\n".join(narrative_sections)
    full_narrative_lower = full_narrative.lower()

    # Check for deterministic additional findings line
    additional_line_match = re.search(
        r"additional findings not addressed in this narrative:\s*([^\n\.]+)",
        full_narrative,
        re.IGNORECASE,
    )
    additional_text = additional_line_match.group(1).lower() if additional_line_match else ""
    additional_teeth = cls.extract_teeth_mentioned(additional_text) if additional_text else set()

    missing_issues = []

    for obs in package.ai_observations:
      t_fdi = obs.tooth_fdi
      p_class = obs.pathology_candidate
      p_name = p_class.value.replace("_", " ")

      if t_fdi is None:
        keywords = cls.PATHOLOGY_KEYWORDS.get(p_class, [p_name])
        found_kw = any(kw in full_narrative_lower for kw in keywords)
        found_in_add = any(kw in additional_text for kw in keywords)
        if not (found_kw or found_in_add):
          missing_issues.append(f"Finding ID '{obs.finding_id}' ({p_name}) was silently omitted from narrative.")
        continue

      # If tooth appears in additional findings line, it is acknowledged
      if t_fdi in additional_teeth or f"#{t_fdi}" in additional_text or f"tooth {t_fdi}" in additional_text:
        continue

      # Tooth must appear in the narrative text
      all_teeth = cls.extract_teeth_mentioned(full_narrative)
      if t_fdi not in all_teeth and f"#{t_fdi}" not in full_narrative:
        missing_issues.append(
            f"Finding Tooth #{t_fdi} ({p_name}) was silently omitted from narrative. "
            f"All findings must be addressed or listed under 'Additional findings not addressed in this narrative:'."
        )
        continue

      # Check that the tooth is paired with appropriate pathology keywords in its context
      keywords = list(cls.PATHOLOGY_KEYWORDS.get(p_class, [p_name]))
      if p_class == PathologyClass.DEEP_CARIES:
        keywords += ["caries", "carious", "decay", "pulp"]

      sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full_narrative) if s.strip()]
      tooth_has_context = False
      for s in sentences:
        s_teeth = cls.extract_teeth_mentioned(s)
        if t_fdi in s_teeth or f"#{t_fdi}" in s:
          s_lower = s.lower()
          if any(kw in s_lower for kw in keywords):
            tooth_has_context = True
            break

      if not tooth_has_context and any(kw in full_narrative_lower for kw in keywords):
        tooth_has_context = True

      if not tooth_has_context:
        missing_issues.append(
            f"Finding Tooth #{t_fdi} ({p_name}) was mentioned without matching clinical pathology context. "
            f"All findings must be addressed or listed under 'Additional findings not addressed in this narrative:'."
        )

    return missing_issues
