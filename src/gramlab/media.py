"""Validated immutable local image values shared by World and HTTP projections."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image

MAX_IMAGE_BYTES = 10_000_000


@dataclass(frozen=True)
class ImageAsset:
    data: bytes
    mime_type: str
    extension: str
    width: int
    height: int
    sha256: str


def validate_image(data: bytes) -> ImageAsset:
    if not isinstance(data, bytes) or not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Photo must contain 1 to 10000000 bytes")
    try:
        with Image.open(io.BytesIO(data), formats=("PNG", "JPEG")) as opened:
            if opened.format not in ("PNG", "JPEG"):
                raise ValueError("GRAMLAB_UNSUPPORTED: photo format")
            width, height = opened.size
            frames = getattr(opened, "n_frames", 1)
            if (
                width <= 0
                or height <= 0
                or width + height > 10_000
                or max(width, height) > 20 * min(width, height)
                or width * height > 25_000_000
            ):
                raise ValueError("Photo dimensions exceed the offline profile")
            if frames != 1:
                raise ValueError("GRAMLAB_UNSUPPORTED: multi-frame photo")
            opened.verify()
        with Image.open(io.BytesIO(data), formats=("PNG", "JPEG")) as decoded:
            decoded.load()
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("Invalid or truncated photo") from error
    mime, extension = ("image/png", "png") if opened.format == "PNG" else ("image/jpeg", "jpg")
    return ImageAsset(data, mime, extension, width, height, hashlib.sha256(data).hexdigest())
