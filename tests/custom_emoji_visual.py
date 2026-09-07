"""Pixel oracle for the authored transparent custom-emoji animation."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from typing import cast

from PIL import Image

STATES = (
    ((10, 35), (240, 48, 72)),
    ((28, 55), (48, 190, 240)),
    ((46, 35), (248, 184, 40)),
    ((64, 55), (112, 72, 232)),
)


def _close(actual: tuple[int, ...], expected: tuple[int, int, int], tolerance: int) -> bool:
    return all(abs(actual[index] - expected[index]) <= tolerance for index in range(3))


def animation_states(
    frames: Sequence[Image.Image],
    boxes: Sequence[tuple[int, int, int, int]],
    *,
    tolerance: int = 55,
) -> list[int]:
    """Return distinct cyclic authored states observed inside semantic carrier boxes."""
    if len(frames) != len(boxes) or not frames:
        raise ValueError("Animation frames require matching semantic boxes")
    observed: list[int] = []
    for frame, box in zip(frames, boxes, strict=True):
        left, top, right, bottom = box
        if not (0 <= left < right <= frame.width and 0 <= top < bottom <= frame.height):
            raise ValueError("Animation carrier box is outside its screenshot")
        sample = frame.convert("RGB").crop(box).resize((100, 100), Image.Resampling.BILINEAR)
        marker = cast(tuple[int, ...], sample.getpixel((15, 15)))
        if not _close(marker, (32, 220, 96), tolerance):
            continue
        matches = [
            index
            for index, ((x, y), color) in enumerate(STATES)
            if _close(cast(tuple[int, ...], sample.getpixel((x + 12, y + 12))), color, tolerance)
        ]
        if len(matches) == 1 and (not observed or observed[-1] != matches[0]):
            observed.append(matches[0])
    return observed


def require_complete_cycle(states: Sequence[int]) -> None:
    """Require all four states in cyclic order, allowing duplicates and skipped captures."""
    if set(states) != {0, 1, 2, 3}:
        raise AssertionError("Animation burst did not contain all four authored states")
    for left, right in pairwise(states):
        if (right - left) % 4 not in (1, 2, 3):
            raise AssertionError("Animation states are not cyclic")
