"""Safe, aspect-ratio preserving image preprocessing and coordinate transformation for ONNX inference."""

from dataclasses import dataclass
from typing import Sequence
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class LetterboxMetadata:
    """Metadata required to reverse letterbox coordinate scaling back to the original image space."""

    original_width: int
    original_height: int
    target_size: int
    scale: float
    pad_x: int
    pad_y: int
    new_width: int
    new_height: int


class ImagePreprocessor:
    """Handles medical radiograph letterboxing, normalization, and coordinate inversion."""

    @staticmethod
    def letterbox(
        image: Image.Image,
        target_size: int = 640,
        fill_color: tuple[int, int, int] = (114, 114, 114),
    ) -> tuple[np.ndarray, LetterboxMetadata]:
        """Preserve aspect ratio by scaling image to fit inside target_size x target_size and padding.

        Returns:
            tensor: Normalized float32 ndarray of shape (1, 3, target_size, target_size) in [0.0, 1.0].
            metadata: LetterboxMetadata used for reverse coordinate transformation.
        """
        if image.width <= 0 or image.height <= 0:
            raise ValueError(f"Invalid image dimensions: {image.width}x{image.height}")

        orig_w, orig_h = image.size
        rgb_image = image.convert("RGB")

        scale = min(target_size / orig_w, target_size / orig_h)
        nw = max(1, int(round(orig_w * scale)))
        nh = max(1, int(round(orig_h * scale)))

        pad_x = (target_size - nw) // 2
        pad_y = (target_size - nh) // 2

        # Bilinear interpolation for smooth high-frequency radiograph edge preservation
        resized = rgb_image.resize((nw, nh), Image.Resampling.BILINEAR)

        letterboxed = Image.new("RGB", (target_size, target_size), fill_color)
        letterboxed.paste(resized, (pad_x, pad_y))

        arr = np.array(letterboxed, dtype=np.float32) / 255.0
        # Transpose HWC -> CHW and add batch dimension (1, 3, H, W)
        tensor = np.expand_dims(np.transpose(arr, (2, 0, 1)), axis=0)

        meta = LetterboxMetadata(
            original_width=orig_w,
            original_height=orig_h,
            target_size=target_size,
            scale=scale,
            pad_x=pad_x,
            pad_y=pad_y,
            new_width=nw,
            new_height=nh,
        )
        return tensor, meta

    @staticmethod
    def unletterbox_box(
        box_xyxy: Sequence[float],
        meta: LetterboxMetadata,
    ) -> list[float]:
        """Convert [x1, y1, x2, y2] from target_size pixel space back to original image coordinates."""
        x1, y1, x2, y2 = box_xyxy
        ox1 = (x1 - meta.pad_x) / meta.scale
        oy1 = (y1 - meta.pad_y) / meta.scale
        ox2 = (x2 - meta.pad_x) / meta.scale
        oy2 = (y2 - meta.pad_y) / meta.scale

        # Clamp to valid image bounds
        ox1 = max(0.0, min(float(meta.original_width), float(ox1)))
        oy1 = max(0.0, min(float(meta.original_height), float(oy1)))
        ox2 = max(0.0, min(float(meta.original_width), float(ox2)))
        oy2 = max(0.0, min(float(meta.original_height), float(oy2)))

        return [round(ox1, 2), round(oy1, 2), round(ox2, 2), round(oy2, 2)]

    @staticmethod
    def unletterbox_polygon(
        points: Sequence[Sequence[float]],
        meta: LetterboxMetadata,
    ) -> list[list[float]]:
        """Convert a list of [x, y] polygon vertices back to original image space."""
        unscaled = []
        for pt in points:
            x, y = pt[0], pt[1]
            ox = max(0.0, min(float(meta.original_width), float((x - meta.pad_x) / meta.scale)))
            oy = max(0.0, min(float(meta.original_height), float((y - meta.pad_y) / meta.scale)))
            unscaled.append([round(ox, 2), round(oy, 2)])
        return unscaled
