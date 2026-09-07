"""Pixel oracle for translated/scaled authored custom-emoji frames."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from PIL import Image

MARKER = (32, 220, 96)
BLUE = (88, 104, 240)
STATES = (
    ((10, 35), (240, 48, 72)),
    ((28, 55), (48, 190, 240)),
    ((46, 35), (248, 184, 40)),
    ((64, 55), (112, 72, 232)),
)


@dataclass(frozen=True)
class LocatedFrame:
    state: int
    origin_x: float
    origin_y: float
    scale: float


def _close(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance: int) -> bool:
    return all(abs(actual[i] - expected[i]) <= tolerance for i in range(3))


def _matching(
    image: Image.Image, box: tuple[int, int, int, int], color: tuple[int, int, int], tolerance: int
) -> list[tuple[int, int]]:
    pixels = image.convert("RGB").load()
    if pixels is None:
        raise ValueError("Screenshot has no pixel access")
    left, top, right, bottom = box
    return [
        (x, y)
        for y in range(top, bottom)
        for x in range(left, right)
        if _close(cast(tuple[int, int, int], pixels[x, y]), color, tolerance)
    ]


def _bounds(points: Sequence[tuple[int, int]]) -> tuple[int, int, int, int]:
    return (
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points) + 1,
        max(y for _, y in points) + 1,
    )


def locate_static(frame: Image.Image, box: tuple[int, int, int, int]) -> bool:
    """Recognize the authored blue thumbnail diamond within a semantic region."""
    points = _matching(frame, box, BLUE, 38)
    if len(points) < 4:
        return False
    left, top, right, bottom = _bounds(points)
    width, height = right - left, bottom - top
    occupancy = len(points) / (width * height)
    rows = [sorted(x for x, y_value in points if y_value == y) for y in range(top, bottom)]
    widths = [len(row) for row in rows]
    contiguous = all(not row or row[-1] - row[0] + 1 <= len(row) + 2 for row in rows)
    center = (left + width // 2, top + height // 2) in set(points)
    corners = {(left, top), (right - 1, top), (left, bottom - 1), (right - 1, bottom - 1)}
    return (
        abs(width - height) <= max(2, width // 3)
        and 0.28 <= occupancy <= 0.78
        and center
        and not corners.intersection(points)
        and max(widths) >= 2 * max(widths[0], widths[-1], 1)
        and contiguous
    )


def require_distinct_carriers(
    carriers: dict[str, tuple[int, int, int, int]], required: set[str]
) -> None:
    if set(carriers) != required or len(set(carriers.values())) != len(carriers):
        raise AssertionError("Custom emoji carriers must have distinct semantic regions")


def locate_animation(
    frame: Image.Image, box: tuple[int, int, int, int], *, color_tolerance: int = 38
) -> LocatedFrame | None:
    """Locate authored geometry without stretching its semantic carrier."""
    left, top, right, bottom = box
    if not (0 <= left < right <= frame.width and 0 <= top < bottom <= frame.height):
        raise ValueError("Animation carrier box is outside its screenshot")
    marker = _matching(frame, box, MARKER, color_tolerance)
    matches = [
        (points, i)
        for i, (_, color) in enumerate(STATES)
        if (points := _matching(frame, box, color, color_tolerance))
    ]
    if not marker or len(matches) != 1:
        return None
    marker_box, moving_box = _bounds(marker), _bounds(matches[0][0])
    marker_scale = ((marker_box[2] - marker_box[0]) + (marker_box[3] - marker_box[1])) / 32
    moving_scale = ((moving_box[2] - moving_box[0]) + (moving_box[3] - moving_box[1])) / 48
    scale = (marker_scale + moving_scale) / 2
    if not 0.12 <= scale <= 1.5 or abs(marker_scale - moving_scale) > max(0.15, scale * 0.35):
        return None
    origin_x, origin_y = marker_box[0] - 8 * scale, marker_box[1] - 8 * scale
    if not (
        left <= origin_x
        and top <= origin_y
        and origin_x + 100 * scale < right
        and origin_y + 100 * scale < bottom
        and origin_x + 100 * scale < frame.width
        and origin_y + 100 * scale < frame.height
    ):
        return None
    (moving_x, moving_y), _ = STATES[matches[0][1]]
    tolerance = max(2.5, scale * 4)
    if (
        abs(moving_box[0] - (origin_x + moving_x * scale)) > tolerance
        or abs(moving_box[1] - (origin_y + moving_y * scale)) > tolerance
    ):
        return None
    pixels = frame.convert("RGB").load()
    if pixels is None:
        return None

    def sample(x: int, y: int) -> tuple[int, int, int]:
        return cast(
            tuple[int, int, int], pixels[round(origin_x + x * scale), round(origin_y + y * scale)]
        )

    outside = [
        (round(origin_x + 50 * scale), round(origin_y - 3 * scale)),
        (round(origin_x + 50 * scale), round(origin_y + 103 * scale)),
        (round(origin_x - 3 * scale), round(origin_y + 50 * scale)),
        (round(origin_x + 103 * scale), round(origin_y + 50 * scale)),
    ]
    backgrounds = [
        cast(tuple[int, int, int], pixels[x, y])
        for x, y in outside
        if left <= x < right and top <= y < bottom
    ]
    if not any(
        _close(sample(4, 4), background, 30) and _close(sample(94, 94), background, 30)
        for background in backgrounds
    ):
        return None
    background = next(
        background
        for background in backgrounds
        if _close(sample(4, 4), background, 30) and _close(sample(94, 94), background, 30)
    )
    for i, ((x, y), _) in enumerate(STATES):
        if i != matches[0][1] and not _close(sample(x + 12, y + 12), background, 30):
            return None
    return LocatedFrame(matches[0][1], origin_x, origin_y, scale)


def animation_states(
    frames: Sequence[Image.Image], boxes: Sequence[tuple[int, int, int, int]]
) -> list[int]:
    if len(frames) != len(boxes) or not frames:
        raise ValueError("Animation frames require matching semantic boxes")
    result: list[int] = []
    for frame, box in zip(frames, boxes, strict=True):
        located = locate_animation(frame, box)
        if located is not None and (not result or result[-1] != located.state):
            result.append(located.state)
    return result


def require_complete_cycle(states: Sequence[int]) -> None:
    """Require one adjacent cyclic four-state sequence; duplicates are allowed."""
    distinct = [state for i, state in enumerate(states) if i == 0 or state != states[i - 1]]
    for start in range(max(0, len(distinct) - 3)):
        window = distinct[start : start + 4]
        if len(window) == 4 and all(window[i] == (window[0] + i) % 4 for i in range(4)):
            return
    raise AssertionError("Animation burst did not contain an adjacent four-state cycle")
