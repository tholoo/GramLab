"""Independent checks for the public media-group scenario source."""

from pathlib import Path


def test_scenario_uses_native_compatible_actions_without_fixed_sleeps() -> None:
    source = Path("tests/probes/media_group_round_trip.py").read_text()
    assert "start_bot_chat" in source
    assert "type_message" in source
    assert source.count("capture_chat") == 2
    assert "time.sleep" not in source


def test_contained_bot_uses_two_atomic_group_calls() -> None:
    source = Path("tests/fixtures/media_group_bot.py").read_text()
    assert source.count('"sendMediaGroup"') == 2
    assert '"sendPhoto"' not in source
    assert '"sendDocument"' not in source
    assert '"reply_markup"' not in source
