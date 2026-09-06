"""The offline-edit scenario has identical bot/world semantics without Android."""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path

from test_android_recovery import assert_recovery_result

from gramlab.runtime import RuntimeProfile, Sandbox


def test_real_bot_older_edit_and_new_reply_match_the_android_recovery_scenario(
    tmp_path: Path,
) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "component-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("component_bot.py", "recovery_round_trip.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    shutil.copy2("tests/fixtures/recovery_bot.py", tmp_path / "recovery_bot.py")
    result = Sandbox(profile).supervise(
        [profile.python, "/work/recovery_round_trip.py"], data=tmp_path, timeout=30
    )
    assert result.returncode == 0, result.stderr
    (tmp_path / "recovery-result.json").write_text(result.stdout)
    assert_recovery_result(json.loads(result.stdout))
