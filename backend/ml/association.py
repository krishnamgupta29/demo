"""
Tooth-Pathology Association Engine.

Associates detected dental anomalies (caries, periapical lesions, impactions, restorations)
with localized anatomical teeth (FDI 11-48).

Evaluates:
- Intersection over Pathology (IoP): fraction of lesion contained inside tooth boundary
- Symmetric IoU: for whole-tooth instance matching
- Centroid containment: checks if pathology center lies inside tooth polygon or box
- Interproximal contact resolution: handles lesions between adjacent teeth
- Multi-pathology support: allows multiple findings per tooth
- Unassociated finding handling: preserves anomalies not attributable to a specific tooth
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import numpy as np

from backend.ml.fdi_solver import ResolvedTooth


@dataclass
class FindingAssociation:
    """Association result for a single pathology finding."""
    finding_id: str
    label: str
    confidence: float
    bbox: list[float]
    associated_tooth_id: Optional[str]
    associated_fdi_number: Optional[int]
    association_method: str  # "mask_overlap", "iop_intersection", "centroid_containment", "unassociated"
    iop: float  # Intersection over Pathology
    iou: float  # Symmetric IoU
    is_interproximal: bool = False
    secondary_fdi_number: Optional[int] = None
    uncertain_association: bool = False
    notes: Optional[str] = None


@dataclass
class ToothWithFindings:
    """Consolidated tooth entity containing all associated pathologies."""
    tooth: ResolvedTooth
    findings: list[FindingAssociation] = field(default_factory=list)

    @property
    def fdi_number(self) -> Optional[int]:
        return self.tooth.fdi_number

    @property
    def is_sound(self) -> bool:
        """True if no pathologies are associated with this tooth."""
        return len(self.findings) == 0


class ToothPathologyAssociator:
    """Geometry-based association engine with adaptive medical thresholds."""

    def __init__(
        self,
        min_iop_threshold: float = 0.25,
        strong_iop_threshold: float = 0.50,
        interproximal_diff_threshold: float = 0.15,
    ):
        self.min_iop_threshold = min_iop_threshold
        self.strong_iop_threshold = strong_iop_threshold
        self.interproximal_diff_threshold = interproximal_diff_threshold

    @staticmethod
    def _box_intersection_and_areas(b1: list[float], b2: list[float]) -> tuple[float, float, float]:
        """Returns (intersection_area, area1, area2) for boxes [x1, y1, x2, y2]."""
        x1 = max(b1[0], b2[0])
        y1 = max(b1[1], b2[1])
        x2 = min(b1[2], b2[2])
        y2 = min(b1[3], b2[3])
        w = max(0.0, x2 - x1)
        h = max(0.0, y2 - y1)
        inter = w * h
        a1 = max(0.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
        a2 = max(0.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))
        return inter, a1, a2

    @staticmethod
    def _is_centroid_inside(cx: float, cy: float, box: list[float]) -> bool:
        return box[0] <= cx <= box[2] and box[1] <= cy <= box[3]

    def associate(
        self,
        findings: list[dict[str, Any]],
        teeth: list[ResolvedTooth],
    ) -> tuple[list[ToothWithFindings], list[FindingAssociation]]:
        """
        Associate findings to teeth using geometric containment and overlap.

        Args:
            findings: list of dicts with 'id', 'label', 'confidence', 'bbox' [x1, y1, x2, y2],
                      and optional 'polygon'.
            teeth: list of ResolvedTooth objects from FDISolver.

        Returns:
            Tuple of (list of ToothWithFindings for all teeth, list of all FindingAssociation).
        """
        teeth_map = {t.tooth_id: ToothWithFindings(tooth=t) for t in teeth}
        all_associations: list[FindingAssociation] = []

        for finding in findings:
            f_id = finding.get("id", f"f_{len(all_associations)+1}")
            label = finding.get("label", "Unknown")
            conf = float(finding.get("confidence", 0.0))
            f_box = finding["bbox"]
            f_cx = (f_box[0] + f_box[2]) / 2.0
            f_cy = (f_box[1] + f_box[3]) / 2.0

            candidates: list[dict[str, Any]] = []

            for tooth in teeth:
                t_box = tooth.bbox
                inter, a_find, a_tooth = self._box_intersection_and_areas(f_box, t_box)
                if a_find <= 0:
                    continue

                iop = inter / a_find
                union = a_find + a_tooth - inter
                iou = inter / union if union > 0 else 0.0
                centroid_inside = self._is_centroid_inside(f_cx, f_cy, t_box)

                if iop > 0.05 or centroid_inside:
                    candidates.append({
                        "tooth": tooth,
                        "iop": iop,
                        "iou": iou,
                        "centroid_inside": centroid_inside,
                    })

            # Sort candidates by IoP descending
            candidates.sort(key=lambda c: c["iop"], reverse=True)

            if not candidates:
                # If finding is an impacted tooth without segmented tooth overlap (e.g. unerupted in bone/ramus)
                if (label == "impacted_tooth" or "impact" in label.lower()) and teeth:
                    arch_cxs = [t.centroid[0] for t in teeth]
                    arch_cys = [t.centroid[1] for t in teeth]
                    mid_x = float(np.median(arch_cxs))
                    mid_y = float(np.median(arch_cys))
                    if f_cx < mid_x and f_cy < mid_y:
                        imp_fdi = 18; q = 1
                    elif f_cx >= mid_x and f_cy < mid_y:
                        imp_fdi = 28; q = 2
                    elif f_cx >= mid_x and f_cy >= mid_y:
                        imp_fdi = 38; q = 3
                    else:
                        imp_fdi = 48; q = 4
                    assoc = FindingAssociation(
                        finding_id=f_id,
                        label=label,
                        confidence=conf,
                        bbox=f_box,
                        associated_tooth_id=f"impacted_q{q}_m3",
                        associated_fdi_number=imp_fdi,
                        association_method="spatial_quadrant_prior",
                        iop=0.0,
                        iou=0.0,
                        uncertain_association=False,
                        notes=f"Impacted third molar (#{imp_fdi}) localized via anatomical spatial prior in quadrant {q}.",
                    )
                    all_associations.append(assoc)
                    continue

                # No overlap with any tooth: unassociated finding
                assoc = FindingAssociation(
                    finding_id=f_id,
                    label=label,
                    confidence=conf,
                    bbox=f_box,
                    associated_tooth_id=None,
                    associated_fdi_number=None,
                    association_method="unassociated",
                    iop=0.0,
                    iou=0.0,
                    uncertain_association=True,
                    notes="No anatomical tooth overlap detected. Likely bony/soft tissue anomaly or unsegmented tooth.",
                )
                all_associations.append(assoc)
                continue

            best = candidates[0]
            best_tooth: ResolvedTooth = best["tooth"]
            best_iop: float = best["iop"]
            best_iou: float = best["iou"]
            best_centroid: bool = best["centroid_inside"]

            # If finding is an impacted tooth or terminal distal molar, resolve to 3rd molar
            assoc_fdi = best_tooth.fdi_number
            if (label == "impacted_tooth" or "impact" in label.lower()) and best_tooth.quadrant:
                if assoc_fdi in (17, 27, 37, 47) or assoc_fdi is None or best_tooth.tooth_index in (7, 8, None):
                    assoc_fdi = best_tooth.quadrant * 10 + 8
                    note = f"Impacted third molar designation (#{assoc_fdi}) via quadrant {best_tooth.quadrant} molar region."
                    uncertain = False
            elif assoc_fdi is None and best_tooth.quadrant:
                assoc_fdi = best_tooth.quadrant * 10 + 8

            # Check if secondary tooth has near-equal overlap (interproximal contact)
            is_interproximal = False
            secondary_fdi = None
            if len(candidates) > 1:
                second = candidates[1]
                if second["iop"] >= self.min_iop_threshold and (best_iop - second["iop"]) < self.interproximal_diff_threshold:
                    is_interproximal = True
                    secondary_fdi = second["tooth"].fdi_number

            # Determine whether association is confident or uncertain
            if best_iop >= self.strong_iop_threshold:
                method = "iop_intersection"
                uncertain = False
                note = f"Confident association ({best_iop*100:.1f}% lesion containment)."
            elif best_centroid and best_iop >= self.min_iop_threshold:
                method = "centroid_containment"
                uncertain = False
                note = f"Centroid containment with {best_iop*100:.1f}% lesion containment."
            elif best_iop >= self.min_iop_threshold:
                method = "iop_intersection"
                uncertain = True
                note = f"Borderline overlap ({best_iop*100:.1f}% containment)."
            else:
                # If finding is an impacted tooth at quadrant margin, resolve via quadrant prior
                if (label == "impacted_tooth" or "impact" in label.lower()) and best_tooth.quadrant:
                    assoc_fdi = best_tooth.quadrant * 10 + 8
                    method = "spatial_quadrant_prior"
                    uncertain = False
                    note = f"Impacted third molar (#{assoc_fdi}) localized in quadrant {best_tooth.quadrant} molar region."
                else:
                    # Overlap is below threshold
                    assoc = FindingAssociation(
                        finding_id=f_id,
                        label=label,
                        confidence=conf,
                        bbox=f_box,
                        associated_tooth_id=None,
                        associated_fdi_number=None,
                        association_method="unassociated",
                        iop=best_iop,
                        iou=best_iou,
                        uncertain_association=True,
                        notes=f"Insufficient tooth overlap (max IoP {best_iop*100:.1f}% < threshold {self.min_iop_threshold*100:.0f}%).",
                    )
                    all_associations.append(assoc)
                    continue

            # Ensure impacted tooth receives anatomical third molar designation
            if (label == "impacted_tooth" or "impact" in label.lower()) and assoc_fdi is None and best_tooth.quadrant:
                assoc_fdi = best_tooth.quadrant * 10 + 8

            assoc = FindingAssociation(
                finding_id=f_id,
                label=label,
                confidence=conf,
                bbox=f_box,
                associated_tooth_id=best_tooth.tooth_id,
                associated_fdi_number=assoc_fdi,
                association_method=method,
                iop=round(best_iop, 4),
                iou=round(best_iou, 4),
                is_interproximal=is_interproximal,
                secondary_fdi_number=secondary_fdi,
                uncertain_association=uncertain,
                notes=note,
            )
            all_associations.append(assoc)
            teeth_map[best_tooth.tooth_id].findings.append(assoc)

        return list(teeth_map.values()), all_associations
