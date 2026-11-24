"""Clinical Attributes Engine for DENTRACE.

Implements authoritative, deterministic clinical rules for:
1. Impaction angulation via PCA on polygon masks relative to horizontal plane.
2. Deep caries radiographic wording requiring vitality testing before claiming pulp involvement.
3. Periodontal bone loss blocker ("not supported in this version (no landmark data)").
4. Composite endodontic failure evaluation (RCT + periapical radiolucency on same tooth).
"""

from typing import Optional, Sequence, Any
import numpy as np
from ..schemas.finding import PathologyClass

class ClinicalAttributeEngine:
    """Deterministic extractor and validator of secondary clinical attributes."""

    @staticmethod
    def classify_impaction_angulation(
        polygon_pts: Optional[Sequence[Sequence[float]]],
        tooth_fdi: Optional[int] = None,
    ) -> str:
        """Computes impaction angulation from polygon mask using PCA against horizontal plane.

        Returns:
            Formatted clinical string:
            - If no mask/insufficient points: 'angulation not determinable (no mask)'
            - Else: '{vertical|mesioangular|distoangular|horizontal} (suspected, requires clinician confirmation)'
        """
        if not polygon_pts or len(polygon_pts) < 3:
            return "angulation not determinable (no mask)"

        pts = np.array(polygon_pts, dtype=np.float64)
        if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] != 2:
            return "angulation not determinable (no mask)"

        # Principal Component Analysis
        mean = np.mean(pts, axis=0)
        centered = pts - mean
        cov = np.cov(centered, rowvar=False)

        try:
            evals, evecs = np.linalg.eigh(cov)
        except Exception:
            return "angulation not determinable (no mask)"

        # Major principal axis
        major_axis = evecs[:, np.argmax(evals)]  # [dx, dy]
        vx = abs(float(major_axis[0]))
        vy = abs(float(major_axis[1]))

        # Angle with horizontal in degrees: 0 deg = horizontal, 90 deg = vertical
        angle_deg = np.degrees(np.arctan2(vy, vx))

        if angle_deg >= 70.0:
            classification = "vertical"
        elif angle_deg <= 20.0:
            classification = "horizontal"
        else:
            # Between 20 and 70 degrees: mesioangular vs distoangular
            # For panoramic OPGs, tooth anatomy places occlusal crown at top (mandible) or bottom (maxilla)
            # Check orientation of the principal vector relative to midline (midline ~ x = 1436 px in 2872 px width)
            quad = (tooth_fdi // 10) if tooth_fdi else 3
            # In mandibular quadrants (3 and 4, FDI 38/48):
            # Midline is between quad 3 (patient left) and quad 4 (patient right).
            # Quad 4 (patient right, image left x < 1436): mesial is toward midline (increasing x).
            # Quad 3 (patient left, image right x > 1436): mesial is toward midline (decreasing x).
            # For PCA slope sign:
            slope = float(major_axis[1]) / (float(major_axis[0]) + 1e-9)
            if quad in (4, 1):  # Patient right
                classification = "mesioangular" if slope < 0 else "distoangular"
            else:  # Patient left (quad 2, 3)
                classification = "mesioangular" if slope > 0 else "distoangular"

        return f"{classification} (suspected, requires clinician confirmation)"

    @staticmethod
    def format_caries_wording(
        pathology_class: PathologyClass,
        clinical_examinations: Optional[Sequence[Any]] = None,
        tooth_fdi: Optional[int] = None,
    ) -> str:
        """Enforces strictly hedged clinical wording for deep caries.

        Rule: Never say pulp is involved unless the dentist explicitly recorded pulp vitality.
        """
        if pathology_class != PathologyClass.DEEP_CARIES:
            return pathology_class.value

        has_pulp_vitality_tested = False
        if clinical_examinations and tooth_fdi is not None:
            for ex in clinical_examinations:
                if getattr(ex, "tooth_fdi", None) == tooth_fdi and getattr(ex, "pulp_vitality", None):
                    has_pulp_vitality_tested = True
                    break

        if has_pulp_vitality_tested:
            return "deep caries, with pulp involvement confirmed by clinician vitality testing"
        return "deep caries, radiographically approaching the pulp (suspected)"

    @staticmethod
    def format_bone_loss_wording(
        clinical_examinations: Optional[Sequence[Any]] = None,
        tooth_fdi: Optional[int] = None,
    ) -> str:
        """Blocks alveolar bone resorption text unless probing depth is explicitly recorded by a clinician."""
        has_probing_depth = False
        probing_mm = None
        if clinical_examinations:
            for ex in clinical_examinations:
                if tooth_fdi is None or getattr(ex, "tooth_fdi", None) == tooth_fdi:
                    pd = getattr(ex, "probing_depth_mm", None)
                    if pd is not None and pd > 0:
                        has_probing_depth = True
                        probing_mm = pd
                        break

        if has_probing_depth:
            return f"periodontal pocketing recorded ({probing_mm} mm) — requires clinical attachment level correlation"
        return "not supported in this version (no landmark data)"

    @staticmethod
    def evaluate_endodontic_failure(
        observations: Sequence[Any],
        tooth_fdi: Optional[int],
    ) -> tuple[bool, Optional[str]]:
        """Composite clinical rule: Root Canal Treatment + Periapical Lesion on same tooth.

        Returns:
            (is_flagged, alert_text)
        """
        if tooth_fdi is None:
            return False, None

        tooth_obs = [o for o in observations if getattr(o, "tooth_fdi", None) == tooth_fdi]
        has_rct = any(
            getattr(o, "pathology_candidate", None) == PathologyClass.ROOT_CANAL_TREATMENT
            or getattr(o, "pathology_class", None) == PathologyClass.ROOT_CANAL_TREATMENT
            for o in tooth_obs
        )
        has_lesion = any(
            getattr(o, "pathology_candidate", None) == PathologyClass.PERIAPICAL_LESION
            or getattr(o, "pathology_class", None) == PathologyClass.PERIAPICAL_LESION
            for o in tooth_obs
        )

        if has_rct and has_lesion:
            msg = (
                "Suspected persistent or recurrent periapical radiolucency on endodontically treated tooth "
                "— requires clinician review."
            )
            return True, msg
        return False, None
