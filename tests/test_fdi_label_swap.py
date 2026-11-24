"""Unit tests for horizontal-flip FDI label swapping."""

import pytest
from backend.schemas.tooth import (
    VALID_FDI_TEETH,
    FDI_HORIZONTAL_FLIP_MAP,
    swap_fdi_horizontal_flip,
)


def test_maxilla_fdi_horizontal_flip_pairs():
    """Verifies that all maxillary teeth (Q1 <-> Q2) correctly swap across midline (11<->21 ... 18<->28)."""
    expected_pairs = [
        (11, 21),
        (12, 22),
        (13, 23),
        (14, 24),
        (15, 25),
        (16, 26),
        (17, 27),
        (18, 28),
    ]
    for q1_tooth, q2_tooth in expected_pairs:
        assert swap_fdi_horizontal_flip(q1_tooth) == q2_tooth
        assert swap_fdi_horizontal_flip(q2_tooth) == q1_tooth


def test_mandible_fdi_horizontal_flip_pairs():
    """Verifies that all mandibular teeth (Q4 <-> Q3) correctly swap across midline (41<->31 ... 48<->38)."""
    expected_pairs = [
        (41, 31),
        (42, 32),
        (43, 33),
        (44, 34),
        (45, 35),
        (46, 36),
        (47, 37),
        (48, 38),
    ]
    for q4_tooth, q3_tooth in expected_pairs:
        assert swap_fdi_horizontal_flip(q4_tooth) == q3_tooth
        assert swap_fdi_horizontal_flip(q3_tooth) == q4_tooth


def test_fdi_horizontal_flip_involution_property():
    """Verifies the mathematical involution property: swap(swap(x)) == x for all 32 valid permanent teeth."""
    assert len(VALID_FDI_TEETH) == 32
    assert len(FDI_HORIZONTAL_FLIP_MAP) == 32
    for tooth in VALID_FDI_TEETH:
        swapped = swap_fdi_horizontal_flip(tooth)
        assert swapped is not None
        assert swapped in VALID_FDI_TEETH
        assert swap_fdi_horizontal_flip(swapped) == tooth
        # Position (last digit) must remain invariant under lateral flip
        assert tooth % 10 == swapped % 10
        # Quadrant must switch across midline (1 <-> 2, 4 <-> 3)
        assert (tooth // 10, swapped // 10) in {(1, 2), (2, 1), (3, 4), (4, 3)}


def test_fdi_horizontal_flip_none_and_unknown():
    """Handles None and out-of-bounds identifiers gracefully without raising exceptions."""
    assert swap_fdi_horizontal_flip(None) is None
    assert swap_fdi_horizontal_flip(99) == 99
    assert swap_fdi_horizontal_flip(-1) == -1
