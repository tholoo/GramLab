"""Independent positive and negative checks for the custom-emoji pixel oracle."""

import pytest
from custom_emoji_visual import (
    MARKER,
    STATES,
    animation_states,
    locate_animation,
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
