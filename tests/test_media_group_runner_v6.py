"""Public runner and exact selector coverage for bridge-v6 media groups."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from gramlab._android import Android
from gramlab._interactions import Interactions
from gramlab.documents import DocumentUpload
from gramlab.runner import run
from gramlab.runtime import RuntimeProfile
from gramlab.world import World

PHOTO_ROOT = Path("tests/assets/rich-media")
EMOJI_ROOT = Path("tests/assets/custom-emoji")
FIRST_DOCUMENT = b"GramLab first grouped document\n"
SECOND_DOCUMENT = b"%PDF-1.4\nGramLab second grouped document\n%%EOF\n"


def profile() -> RuntimeProfile:
    return RuntimeProfile(bubblewrap="", python=sys.executable, store_paths=())


def stage_project(directory: Path, *, mode: str) -> Path:
    directory.mkdir()
    timeout = 60 if mode == "simulation-only" else 300
    (directory / "run.toml").write_text(
        f'schema = 1\nmode = "{mode}"\nseed = 114\nnow = 1700000000\ntimeout = {timeout}\n'
        '[scenario]\nentry = "scenario.py"\n'
        'files = ["scenario.py", "emoji-static.webp", "emoji-thumbnail.webp"]\n'
        '[bots.albums]\nentry = "bot.py"\n'
        'files = ["bot.py", "photo-one.png", "photo-two.jpg", '
        '"first-document.bin", "second-document.bin"]\n'
    )
    shutil.copy2("tests/probes/media_group_round_trip.py", directory / "scenario.py")
    shutil.copy2("tests/fixtures/media_group_bot.py", directory / "bot.py")
    shutil.copy2(EMOJI_ROOT / "emoji-static.webp", directory / "emoji-static.webp")
    shutil.copy2(EMOJI_ROOT / "emoji-thumbnail.webp", directory / "emoji-thumbnail.webp")
    shutil.copy2(PHOTO_ROOT / "photo-square-16x16.png", directory / "photo-one.png")
    shutil.copy2(PHOTO_ROOT / "photo-quadrants-64x48.jpg", directory / "photo-two.jpg")
    (directory / "first-document.bin").write_bytes(FIRST_DOCUMENT)
    (directory / "second-document.bin").write_bytes(SECOND_DOCUMENT)
    return directory / "run.toml"


def invoke(directory: Path, *, mode: str) -> tuple[dict[str, Any], Path]:
    manifest = stage_project(directory, mode=mode)
    output = directory.parent / f"{mode}-run"
    arguments = [
        sys.executable,
        "-m",
        "gramlab",
        "run",
        str(manifest),
        "--output",
        str(output),
        "--bridge-version",
        "6",
    ]
    if mode == "headless-android":
        android_profile = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
        apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
        if android_profile is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
            pytest.skip("Requires the normal31 APK, Android profile and accessible KVM")
        arguments.extend(("--android-profile", android_profile, "--android-apk", apk))
    result = subprocess.run(  # noqa: S603 — public CLI in the caller's outer network guard.
        arguments,
        capture_output=True,
        text=True,
        timeout=90 if mode == "simulation-only" else 420,
        env=os.environ.copy(),
    )
    (output.parent / f"{mode}-stdout.log").write_text(result.stdout)
    (output.parent / f"{mode}-stderr.log").write_text(result.stderr)
    recorded = json.loads((output / "result.json").read_text())
    assert result.returncode == 0, recorded
    assert recorded["outcome"] == "passed" and recorded["failure"] is None
    return recorded, output


def process_events(recorded: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in recorded["processes"][name]["stdout"].splitlines()
        if line.strip()
    ]


def assert_public_album_result(recorded: dict[str, Any], output: Path, *, native: bool) -> None:
    scenario = process_events(recorded, "scenario")
    bot = process_events(recorded, "bot:albums")
    assert len(scenario) == 1
    assert [item["event"] for item in bot] == ["photo_group", "document_group"]
    result = scenario[0]
    history = result["history"]
    assert history == recorded["histories"]["1"]
    assert [message["id"] for message in history] == list(range(1, 7))
    assert [message.get("media_group_id") for message in history] == [
        None,
        "1",
        "1",
        None,
        "2",
        "2",
    ]
    assert [message.get("caption") for message in history[1:3]] == ["Album 👩‍💻", None]
    assert [message.get("caption") for message in history[4:]] == [
        "First / نخست",
        "Second / دوم",
    ]
    assert [message["document"]["document_id"] for message in history[4:]] == ["1", "2"]
    assert result["photo_group"] == history[1:3]
    assert result["document_group"] == history[4:]
    for index in range(2):
        response = bot[index]["response"]
        assert response["status"] == 200 and response["body"]["ok"] is True
        public = response["body"]["result"]
        assert [item["message_id"] for item in public] == ([2, 3] if index == 0 else [5, 6])
        assert {item["media_group_id"] for item in public} == {str(index + 1)}
        assert len(public) == 2
    assert len(bot[0]["grouped_edit_rejections"]) == 2
    for rejection in bot[0]["grouped_edit_rejections"]:
        assert rejection["status"] == 400
        assert rejection["body"]["ok"] is False
        assert "editing grouped media" in rejection["body"]["description"]
    assert result["events"] == recorded["events"]
    created = [event for event in recorded["events"] if event["type"] == "message.created"]
    assert [event["data"] for event in created] == history
    assert [event["sequence"] for event in created[1:3]] == list(
        range(created[1]["sequence"], created[1]["sequence"] + 2)
    )
    assert [event["sequence"] for event in created[4:6]] == list(
        range(created[4]["sequence"], created[4]["sequence"] + 2)
    )
    with World.open(output / "world") as world:
        snapshot = world.client_snapshot(2, version=6)
        changes = world.client_changes(2, after=0, limit=100, version=6)
        assert snapshot["messages"] == history
        assert [
            row["data"] for row in changes["changes"] if row["type"] == "message.created"
        ] == history
        assert changes["cursor"] == changes["head"] == 6
        assert [row["position"] for row in changes["changes"]] == list(range(1, 7))
        descriptors = snapshot["documents"]
        assert [row["file_name"] for row in descriptors] == ["first-album.txt", "second-album.pdf"]
        assert [row["sha256"] for row in descriptors] == [
            hashlib.sha256(FIRST_DOCUMENT).hexdigest(),
            hashlib.sha256(SECOND_DOCUMENT).hexdigest(),
        ]
    assert [capture["label"] for capture in recorded["captures"]] == [
        "album-photos",
        "album-documents",
    ]
    assert all(capture["rendered"] is native for capture in recorded["captures"])
    assert recorded["configuration"]["bridge_version"] == 6
    assert recorded["configuration"].get("android", {}).get("bridge_version", 6) == 6
    assert "gramlab_bot_" not in json.dumps(recorded)
    assert "gramlab_client_" not in json.dumps(recorded)
    assert "gramlab-control_" not in json.dumps(recorded)


def test_public_runner_executes_complete_media_groups_at_v6(tmp_path: Path) -> None:
    recorded, output = invoke(tmp_path / "project", mode="simulation-only")
    assert recorded["android"] == {}
    assert_public_album_result(recorded, output, native=False)


@pytest.mark.parametrize("version", [True, False, 2, 7, "6", 6.0, None])
def test_runner_and_android_reject_non_exact_v6_selections(tmp_path: Path, version: object) -> None:
    with pytest.raises(ValueError, match="bridge version"):
        run(
            tmp_path / "missing.toml",
            tmp_path / "output",
            profile=profile(),
            bridge_version=version,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="bridge version"):
        Android(
            profile(),
            deadline=time.monotonic() + 5,
            secrets=[],
            bridge_version=version,  # type: ignore[arg-type]
        )


def test_virtual_callback_uses_the_selected_bridge_v6(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "world"
    keyboard = {"inline_keyboard": [[{"text": "Tap", "callback_data": "v6"}]]}
    with World.create(directory, seed=114, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Albums", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://d"},
            uploads={"d": DocumentUpload(FIRST_DOCUMENT, "first-album.txt")},
            reply_markup=keyboard,
        )
    selected: list[int] = []
    original = World.create_callback

    def tracked(world: World, *args: Any, version: int = 1, **kwargs: Any) -> dict[str, Any]:
        selected.append(version)
        return original(world, *args, version=version, **kwargs)

    monkeypatch.setattr(World, "create_callback", tracked)
    receipt = Interactions(directory, lock=threading.Lock(), bridge_version=6).tap_inline_button(
        chat_id=chat["id"], message_id=message["id"], row=0, column=0
    )
    with World.open(directory) as world:
        dependencies = world.callback_dependencies(user["id"], receipt["callback"], version=6)
    assert selected == [6]
    assert dependencies["documents"][0]["file_name"] == "first-album.txt"
    assert receipt["callback"]["message"] == message


@pytest.mark.android
def test_public_runner_captures_original_photo_and_document_groups_at_v6(tmp_path: Path) -> None:
    recorded, output = invoke(tmp_path / "project", mode="headless-android")
    assert_public_album_result(recorded, output, native=True)
    assert recorded["android"]["api"] == "36"
    assert recorded["android"]["abi"] == "x86_64"
    assert recorded["android"]["network"] == {"ipv4": 1, "ipv6": 1}
    assert recorded["android"]["filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "scenario_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    for row in recorded["captures"]:
        assert "Accounts: 0" in row["android"]["accounts"]
        expected = (
            ("Album 👩‍💻",)
            if row["label"] == "album-photos"
            else ("first-album.txt", "First / نخست", "second-album.pdf", "Second / دوم")
        )
        assert all(value in row["android"]["ui"] for value in expected)
        with Image.open(output / "captures" / f"{row['label']}.png") as capture:
            assert capture.size == (320, 640)
            assert len(capture.convert("RGB").getcolors(maxcolors=320 * 640) or []) > 16
