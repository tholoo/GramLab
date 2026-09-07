"""Independent positive and negative checks for the custom-emoji pixel oracle."""

from custom_emoji_visual import STATES, animation_states, require_complete_cycle
from PIL import Image, ImageDraw


def _frame(state: int) -> Image.Image:
    image = Image.new("RGB", (140, 120), (237, 245, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((28, 18, 43, 33), fill=(32, 220, 96))
    (x, y), color = STATES[state]
    draw.rectangle((20 + x, 10 + y, 20 + x + 23, 10 + y + 23), fill=color)
    return image


def test_pixel_oracle_accepts_authored_cycle_in_semantic_box() -> None:
    frames = [_frame(state) for state in (0, 0, 1, 3, 0, 2, 3)]
    states = animation_states(frames, [(20, 10, 120, 110)] * len(frames), tolerance=2)
    assert states == [0, 1, 3, 0, 2, 3]
    require_complete_cycle(states)


def test_pixel_oracle_rejects_global_change_without_fixture_geometry() -> None:
    frames = [Image.new("RGB", (140, 120), (index * 30, 20, 20)) for index in range(4)]
    states = animation_states(frames, [(20, 10, 120, 110)] * 4)
    assert states == []
    try:
        require_complete_cycle(states)
    except AssertionError as error:
        assert "all four" in str(error)
    else:
        raise AssertionError("Global screenshot changes passed the animation oracle")
