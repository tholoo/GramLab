"""Contained scenarios register static and animated custom emoji through public control."""

import json
import subprocess
import sys
from pathlib import Path

SCENARIO = r"""import os
from pathlib import Path
from gramlab.scenario import Scenario

lab = Scenario.from_environment()
static = Path("emoji-static.webp").read_bytes()
animated = Path("emoji-animated.webm").read_bytes()
thumbnail = Path("emoji-thumbnail.webp").read_bytes()
assert "GRAMLAB_FFMPEG" not in os.environ and "GRAMLAB_FFPROBE" not in os.environ
assert lab.register_custom_emoji(
    request_id="static", main=static, thumbnail=thumbnail, fallback="🙂",
) == {
    "custom_emoji_id": "1", "fallback": "🙂", "free": True,
    "needs_repainting": False, "main_asset_id": 1,
    "thumbnail_asset_id": 2, "duration_ms": 0,
}
animated_expected = {
    "custom_emoji_id": "7000000000000000000", "fallback": "✨", "free": False,
    "needs_repainting": True, "main_asset_id": 3,
    "thumbnail_asset_id": 2, "duration_ms": 1000,
}
assert lab.register_custom_emoji(
    request_id="animated", main=animated, thumbnail=thumbnail, fallback="✨",
    custom_emoji_id="7000000000000000000", free=False, needs_repainting=True,
) == animated_expected
assert lab.register_custom_emoji(
    request_id="animated", main=animated, thumbnail=thumbnail, fallback="✨",
    custom_emoji_id="7000000000000000000", free=False, needs_repainting=True,
) == animated_expected
print("Custom emoji registration verified")
"""


def test_contained_runner_registers_static_and_animated_custom_emoji(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    manifest = project / "run.toml"
    manifest.write_text(
        'schema = 1\nseed = 7\nnow = 1700000000\ntimeout = 10\n'
        '[scenario]\nentry = "scenario.py"\n'
        'files = ["scenario.py", "emoji-static.webp", "emoji-animated.webm", '
        '"emoji-thumbnail.webp"]\n'
        '[bots.echo]\nentry = "bot.py"\nfiles = ["bot.py"]\n'
    )
    (project / "scenario.py").write_text(SCENARIO)
    (project / "bot.py").write_bytes(Path("tests/fixtures/echo_bot.py").read_bytes())
    fixture = Path("tests/assets/custom-emoji")
    for name in ("emoji-static.webp", "emoji-animated.webm", "emoji-thumbnail.webp"):
        (manifest.parent / name).write_bytes((fixture / name).read_bytes())
    output = tmp_path / "run"
    result = subprocess.run(  # noqa: S603 — actual CLI in the enclosing network guard
        [sys.executable, "-m", "gramlab", "run", str(manifest), "--output", str(output)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        (output / "result.json").read_text() if output.exists() else result.stderr
    )
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["outcome"] == "passed"
    assert recorded["processes"]["scenario"]["stdout"] == ("Custom emoji registration verified\n")
    assert recorded["world"] == {
        "schema": 1,
        "seed": 7,
        "now": 1700000000,
        "users": [{"id": 1, "is_bot": True, "first_name": "echo"}],
        "chats": [],
    }
