"""The private emulator process selects a bounded, explicit boot policy."""

from gramlab._emulator import _emulator_command


def test_emulator_uses_a_bounded_four_core_cold_boot() -> None:
    command = _emulator_command("emulator")

    assert command[:3] == ["emulator", "-avd", "gramlab-probe"]
    assert "-no-snapshot" in command
    assert "-snapshot" not in command
    assert command[command.index("-gpu") + 1] == "swangle"
    assert command[command.index("-cores") + 1] == "4"
