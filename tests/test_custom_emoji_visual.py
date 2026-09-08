"""Independent positive and negative checks for the custom-emoji pixel oracle."""

import pytest
from custom_emoji_visual import (
    MARKER,
    STATES,
    animation_states,
    capture_intervals,
    locate_animation,
    locate_animation_sequence,
    locate_static,
    require_complete_cycle,
    require_distinct_carriers,
)
from PIL import Image, ImageDraw

BACKGROUND = (237, 245, 252)


def _frame(state: int, *, scale: int = 1, opaque: bool = False) -> Image.Image:
    image = Image.new("RGB", (280, 160), BACKGROUND)
    draw = ImageDraw.Draw(image)
    ox, oy = 93, 24
    draw.rectangle(
        (ox + 8 * scale, oy + 8 * scale, ox + 24 * scale - 1, oy + 24 * scale - 1), fill=MARKER
    )
    if opaque:
        draw.rectangle((ox, oy, ox + 100 * scale - 1, oy + 100 * scale - 1), fill=(10, 10, 10))
        draw.rectangle(
            (ox + 8 * scale, oy + 8 * scale, ox + 24 * scale - 1, oy + 24 * scale - 1), fill=MARKER
        )
    (x, y), color = STATES[state]
    draw.rectangle(
        (ox + x * scale, oy + y * scale, ox + (x + 24) * scale - 1, oy + (y + 24) * scale - 1),
        fill=color,
    )
    return image


def test_locator_finds_translated_scaled_glyph_inside_wide_carrier() -> None:
    located = locate_animation(_frame(2, scale=1), (20, 10, 260, 140))
    assert located is not None and located.state == 2
    assert abs(located.origin_x - 93) <= 2 and abs(located.origin_y - 24) <= 2


def test_locator_finds_antialiased_quarter_scale_glyph() -> None:
    large = _frame(1, scale=1)
    small = large.resize((70, 40), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (240, 100), BACKGROUND)
    canvas.paste(small, (55, 30))
    located = locate_animation(canvas, (20, 10, 180, 90))
    assert located is not None and located.state == 1
    assert 0.18 <= located.scale <= 0.32


def test_cycle_requires_actual_adjacent_order_with_duplicates() -> None:
    frames = [_frame(state) for state in (3, 3, 0, 1, 2)]
    states = animation_states(frames, [(20, 10, 260, 140)] * len(frames))
    assert states == [3, 0, 1, 2]
    require_complete_cycle(states)
    with pytest.raises(AssertionError):
        require_complete_cycle([0, 2, 1, 3])


def test_locator_rejects_opaque_backing_and_global_changes() -> None:
    assert locate_animation(_frame(0, opaque=True), (20, 10, 260, 140)) is None
    changed = [Image.new("RGB", (280, 160), (index * 30, 20, 20)) for index in range(4)]
    assert animation_states(changed, [(20, 10, 260, 140)] * 4) == []


def test_distinct_carrier_mapping_rejects_overlapping_duplicate_bounds() -> None:
    carriers = {"incoming": (0, 0, 100, 50), "ordinary": (0, 0, 100, 50)}
    with pytest.raises(AssertionError, match="distinct"):
        require_distinct_carriers(carriers, {"incoming", "ordinary"})
    overlapping = {"incoming": (0, 0, 100, 50), "ordinary": (90, 10, 180, 60)}
    with pytest.raises(AssertionError, match="intersect"):
        require_distinct_carriers(overlapping, {"incoming", "ordinary"})


def test_static_oracle_requires_diamond_geometry_not_one_blue_pixel() -> None:
    image = Image.new("RGB", (200, 100), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.polygon(((70, 20), (82, 32), (70, 44), (58, 32)), fill=(88, 104, 240))
    assert locate_static(image, (20, 5, 180, 80))
    image.putpixel((150, 50), (88, 104, 240))
    assert not locate_static(image, (140, 40, 160, 60))
    checker = Image.new("RGB", (40, 40), BACKGROUND)
    checker_draw = ImageDraw.Draw(checker)
    for y in range(10, 22):
        for x in range(10, 22):
            if (x + y) % 2 == 0:
                checker_draw.point((x, y), fill=(88, 104, 240))
    assert not locate_static(checker, (0, 0, 40, 40))


def test_animation_locator_rejects_inferred_canvas_clipped_by_carrier() -> None:
    assert locate_animation(_frame(0), (100, 20, 200, 110)) is None


# Independently specified quarter-size color cores: one-pixel edge loss changes
# threshold bounds but leaves the authored marker/moving-square centers intact.
def _small_frame(state: int, *, dx: int = 0, scale: float = 0.24) -> Image.Image:
    image = Image.new("RGB", (200, 100), BACKGROUND)
    draw = ImageDraw.Draw(image)
    ox, oy = 84 + dx, 24
    for (x, y), color, width, height in [
        ((16, 16), MARKER, max(2, round(16 * scale) - 2), max(2, round(16 * scale) - 2)),
        (
            (STATES[state][0][0] + 12, STATES[state][0][1] + 12),
            STATES[state][1],
            max(3, round(24 * scale) - 1),
            max(3, round(24 * scale) - 2),
        ),
    ]:
        left = round(ox + x * scale - width / 2)
        top = round(oy + y * scale - height / 2)
        draw.rectangle((left, top, left + width - 1, top + height - 1), fill=color)
    return image


def test_threshold_edge_loss_preserves_authored_stationary_animation() -> None:
    frames = [_small_frame(state) for state in range(4)]
    assert animation_states(frames, [(20, 10, 180, 90)] * 4) == [0, 1, 2, 3]


def test_sampled_animation_allows_one_skipped_state_in_cyclic_order() -> None:
    intervals = [
        (t, t + 100_000_000) for t in (0, 300_000_000, 800_000_000, 1_100_000_000, 1_550_000_000)
    ]
    assert require_complete_cycle([0, 1, 3, 0, 2], intervals_ns=intervals) is not None


@pytest.mark.parametrize("defect", ["drift", "extent", "position", "opaque", "isolated", "scale"])
def test_shared_fit_rejects_incorrect_animation_geometry(defect: str) -> None:
    frames = [
        _small_frame(state, dx=4 if defect == "drift" and state % 2 else 0) for state in range(4)
    ]
    if defect == "scale":
        frames[2] = _small_frame(2, scale=0.375)
    elif defect == "opaque":
        frames = [_frame(state, opaque=True) for state in range(4)]
    elif defect in {"extent", "position", "isolated"}:
        image = Image.new("RGB", (200, 100), BACKGROUND)
        draw = ImageDraw.Draw(image)
        draw.rectangle((87, 27, 88, 28), fill=MARKER)
        # Wrong state-2 shape; every other frame remains a valid authored sample.
        box = {
            "extent": (96, 34, 97, 35),
            "position": (115, 33, 119, 36),
            "isolated": (98, 35, 98, 35),
        }[defect]
        draw.rectangle(box, fill=STATES[2][1])
        frames[2] = image
    if defect in {"drift", "scale"}:
        assert all(locate_animation(frame, (20, 10, 180, 90)) is not None for frame in frames)
    with pytest.raises(AssertionError):
        locate_animation_sequence(frames, [(20, 10, 180, 90)] * 4)


def test_shared_fit_returns_identical_transform_for_every_state() -> None:
    result = locate_animation_sequence(
        [_small_frame(state) for state in range(4)], [(20, 10, 180, 90)] * 4
    )
    assert [frame.state for frame in result] == [0, 1, 2, 3]
    assert len({(frame.origin_x, frame.origin_y, frame.scale) for frame in result}) == 1
    assert 0.22 <= result[0].scale <= 0.26
    assert abs(result[0].origin_x - 84) < 1
    assert abs(result[0].origin_y - 24) < 1


def _intervals() -> list[tuple[int, int]]:
    # Each acquisition straddles the point at which an exact-start interpretation
    # would give a contradictory phase. A single 200ms phase satisfies all windows.
    return [
        (0, 240_000_000),
        (360_000_000, 600_000_000),
        (720_000_000, 960_000_000),
        (1_250_000_000, 1_490_000_000),
        (1_850_000_000, 2_090_000_000),
    ]


def test_acquisition_uncertainty_has_one_reviewable_phase() -> None:
    phase = require_complete_cycle([0, 1, 3, 0, 2], intervals_ns=_intervals())
    assert phase is not None and phase[0] <= 200_000_000 <= phase[1]
    with pytest.raises(AssertionError, match="one-second phase"):
        require_complete_cycle(
            [0, 1, 3, 0, 2], intervals_ns=[(start, start + 1) for start, _ in _intervals()]
        )


@pytest.mark.parametrize(
    "states", [[0, 3, 1, 0, 2], [0, 2, 1, 3, 0], [0, 0, 0, 1, 0], [0, 1, 0, 1, 0]]
)
def test_sampled_phase_rejects_reverse_shuffled_or_missing_states(states: list[int]) -> None:
    with pytest.raises(AssertionError):
        require_complete_cycle(states, intervals_ns=_intervals())


@pytest.mark.parametrize("factor", [0.5, 2.0])
def test_authored_period_rejects_changed_playback_speed(factor: float) -> None:
    # Keep acquisition widths small and bounded; only the actual elapsed timing changes.
    starts = [0, 300_000_000, 800_000_000, 1_100_000_000, 1_550_000_000]
    intervals = [(int(start * factor), int(start * factor) + 10_000_000) for start in starts]
    with pytest.raises((AssertionError, ValueError)):
        require_complete_cycle([0, 1, 3, 0, 2], intervals_ns=intervals)


@pytest.mark.parametrize(
    "intervals",
    [
        [(0, 600_000_000)],
        [(0, 0)],
        [(1, 0)],
        [(-1, 1)],
        [(True, 3)],
        [(0, 200_000_000), (100_000_000, 300_000_000)],
        [(0, 100_000_000), (2_000_000_000, 2_100_000_000)],
    ],
)
def test_capture_intervals_reject_unbounded_overlap_and_arbitrary_wraps(
    intervals: list[tuple[int, int]],
) -> None:
    with pytest.raises(ValueError):
        capture_intervals([start for start, _ in intervals], [end for _, end in intervals])


def test_retained_intervals_omit_only_the_unknown_final_acquisition() -> None:
    starts = [0, 360_000_000, 720_000_000, 1_080_000_000]
    assert capture_intervals(starts) == [
        (0, 280_000_000),
        (360_000_000, 640_000_000),
        (720_000_000, 1_000_000_000),
    ]
    ends = [200_000_000, 560_000_000, 920_000_000, 1_280_000_000]
    assert capture_intervals(starts, ends) == list(zip(starts, ends, strict=True))
    with pytest.raises(ValueError):
        capture_intervals(starts, [])


def test_stationary_sequence_rejects_global_color_change() -> None:
    frames = [Image.new("RGB", (200, 100), color) for _, color in STATES]
    with pytest.raises(AssertionError):
        locate_animation_sequence(frames, [(20, 10, 180, 90)] * 4)
