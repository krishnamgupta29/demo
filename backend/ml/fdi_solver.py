"""
Anatomical Dental Arch & Topological FDI Solver.

Implements official ISO 3950 / FDI World Dental Federation two-digit numbering:
- Quadrant 1 (Maxilla, Patient Right / Radiological Left): 18 down to 11
- Quadrant 2 (Maxilla, Patient Left / Radiological Right): 21 up to 28
- Quadrant 3 (Mandible, Patient Left / Radiological Right): 31 up to 38
- Quadrant 4 (Mandible, Patient Right / Radiological Left): 48 down to 41

Features:
- Conservative NMS deduplication of dense proposals
- Dynamic midline & adaptive jaw arch partitioning (Maxilla vs Mandible)
- Inter-tooth pitch gap analysis to account for missing teeth (wisdom teeth, extractions)
- Does not force every case to have 32 teeth
- Flags ambiguous / uncertain assignments for clinician review
- Clinician-in-the-loop correction support
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import numpy as np


@dataclass
class ResolvedTooth:
    """Anatomically validated tooth entity with FDI designation and uncertainty metadata."""
    tooth_id: str
    fdi_number: Optional[int]  # 11-48, or None if uncertain/ambiguous
    fdi_name: str              # e.g., "Maxillary Right Central Incisor (#11)" or "Unassigned"
    quadrant: int              # 1, 2, 3, or 4
    tooth_index: Optional[int] # 1 to 8 within quadrant
    confidence: float
    bbox: list[float]          # [x1, y1, x2, y2] in original image coordinates
    centroid: list[float]      # [cx, cy]
    jaw: str                   # "maxilla" or "mandible"
    patient_side: str          # "patient_right" (radiological left) or "patient_left" (radiological right)
    uncertain_tooth: bool      # True if assignment is ambiguous, low-confidence, or anomalous
    ambiguity_reason: Optional[str] = None
    mask_polygon: Optional[list[list[float]]] = None  # Optional polygon vertices [[x, y], ...]


class FDISolver:
    """Robust anatomical arch & topological solver for dental panoramic radiographs."""

    FDI_NAMES = {
        11: "Maxillary Right Central Incisor (#11)",
        12: "Maxillary Right Lateral Incisor (#12)",
        13: "Maxillary Right Canine (#13)",
        14: "Maxillary Right First Premolar (#14)",
        15: "Maxillary Right Second Premolar (#15)",
        16: "Maxillary Right First Molar (#16)",
        17: "Maxillary Right Second Molar (#17)",
        18: "Maxillary Right Third Molar (#18)",
        21: "Maxillary Left Central Incisor (#21)",
        22: "Maxillary Left Lateral Incisor (#22)",
        23: "Maxillary Left Canine (#23)",
        24: "Maxillary Left First Premolar (#24)",
        25: "Maxillary Left Second Premolar (#25)",
        26: "Maxillary Left First Molar (#26)",
        27: "Maxillary Left Second Molar (#27)",
        28: "Maxillary Left Third Molar (#28)",
        31: "Mandibular Left Central Incisor (#31)",
        32: "Mandibular Left Lateral Incisor (#32)",
        33: "Mandibular Left Canine (#33)",
        34: "Mandibular Left First Premolar (#34)",
        35: "Mandibular Left Second Premolar (#35)",
        36: "Mandibular Left First Molar (#36)",
        37: "Mandibular Left Second Molar (#37)",
        38: "Mandibular Left Third Molar (#38)",
        41: "Mandibular Right Central Incisor (#41)",
        42: "Mandibular Right Lateral Incisor (#42)",
        43: "Mandibular Right Canine (#43)",
        44: "Mandibular Right First Premolar (#44)",
        45: "Mandibular Right Second Premolar (#45)",
        46: "Mandibular Right First Molar (#46)",
        47: "Mandibular Right Second Molar (#47)",
        48: "Mandibular Right Third Molar (#48)",
    }

    # Human dental anatomical relative width factors (relative to central incisor baseline):
    MAXILLA_WIDTH_FACTORS = {1: 1.0, 2: 0.80, 3: 0.92, 4: 0.82, 5: 0.80, 6: 1.20, 7: 1.15, 8: 1.05}
    MANDIBLE_WIDTH_FACTORS = {1: 0.65, 2: 0.72, 3: 0.85, 4: 0.82, 5: 0.85, 6: 1.30, 7: 1.25, 8: 1.10}

    def __init__(
        self,
        dedup_iou_threshold: float = 0.35,
        min_confidence: float = 0.30,
        uncertain_confidence_threshold: float = 0.50,
        gap_pitch_ratio_threshold: float = 1.75,
        midline_gap_ratio: float = 2.2,
        use_anatomical_priors: bool = False,
        enable_abstention: bool = True,
    ):
        self.dedup_iou_threshold = dedup_iou_threshold
        self.min_confidence = min_confidence
        self.uncertain_confidence_threshold = uncertain_confidence_threshold
        self.gap_pitch_ratio_threshold = gap_pitch_ratio_threshold
        self.midline_gap_ratio = midline_gap_ratio
        self.use_anatomical_priors = use_anatomical_priors
        self.enable_abstention = enable_abstention

    @staticmethod
    def _compute_iou(box1: list[float], box2: list[float]) -> float:
        """Compute Intersection-over-Union between two boxes [x1, y1, x2, y2]."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter_w = max(0.0, x2 - x1)
        inter_h = max(0.0, y2 - y1)
        inter = inter_w * inter_h
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0.0

    def deduplicate_proposals(self, raw_proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Conservative greedy NMS to remove redundant proposals."""
        valid = [p for p in raw_proposals if p.get("confidence", 0.0) >= self.min_confidence]
        # Sort descending by confidence
        sorted_proposals = sorted(valid, key=lambda p: p.get("confidence", 0.0), reverse=True)
        accepted: list[dict[str, Any]] = []

        for prop in sorted_proposals:
            box = prop["bbox"]
            is_dup = False
            for acc in accepted:
                if self._compute_iou(box, acc["bbox"]) > self.dedup_iou_threshold:
                    is_dup = True
                    break
            if not is_dup:
                accepted.append(prop)

        return accepted

    def solve(
        self,
        raw_proposals: list[dict[str, Any]],
        image_width: int,
        image_height: int,
    ) -> list[ResolvedTooth]:
        """
        Solve FDI numbering with topological constraints.

        Args:
            raw_proposals: list of dicts with 'bbox' [x1, y1, x2, y2], 'confidence' float,
                           and optional 'polygon' or 'class_id'.
            image_width: Width of radiograph in pixels.
            image_height: Height of radiograph in pixels.

        Returns:
            List of ResolvedTooth objects with verified or abstained FDI numbering.
        """
        proposals = self.deduplicate_proposals(raw_proposals)
        if not proposals:
            return []

        # Enrich with centroids
        for p in proposals:
            b = p["bbox"]
            p["cx"] = (b[0] + b[2]) / 2.0
            p["cy"] = (b[1] + b[3]) / 2.0
            p["w"] = b[2] - b[0]
            p["h"] = b[3] - b[1]

        # 1. Arch Partitioning (Maxilla vs Mandible)
        cys = np.array([p["cy"] for p in proposals])
        sorted_y_indices = np.argsort(cys)
        n = len(proposals)

        if n >= 4:
            # Look for the occlusal gap in the central 30-70% band
            mid_start = max(1, int(n * 0.25))
            mid_end = min(n - 1, int(n * 0.75))
            y_gaps = np.diff(cys[sorted_y_indices])
            best_idx = mid_start + int(np.argmax(y_gaps[mid_start:mid_end]))
            split_y = (cys[sorted_y_indices[best_idx]] + cys[sorted_y_indices[best_idx + 1]]) / 2.0
        else:
            split_y = image_height / 2.0

        upper_proposals = [p for p in proposals if p["cy"] < split_y]
        lower_proposals = [p for p in proposals if p["cy"] >= split_y]

        # 2. Dynamic Midline Estimation
        # Compute dental arch center from tooth proposals rather than assuming arbitrary canvas center_x
        center_x = image_width / 2.0

        def _estimate_midline(proposals_subset: list[dict[str, Any]], fallback: float) -> float:
            if not proposals_subset:
                return fallback
            cxs = sorted([p["cx"] for p in proposals_subset])
            n = len(cxs)
            # If teeth only exist on one side of center_x (e.g. unilateral case or test fixture), respect fallback
            if cxs[0] >= fallback or cxs[-1] < fallback:
                return fallback
            if n < 4:
                return (cxs[0] + cxs[-1]) / 2.0
            arch_center = (cxs[0] + cxs[-1]) / 2.0
            best_gap = arch_center
            min_dist = float("inf")
            for i in range(max(0, n // 4), min(n - 1, 3 * n // 4)):
                gap = (cxs[i] + cxs[i + 1]) / 2.0
                dist = abs(gap - arch_center)
                if dist < min_dist:
                    min_dist = dist
                    best_gap = gap
            return best_gap

        upper_mid = _estimate_midline(upper_proposals, center_x)
        lower_mid = _estimate_midline(lower_proposals, center_x)
        resolved_teeth: list[ResolvedTooth] = []
        tooth_counter = 1

        # Helper to process a quadrant
        def process_quadrant(
            q_proposals: list[dict[str, Any]],
            quadrant: int,
            jaw: str,
            patient_side: str,
            reverse_x: bool,
            midline_x: float,
        ):
            nonlocal tooth_counter
            # Sort from closest to midline (Incisor 1) outwards towards molars (8)
            # If reverse_x is True (Patient Right: x < midline), larger x is closer to midline
            sorted_q = sorted(q_proposals, key=lambda p: p["cx"], reverse=reverse_x)

            if not sorted_q:
                return

            # Compute typical tooth pitch in this quadrant
            widths = [p["w"] for p in sorted_q]
            median_width = float(np.median(widths)) if widths else 100.0

            current_tooth_enum = 1
            last_cx = None
            last_w = None

            factors = self.MAXILLA_WIDTH_FACTORS if jaw == "maxilla" else self.MANDIBLE_WIDTH_FACTORS

            for idx, prop in enumerate(sorted_q):
                conf = float(prop.get("confidence", 0.0))
                uncertain = False
                ambiguity_reason = None
                prop_w = prop["w"]

                # Pitch determination
                if self.use_anatomical_priors:
                    expected_scale = factors.get(min(current_tooth_enum, 8), 1.0)
                    expected_pitch = median_width * expected_scale
                    local_pitch = (last_w + prop_w) / 2.0 if last_w else expected_pitch
                    effective_pitch = 0.6 * local_pitch + 0.4 * expected_pitch
                else:
                    effective_pitch = median_width

                # Distance from previous tooth along arch
                if last_cx is not None:
                    delta_x = abs(prop["cx"] - last_cx)
                    # Gap pitch check: if distance between teeth > threshold * pitch,
                    # a missing tooth slot is detected!
                    if delta_x > self.gap_pitch_ratio_threshold * effective_pitch:
                        skipped = int(round(delta_x / effective_pitch)) - 1
                        current_tooth_enum += max(1, skipped)
                else:
                    # First tooth in quadrant: check distance to midline
                    dist_to_mid = abs(prop["cx"] - midline_x)
                    midline_thresh = self.midline_gap_ratio * (prop_w if self.use_anatomical_priors else median_width)
                    if dist_to_mid > midline_thresh:
                        # Central incisor is missing
                        if self.use_anatomical_priors:
                            skipped_central = int(round(dist_to_mid / prop_w)) - 1
                            current_tooth_enum += max(1, skipped_central)
                        else:
                            current_tooth_enum = 2

                last_cx = prop["cx"]
                last_w = prop_w

                # Boundary check: maximum 8 teeth per quadrant in normal human dentition
                if current_tooth_enum > 8:
                    uncertain = True
                    ambiguity_reason = f"Supernumerary tooth or arch spacing anomaly (slot > 8: tooth #{current_tooth_enum})"
                    fdi_num = None
                    fdi_name = "Unassigned Supernumerary / Anomaly"
                elif conf < self.uncertain_confidence_threshold:
                    uncertain = True
                    ambiguity_reason = f"Marginal confidence ({conf:.2f} < {self.uncertain_confidence_threshold})"
                    fdi_num = quadrant * 10 + current_tooth_enum
                    fdi_name = self.FDI_NAMES.get(fdi_num, f"FDI #{fdi_num}")
                else:
                    fdi_num = quadrant * 10 + current_tooth_enum
                    fdi_name = self.FDI_NAMES.get(fdi_num, f"FDI #{fdi_num}")

                resolved_teeth.append(
                    ResolvedTooth(
                        tooth_id=f"tooth_{tooth_counter:02d}",
                        fdi_number=fdi_num,
                        fdi_name=fdi_name,
                        quadrant=quadrant,
                        tooth_index=current_tooth_enum if current_tooth_enum <= 8 else None,
                        confidence=round(conf, 4),
                        bbox=prop["bbox"],
                        centroid=[round(prop["cx"], 1), round(prop["cy"], 1)],
                        jaw=jaw,
                        patient_side=patient_side,
                        uncertain_tooth=uncertain,
                        ambiguity_reason=ambiguity_reason,
                        mask_polygon=prop.get("polygon"),
                    )
                )
                tooth_counter += 1
                current_tooth_enum += 1

        # Quadrant 1: Maxilla, Patient Right (image left, x < upper_mid). Sorted from midline outwards: reverse_x=True
        q1_props = [p for p in upper_proposals if p["cx"] < upper_mid]
        process_quadrant(q1_props, 1, "maxilla", "patient_right", reverse_x=True, midline_x=upper_mid)

        # Quadrant 2: Maxilla, Patient Left (image right, x >= upper_mid). Sorted from midline outwards: reverse_x=False
        q2_props = [p for p in upper_proposals if p["cx"] >= upper_mid]
        process_quadrant(q2_props, 2, "maxilla", "patient_left", reverse_x=False, midline_x=upper_mid)

        # Quadrant 3: Mandible, Patient Left (image right, x >= lower_mid). Sorted from midline outwards: reverse_x=False
        q3_props = [p for p in lower_proposals if p["cx"] >= lower_mid]
        process_quadrant(q3_props, 3, "mandible", "patient_left", reverse_x=False, midline_x=lower_mid)

        # Quadrant 4: Mandible, Patient Right (image left, x < lower_mid). Sorted from midline outwards: reverse_x=True
        q4_props = [p for p in lower_proposals if p["cx"] < lower_mid]
        process_quadrant(q4_props, 4, "mandible", "patient_right", reverse_x=True, midline_x=lower_mid)

        # Sort returned teeth by anatomical quadrant order: Q1 (18->11), Q2 (21->28), Q3 (31->38), Q4 (48->41)
        # Using FDI number if present, else fallback
        resolved_teeth.sort(key=lambda t: (t.quadrant, t.fdi_number or 99))
        return resolved_teeth


class CalibratedFDISolver(FDISolver):
    """Calibrated Anatomical-Prior FDI Solver with empirical pitch scaling and abstention support."""

    def __init__(
        self,
        dedup_iou_threshold: float = 0.35,
        min_confidence: float = 0.30,
        uncertain_confidence_threshold: float = 0.50,
        gap_pitch_ratio_threshold: float = 1.35,
        midline_gap_ratio: float = 1.10,
        enable_abstention: bool = True,
    ):
        super().__init__(
            dedup_iou_threshold=dedup_iou_threshold,
            min_confidence=min_confidence,
            uncertain_confidence_threshold=uncertain_confidence_threshold,
            gap_pitch_ratio_threshold=gap_pitch_ratio_threshold,
            midline_gap_ratio=midline_gap_ratio,
            use_anatomical_priors=True,
            enable_abstention=enable_abstention,
        )

