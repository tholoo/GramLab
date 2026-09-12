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
    ticks = [0, 1, 3, *range(4, 21)]
    intervals = [(tick * 250_000_000, tick * 250_000_000 + 100_000_000) for tick in ticks]
    timing = require_complete_cycle([tick % 4 for tick in ticks], intervals_ns=intervals)
    assert timing is not None and timing.capture_indexes == (0, 19)


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
    intervals = [
        (0, 240_000_000),
        (360_000_000, 600_000_000),
        (720_000_000, 960_000_000),
        (1_250_000_000, 1_490_000_000),
        (1_850_000_000, 2_090_000_000),
    ]
    intervals.extend(((2_090_000_000, 2_170_000_000), (2_170_000_000, 2_250_000_000)))
    intervals.extend(
        (tick * 250_000_000 + 160_000_000, tick * 250_000_000 + 240_000_000)
        for tick in range(9, 23)
    )
    return intervals


def _ideal_burst() -> tuple[list[int], list[tuple[int, int]]]:
    states = [index % 4 for index in range(24)]
    intervals = [
        (index * 250_000_000 + 100_000_000, index * 250_000_000 + 120_000_000)
        for index in range(24)
    ]
    return states, intervals


def _bounded_window_burst() -> tuple[list[int], list[tuple[int, int]]]:
    """A 24-frame burst whose first two captures contradict the stable suffix."""
    states = [index % 4 for index in range(24)]
    intervals = [(0, 20_000_000), (250_000_000, 270_000_000)]
    intervals.extend(
        (index * 250_000_000 + 300_000_000, index * 250_000_000 + 320_000_000)
        for index in range(2, 24)
    )
    return states, intervals


def test_timing_accepts_long_stable_window_when_full_horizon_has_no_phase() -> None:
    states, intervals = _bounded_window_burst()

    # Independently demonstrate the old full-horizon intersection is empty.
    full_horizon_lower = max(
        start - (index + 1) * 250_000_000 + 1 for index, (start, _) in enumerate(intervals)
    )
    full_horizon_upper = min(end - index * 250_000_000 for index, (_, end) in enumerate(intervals))
    assert (full_horizon_lower, full_horizon_upper) == (50_000_001, 20_000_000)

    timing = require_complete_cycle(states, intervals_ns=intervals)

    assert timing is not None
    assert timing.capture_indexes == (2, 23)
    assert timing.capture_count == 22
    assert timing.capture_span_ns == 5_270_000_000
    assert timing.phase_bounds_ns[0] <= timing.phase_bounds_ns[1]


def test_acquisition_uncertainty_has_one_reviewable_phase() -> None:
    ticks = [0, 1, 3, 4, 6, *range(7, 23)]
    phase = require_complete_cycle([tick % 4 for tick in ticks], intervals_ns=_intervals())
    assert phase is not None and phase[0] <= 200_000_000 <= phase[1]
    with pytest.raises(AssertionError, match="one-second phase"):
        require_complete_cycle(
            [tick % 4 for tick in ticks],
            intervals_ns=[(start, start + 1) for start, _ in _intervals()],
        )


def test_bounded_window_still_rejects_reversal_outside_selected_suffix() -> None:
    states, intervals = _bounded_window_burst()
    states[:2] = [1, 0]
    with pytest.raises(AssertionError, match="reversed"):
        require_complete_cycle(states, intervals_ns=intervals)


def test_sampled_phase_rejects_reverse_and_over_skipping() -> None:
    _, intervals = _ideal_burst()
    reversed_states = [(-index) % 4 for index in range(24)]
    with pytest.raises(AssertionError, match="reversed"):
        require_complete_cycle(reversed_states, intervals_ns=intervals)
    over_skipping = [index % 4 for index in range(24)]
    over_skipping[10] = (over_skipping[9] + 3) % 4
    with pytest.raises(AssertionError, match="skipped"):
        require_complete_cycle(over_skipping, intervals_ns=intervals)


def test_sampled_phase_rejects_short_count_duration_and_incomplete_sequences() -> None:
    states, intervals = _ideal_burst()
    with pytest.raises(AssertionError, match="at least 20"):
        require_complete_cycle(states[:19], intervals_ns=intervals[:19])
    with pytest.raises(AssertionError, match="20 captures and five seconds"):
        require_complete_cycle(states[:20], intervals_ns=intervals[:20])
    with pytest.raises(AssertionError, match="every authored state"):
        require_complete_cycle([0] * 24, intervals_ns=intervals)


def test_sampled_phase_rejects_forward_but_phase_incoherent_sequence() -> None:
    states = [index % 4 for index in range(24)]
    intervals = [
        (index * 300_000_000 + 100_000_000, index * 300_000_000 + 120_000_000)
        for index in range(24)
    ]
    with pytest.raises(AssertionError, match="20 captures and five seconds"):
        require_complete_cycle(states, intervals_ns=intervals)


def test_authored_period_rejects_changed_playback_speed() -> None:
    slow_states = [index % 4 for index in range(24)]
    slow_intervals = [
        (index * 375_000_000 + 100_000_000, index * 375_000_000 + 110_000_000)
        for index in range(24)
    ]
    ticks = [0]
    for index in range(1, 24):
        ticks.append(ticks[-1] + (2 if index % 2 == 0 else 1))
    fast_states = [tick % 4 for tick in ticks]
    fast_intervals = [
        (tick * 225_000_000 + 100_000_000, tick * 225_000_000 + 110_000_000) for tick in ticks
    ]
    for states, intervals in (
        (slow_states, slow_intervals),
        (fast_states, fast_intervals),
    ):
        with pytest.raises(AssertionError, match="20 captures and five seconds"):
            require_complete_cycle(states, intervals_ns=intervals)


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
