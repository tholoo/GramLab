"""Pixel oracle for translated/scaled authored custom-emoji frames."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import cast, overload

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


@dataclass(frozen=True)
class AnimationTiming:
    """Feasible authored phase and the contiguous capture window that proves it.

    Integer indexing and iteration expose the two phase bounds for compatibility with
    callers that previously consumed the returned ``tuple[int, int]``.
    """

    phase_bounds_ns: tuple[int, int]
    capture_indexes: tuple[int, int]
    capture_times_ns: tuple[int, int]

    @property
    def capture_count(self) -> int:
        return self.capture_indexes[1] - self.capture_indexes[0] + 1

    @property
    def capture_span_ns(self) -> int:
        return self.capture_times_ns[1] - self.capture_times_ns[0]

    def __len__(self) -> int:
        return 2

    def __iter__(self) -> Iterator[int]:
        return iter(self.phase_bounds_ns)

    @overload
    def __getitem__(self, index: int) -> int: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[int, ...]: ...

    def __getitem__(self, index: int | slice) -> int | tuple[int, ...]:
        return self.phase_bounds_ns[index]


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
    values = list(carriers.values())
    for index, (left, top, right, bottom) in enumerate(values):
        for other_left, other_top, other_right, other_bottom in values[index + 1 :]:
            if max(left, other_left) < min(right, other_right) and max(top, other_top) < min(
                bottom, other_bottom
            ):
                raise AssertionError("Custom emoji carrier regions must not intersect")


@dataclass(frozen=True)
class _Shapes:
    state: int
    marker: list[tuple[int, int]]
    moving: list[tuple[int, int]]


def _center(points: Sequence[tuple[int, int]]) -> tuple[float, float]:
    # Pixel centers, rather than inclusive top-left pixel indices.
    return (
        sum(x + 0.5 for x, _ in points) / len(points),
        sum(y + 0.5 for _, y in points) / len(points),
    )


def _measure(
    frame: Image.Image, box: tuple[int, int, int, int], color_tolerance: int
) -> _Shapes | None:
    left, top, right, bottom = box
    if not (0 <= left < right <= frame.width and 0 <= top < bottom <= frame.height):
        raise ValueError("Animation carrier box is outside its screenshot")
    marker = _matching(frame, box, MARKER, color_tolerance)
    matches = [
        (points, i)
        for i, (_, color) in enumerate(STATES)
        if (points := _matching(frame, box, color, color_tolerance))
    ]
    if len(marker) < 4 or len(matches) != 1 or len(matches[0][0]) < 4:
        return None
    for points in (marker, matches[0][0]):
        left, top, right, bottom = _bounds(points)
        if len(points) < 0.6 * (right - left) * (bottom - top):
            return None
        for y in range(top, bottom):
            row = [x for x, py in points if py == y]
            if not row or max(row) - min(row) + 1 > len(row) + 1:
                return None
    return _Shapes(matches[0][1], marker, matches[0][0])


def _fit(shapes: Sequence[_Shapes]) -> tuple[float, float, float] | None:
    centers = [_center(shape.marker) for shape in shapes]
    marker_center = (
        sum(x for x, _ in centers) / len(centers),
        sum(y for _, y in centers) / len(centers),
    )
    numerator = denominator = 0.0
    lower, upper = 0.12, 1.5
    for shape, center in zip(shapes, centers, strict=True):
        moving = _center(shape.moving)
        expected = tuple(value - 4 for value in STATES[shape.state][0])
        for j in (0, 1):
            delta = moving[j] - center[j]
            numerator += delta * expected[j]
            denominator += expected[j] ** 2
            # At most one screenshot pixel of center uncertainty per axis.
            lower = max(lower, (delta - 1) / expected[j])
            upper = min(upper, (delta + 1) / expected[j])
        for points, extent in ((shape.marker, 16), (shape.moving, 24)):
            bounds = _bounds(points)
            for j in (0, 1):
                width = bounds[j + 2] - bounds[j]
                # Thresholding/resampling can displace either edge by one pixel.
                lower = max(lower, (width - 2) / extent)
                upper = min(upper, (width + 2) / extent)
    if lower > upper:
        return None
    scale = min(upper, max(lower, numerator / denominator))
    origin_x, origin_y = (value - 16 * scale for value in marker_center)
    for shape in shapes:
        for actual, expected in (
            (_center(shape.marker), (16, 16)),
            (_center(shape.moving), tuple(value + 12 for value in STATES[shape.state][0])),
        ):
            if any(
                abs(actual[j] - ((origin_x, origin_y)[j] + expected[j] * scale)) > 1 for j in (0, 1)
            ):
                return None
    return origin_x, origin_y, scale


def _validate(
    frame: Image.Image,
    box: tuple[int, int, int, int],
    shapes: _Shapes,
    transform: tuple[float, float, float],
) -> LocatedFrame | None:
    left, top, right, bottom = box
    origin_x, origin_y, scale = transform
    moving_box = _bounds(shapes.moving)
    if not (
        left <= origin_x
        and top <= origin_y
        and origin_x + 100 * scale < right
        and origin_y + 100 * scale < bottom
        and origin_x + 100 * scale < frame.width
        and origin_y + 100 * scale < frame.height
    ):
        return None
    (moving_x, moving_y), _ = STATES[shapes.state]
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
        if i != shapes.state and not _close(sample(x + 12, y + 12), background, 30):
            return None
    return LocatedFrame(shapes.state, origin_x, origin_y, scale)


def locate_animation(
    frame: Image.Image, box: tuple[int, int, int, int], *, color_tolerance: int = 38
) -> LocatedFrame | None:
    """Check one authored frame; a stationary sequence requires a shared fit below."""
    shapes = _measure(frame, box, color_tolerance)
    if shapes is None or (transform := _fit([shapes])) is None:
        return None
    return _validate(frame, box, shapes, transform)


def locate_animation_sequence(
    frames: Sequence[Image.Image], boxes: Sequence[tuple[int, int, int, int]]
) -> list[LocatedFrame]:
    """Validate every frame against one fixed carrier origin and isotropic scale."""
    if len(frames) != len(boxes) or not frames:
        raise ValueError("Animation frames require matching semantic boxes")
    shapes = []
    for frame, box in zip(frames, boxes, strict=True):
        measured = _measure(frame, box, 38)
        if measured is None:
            raise AssertionError("Animation frame lacks the authored shapes")
        shapes.append(measured)
    transform = _fit(shapes)
    if transform is None:
        raise AssertionError("Animation does not have one fixed authored transform")
    result = []
    for frame, box, measured in zip(frames, boxes, shapes, strict=True):
        located = _validate(frame, box, measured, transform)
        if located is None:
            raise AssertionError("Animation frame failed canvas or transparency checks")
        result.append(located)
    return result


def animation_states(
    frames: Sequence[Image.Image], boxes: Sequence[tuple[int, int, int, int]]
) -> list[int]:
    """Return consecutive distinct states after validating the entire shared fit."""
    try:
        located = locate_animation_sequence(frames, boxes)
    except AssertionError:
        return []
    return [
        frame.state
        for i, frame in enumerate(located)
        if not i or frame.state != located[i - 1].state
    ]


def capture_intervals(
    starts_ns: Sequence[int],
    ends_ns: Sequence[int] | None = None,
) -> list[tuple[int, int]]:
    """Use actual acquisition ends, or the retained probe's 80ms post-capture sleep.

    Historical captures lack an end for the final sample, so that sample is omitted.
    Start timestamps alone are never interpreted as exact capture instants.
    """
    if not starts_ns or any(type(value) is not int or value < 0 for value in starts_ns):
        raise ValueError("Capture starts must be nonnegative integer nanoseconds")
    if ends_ns is None:
        intervals = list(
            zip(starts_ns[:-1], (value - 80_000_000 for value in starts_ns[1:]), strict=True)
        )
    else:
        if len(starts_ns) != len(ends_ns):
            raise ValueError("Capture start/end counts differ")
        intervals = list(zip(starts_ns, ends_ns, strict=True))
    _validate_intervals(intervals)
    return intervals


def _validate_intervals(intervals: Sequence[tuple[int, int]]) -> None:
    for i, (start, end) in enumerate(intervals):
        if (
            type(start) is not int
            or type(end) is not int
            or start < 0
            or not 0 < end - start < 500_000_000
        ):
            raise ValueError("Capture intervals must be positive and shorter than half a period")
        if i and (intervals[i - 1][1] > start or end - intervals[i - 1][0] >= 1_000_000_000):
            raise ValueError("Capture intervals overlap or leave an ambiguous full-period gap")


def _forward_ticks(states: Sequence[int]) -> list[int]:
    ticks = [states[0]]
    for previous, state in pairwise(states):
        delta = (state - previous) % 4
        if delta > 2:
            raise AssertionError("Animation reversed or skipped more than one authored state")
        ticks.append(ticks[-1] + delta)  # Never invent an unobserved full-period wrap.
    return ticks


def _phase_bounds(
    states: Sequence[int], intervals_ns: Sequence[tuple[int, int]]
) -> tuple[int, int] | None:
    ticks = _forward_ticks(states)
    first = intervals_ns[0][0]
    lower = max(
        start - first - (tick + 1) * 250_000_000 + 1
        for (start, _), tick in zip(intervals_ns, ticks, strict=True)
    )
    upper = min(
        end - first - tick * 250_000_000 for (_, end), tick in zip(intervals_ns, ticks, strict=True)
    )
    return (lower, upper) if lower <= upper else None


def require_complete_cycle(
    states: Sequence[int],
    *,
    intervals_ns: Sequence[tuple[int, int]] | None = None,
) -> AnimationTiming | None:
    """Require cyclic states and a stable, long-window authored one-second phase.

    Timed bursts retain full-sequence order and four-state checks. Their phase may be proven by
    any contiguous window of at least 20 captures spanning at least five seconds. The selected
    window is the longest feasible window, with the earliest one winning a length tie. Returned
    inclusive phase bounds are relative to that window's first acquisition start. Each interval
    bounds an actual screenshot acquisition, not an inferred frame timestamp.
    """
    if any(type(state) is not int or state not in range(4) for state in states):
        raise ValueError("Animation states must be authored integer state indices")
    if intervals_ns is None:
        distinct = [state for i, state in enumerate(states) if i == 0 or state != states[i - 1]]
        for start in range(max(0, len(distinct) - 3)):
            window = distinct[start : start + 4]
            if all(window[i] == (window[0] + i) % 4 for i in range(4)):
                return None
        raise AssertionError("Animation burst did not contain an adjacent four-state cycle")
    if len(states) != len(intervals_ns):
        raise ValueError("Animation states require matching acquisition intervals")
    _validate_intervals(intervals_ns)
    if set(states) != {0, 1, 2, 3}:
        raise AssertionError("Animation burst did not observe every authored state")
    _forward_ticks(states)  # The chosen window cannot hide a defect elsewhere in the burst.
    if len(states) < 20:
        raise AssertionError("Animation timing needs at least 20 captures")
    for length in range(len(states), 19, -1):
        for start_index in range(len(states) - length + 1):
            end_index = start_index + length - 1
            capture_times = (intervals_ns[start_index][0], intervals_ns[end_index][1])
            if capture_times[1] - capture_times[0] < 5_000_000_000:
                continue
            phase = _phase_bounds(
                states[start_index : end_index + 1],
                intervals_ns[start_index : end_index + 1],
            )
            if phase is not None:
                return AnimationTiming(phase, (start_index, end_index), capture_times)
    raise AssertionError(
        "Animation states do not fit one authored one-second phase "
        "over 20 captures and five seconds"
    )
