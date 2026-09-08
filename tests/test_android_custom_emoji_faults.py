"""Bounded original custom-emoji failures, restart recovery, and shared transfer."""

import hashlib
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image
from test_android_quoted_code import assert_isolation

from gramlab.reports import Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox
from gramlab.world import World

ASSETS = Path("tests/assets/custom-emoji")
STATIC = ASSETS / "emoji-static.webp"
THUMBNAIL = ASSETS / "emoji-thumbnail.webp"
PACKAGE = "org.gramlab.android"
FAULT_CASES = {
    "single-404": ("missing", ["1"], ["1"], ["Single unavailable"]),
    "mixed-404": ("missing", ["1", "2"], ["2"], ["Mixed unavailable"]),
    "partial-200": ("partial", ["1", "2"], [], ["Partial response"]),
}


def _utf16_offset(value: str, index: int) -> int:
    return len(value[:index].encode("utf-16-le")) // 2


def _entities(text: str, identifiers: list[int]) -> list[dict[str, Any]]:
    fallback = "👩‍💻"
    positions = []
    start = 0
    while (position := text.find(fallback, start)) >= 0:
        positions.append(position)
        start = position + len(fallback)
    assert len(positions) == len(identifiers)
    return [
        {
            "type": "custom_emoji",
            "offset": _utf16_offset(text, position),
            "length": 5,
            "custom_emoji_id": identifier,
        }
        for position, identifier in zip(positions, identifiers, strict=True)
    ]


def _stage_world(directory: Path, messages: list[tuple[str, list[int]]]) -> dict[str, Any]:
    static = STATIC.read_bytes()
    thumbnail = THUMBNAIL.read_bytes()
    with World.create(directory, seed=66, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Echo", username="gramlab_echo_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.register_custom_emoji(
            request_id="static",
            main=static,
            thumbnail=thumbnail,
            fallback="👩‍💻",
            custom_emoji_id=1,
        )
        world.register_custom_emoji(
            request_id="second-static",
            main=static,
            thumbnail=thumbnail,
            fallback="👩‍💻",
            custom_emoji_id=2,
        )
        for text, identifiers in messages:
            world.send_message(
                chat_id=1,
                sender_id=2,
                text=text,
                entities=_entities(text, identifiers),
            )
        return {
            "world_id": world.world_id,
            "capability": world.issue_client_token(1),
        }


def _expected_assets() -> dict[str, dict[str, Any]]:
    return {
        "2_2.jpg": {
            "size": THUMBNAIL.stat().st_size,
            "sha256": hashlib.sha256(THUMBNAIL.read_bytes()).hexdigest(),
        }
    }


def _stage_shared_case(tmp_path: Path) -> dict[str, Any]:
    shared_directory = tmp_path / "world-shared"
    shared_identity = _stage_world(
        shared_directory,
        [("Static carrier 👩‍💻", [1]), ("Second carrier 👩‍💻", [2])],
    )
    return {
        "name": "shared-thumbnail",
        "world": shared_directory.name,
        "labels": ["Static carrier", "Second carrier"],
        **shared_identity,
    }


def _stage_cases(tmp_path: Path) -> dict[str, Any]:
    document_cases = []
    texts = {
        "single-404": [("Single unavailable 👩‍💻", [1])],
        "mixed-404": [("Mixed unavailable 👩‍💻 👩‍💻", [1, 2])],
        "partial-200": [("Partial response 👩‍💻 👩‍💻", [1, 2])],
    }
    for name, (fault, expected_ids, missing_ids, labels) in FAULT_CASES.items():
        directory = tmp_path / ("world-" + name)
        identity = _stage_world(directory, texts[name])
        document_cases.append(
            {
                "name": name,
                "world": directory.name,
                "fault": fault,
                "expected_ids": expected_ids,
                "missing_ids": missing_ids,
                "labels": labels,
                **identity,
            }
        )
    return {
        "document_cases": document_cases,
        "shared_case": _stage_shared_case(tmp_path),
        "expected": _expected_assets(),
    }


def _document_terminal(trace: list[dict[str, Any]]) -> list[str]:
    return [
        row["event"]
        for row in trace
        if row.get("method") == "TL_messages_getCustomEmojiDocuments"
        and (row.get("event") == "response" or str(row.get("event", "")).startswith("error_"))
    ]


def _assert_capture(tmp_path: Path, capture: dict[str, Any], labels: list[str]) -> None:
    joined = "\n".join(capture["labels"])
    assert all(label in joined for label in labels)
    assert (tmp_path / capture["png"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def _diamond_count(tmp_path: Path, capture: dict[str, Any], label: str) -> int:
    with Image.open(tmp_path / capture["png"]) as opened:
        image = opened.convert("RGB")
    matches = [record for record in capture["bounds"] if label in record["text"]]
    assert len(matches) == 1
    left, top, right, bottom = matches[0]["bounds"]
    crop = image.crop((left, top, right, bottom))
    blue = {
        (x, y)
        for y in range(crop.height)
        for x in range(crop.width)
        if all(
            abs(cast(tuple[int, ...], crop.getpixel((x, y)))[index] - expected) <= 45
            for index, expected in enumerate((88, 104, 240))
        )
    }
    components = []
    while blue:
        pending = [blue.pop()]
        component = set(pending)
        while pending:
            x, y = pending.pop()
            neighbors = {(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy}
            found = neighbors & blue
            blue -= found
            component |= found
            pending.extend(found)
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        width = max(xs) - min(xs) + 1
        height = max(ys) - min(ys) + 1
        rows = [sum(point[1] == row for point in component) for row in range(min(ys), max(ys) + 1)]
        if (
            len(component) >= 20
            and width >= 7
            and height >= 7
            and width <= height * 2
            and height <= width * 2
            and max(rows) > rows[0]
            and max(rows) > rows[-1]
        ):
            components.append(component)
    return len(components)


def _carrier_pixels(tmp_path: Path, capture: dict[str, Any], label: str) -> bytes:
    matches = [record for record in capture["bounds"] if label in record["text"]]
    assert len(matches) == 1
    with Image.open(tmp_path / capture["png"]) as opened:
        return opened.convert("RGB").crop(tuple(matches[0]["bounds"])).tobytes()


def _assert_cache(
    files: dict[str, list[dict[str, Any]]], expected: dict[str, dict[str, Any]], names: set[str]
) -> None:
    for name in names:
        assert files[name]
        assert all(
            copy["size"] == expected[name]["size"] and copy["sha256"] == expected[name]["sha256"]
            for copy in files[name]
        )


def _android_inputs() -> tuple[RuntimeProfile, str]:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile, reviewed custom emoji APK and accessible KVM")
    return RuntimeProfile.load(Path(manifest)), apk


def _execute_android(
    tmp_path: Path, profile: RuntimeProfile, apk: str, cases: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    (tmp_path / "cases.json").write_text(json.dumps(cases))
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in (
        "emulator_process.py",
        "android_guest.py",
        "native_asset_proxy.py",
        "custom_emoji_fault_server.py",
        "android_custom_emoji_faults.py",
    ):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_custom_emoji_faults.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image,
        ],
        data=tmp_path,
        kvm=True,
        timeout=900,
    )
    (tmp_path / "custom-emoji-fault-result.json").write_text(result.stdout)
    (tmp_path / "custom-emoji-fault-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]
    assert "Accounts: 0" in observed["accounts"]
    assert observed["expected"] == cases["expected"]
    return full, observed, toolchain, image


def _assert_shared_case(tmp_path: Path, observed: dict[str, Any]) -> tuple[Screenshot, Screenshot]:
    shared = observed["shared"]
    assert "Status: ok" in shared["launch"] and "LaunchState: COLD" in shared["launch"]
    assert shared["hold"] == {"started": True, "partial_sent": True, "finished": True}
    for stage, labels in (
        ("initial_capture", ["Static carrier", "Second carrier"]),
        ("removed_capture", ["Static removed", "Second carrier"]),
        ("complete_capture", ["Static removed", "Second carrier"]),
    ):
        _assert_capture(tmp_path, shared[stage], labels)
    asset_two = [row for row in shared["assets"] if row["asset_id"] == 2]
    assert len(asset_two) == 1
    assert asset_two[0]["status"] == 200 and asset_two[0]["error"] is None
    assert asset_two[0]["bytes"] == observed["expected"]["2_2.jpg"]["size"]
    events = [row for row in shared["trace"] if row.get("asset_id") == 2]
    assert any(row["event"] == "media_load_success" for row in events)
    assert not any(row["event"] == "media_load_cancel" for row in events)
    _assert_cache(shared["cache"], observed["expected"], {"2_2.jpg"})
    assert _diamond_count(tmp_path, shared["complete_capture"], "Second carrier") == 1
    assert observed["limits"] == {
        "same_process_refetch": "External outcome only; callback owner identity is not observed.",
        "late_completion": (
            "File completion and surviving UI only; removed receiver delivery is not observed."
        ),
        "batching": (
            "A false batch_observed value retains failure evidence without claiming original "
            "batching."
        ),
    }
    return (
        Screenshot(
            caption="shared-removed",
            png=(tmp_path / shared["removed_capture"]["png"]).read_bytes(),
        ),
        Screenshot(
            caption="shared-complete",
            png=(tmp_path / shared["complete_capture"]["png"]).read_bytes(),
        ),
    )


@pytest.mark.android
def test_original_custom_emoji_faults_and_shared_thumbnail_recover(tmp_path: Path) -> None:
    profile, apk = _android_inputs()
    cases = _stage_cases(tmp_path)
    full, observed, toolchain, image = _execute_android(tmp_path, profile, apk, cases)
    assert set(observed["document_cases"]) == set(FAULT_CASES)
    screenshots = []

    for name, (fault, expected_ids, _missing_ids, labels) in FAULT_CASES.items():
        case = observed["document_cases"][name]
        assert case["fault"] == fault
        assert case["expected_ids"] == expected_ids
        assert (
            "Status: ok" in case["failed_launch"] and "LaunchState: COLD" in case["failed_launch"]
        )
        failed_documents = case["failed_documents"]
        assert {
            identifier for row in failed_documents for identifier in row["custom_emoji_ids"]
        } == set(expected_ids)
        assert all(row["phase"] == "failed" for row in failed_documents)
        assert all(
            row["status"] == (404 if fault == "missing" else 200) for row in failed_documents
        )
        assert all(row["bytes"] > 0 and row["error"] is None for row in failed_documents)
        assert case["batch_observed"] == any(
            row["custom_emoji_ids"] == expected_ids for row in failed_documents
        )
        if len(expected_ids) > 1:
            assert case["batch_observed"], "Original client did not exercise the required pair"
        terminals = _document_terminal(case["failed_trace"])
        assert len(terminals) == len(failed_documents)
        assert set(terminals) == {"error_503" if fault == "missing" else "error_400"}
        history_response = next(
            index
            for index, row in enumerate(case["failed_trace"])
            if row.get("event") == "response" and row.get("method") == "TL_messages_getHistory"
        )
        document_request = next(
            index
            for index, row in enumerate(case["failed_trace"])
            if row.get("event") == "request"
            and row.get("method") == "TL_messages_getCustomEmojiDocuments"
        )
        assert history_response < document_request
        assert case["failed_assets"] == []
        assert case["idle_document_count"] == case["document_count_before_idle"]
        assert case["idle_seconds"] == 3.0
        for stage in ("failed_capture", "idle_capture", "reopen_capture"):
            _assert_capture(tmp_path, case[stage], labels)
        assert _diamond_count(tmp_path, case["failed_capture"], labels[0]) == 0
        assert _diamond_count(tmp_path, case["idle_capture"], labels[0]) == 0
        assert _carrier_pixels(tmp_path, case["failed_capture"], labels[0]) == _carrier_pixels(
            tmp_path, case["idle_capture"], labels[0]
        )
        assert case["stopped_pid"] == ""
        assert "Status: ok" in case["recovered_launch"]
        assert "LaunchState: COLD" in case["recovered_launch"]
        recovery = [row for row in case["recovered_documents"] if row["phase"] == "recovery"]
        assert recovery and recovery[-1]["status"] == 200 and recovery[-1]["error"] is None
        assert _document_terminal(case["recovered_trace"])[-1] == "response"
        _assert_capture(tmp_path, case["recovered_capture"], labels)
        assert _diamond_count(tmp_path, case["recovered_capture"], labels[0]) == len(expected_ids)
        _assert_cache(case["recovered_cache"], observed["expected"], {"2_2.jpg"})
        recovery_assets = [row for row in case["recovered_assets"] if row["phase"] == "recovery"]
        assert recovery_assets
        assert {row["asset_id"] for row in recovery_assets} == {2}
        assert all(row["status"] == 200 and row["error"] is None for row in recovery_assets)
        assert not case["same_process_refetch"] or len(case["reopened_documents"]) > len(
            case["failed_documents"]
        )
        for stage in ("failed_capture", "recovered_capture"):
            screenshots.append(
                Screenshot(
                    caption=f"{name}-{stage.removesuffix('_capture')}",
                    png=(tmp_path / case[stage]["png"]).read_bytes(),
                )
            )

    screenshots.extend(_assert_shared_case(tmp_path, observed))
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="custom-emoji-native-faults",
            title="Original custom emoji failure and recovery",
            mode="headless-android",
            outcome="passed",
            seed=66,
            profile={
                "Android SDK": str(toolchain["sdk"]["platform"]),
                "System image": image,
                "Application": PACKAGE,
            },
            summary=(
                "Authorized custom emoji messages remain stable through bounded lookup faults, "
                "recover after a cold launch, and retain a shared thumbnail transfer."
            ),
            evidence={
                "Document cases": observed["document_cases"],
                "Shared thumbnail": observed["shared"],
                "Network isolation": full["network"],
            },
            screenshots=tuple(screenshots),
            limitations=tuple(observed["limits"].values()),
        ),
    )


@pytest.mark.android
def test_original_custom_emoji_shared_thumbnail_progressive_transfer(tmp_path: Path) -> None:
    profile, apk = _android_inputs()
    cases = {
        "selector": "shared",
        "document_cases": [],
        "shared_case": _stage_shared_case(tmp_path),
        "expected": _expected_assets(),
    }
    full, observed, toolchain, image = _execute_android(tmp_path, profile, apk, cases)
    assert observed["document_cases"] == {}
    screenshots = _assert_shared_case(tmp_path, observed)
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="custom-emoji-native-shared-thumbnail",
            title="Original custom emoji shared thumbnail transfer",
            mode="headless-android",
            outcome="passed",
            seed=66,
            profile={
                "Android SDK": str(toolchain["sdk"]["platform"]),
                "System image": image,
                "Application": PACKAGE,
            },
            summary=(
                "One original shared thumbnail transfer remains active while its first carrier "
                "is removed, then completes for the surviving carrier."
            ),
            evidence={
                "Shared thumbnail": observed["shared"],
                "Network isolation": full["network"],
            },
            screenshots=screenshots,
            limitations=tuple(observed["limits"].values()),
        ),
    )


def test_fault_case_staging_uses_isolated_worlds_and_shared_thumbnail(tmp_path: Path) -> None:
    cases = _stage_cases(tmp_path)
    worlds = [case["world"] for case in cases["document_cases"]] + [cases["shared_case"]["world"]]
    assert len(set(worlds)) == 4
    assert all((tmp_path / world).is_dir() for world in worlds)
    with World.open(tmp_path / cases["shared_case"]["world"]) as world:
        snapshot = world.client_snapshot(1, version=4)
    assert [message["text"] for message in snapshot["messages"]] == [
        "Static carrier 👩‍💻",
        "Second carrier 👩‍💻",
    ]
    assert snapshot["custom_emoji"] == [
        {
            "custom_emoji_id": "1",
            "fallback": "👩‍💻",
            "free": True,
            "needs_repainting": False,
            "main_asset_id": 1,
            "thumbnail_asset_id": 2,
            "duration_ms": 0,
        },
        {
            "custom_emoji_id": "2",
            "fallback": "👩‍💻",
            "free": True,
            "needs_repainting": False,
            "main_asset_id": 1,
            "thumbnail_asset_id": 2,
            "duration_ms": 0,
        },
    ]


def test_diamond_oracle_requires_complete_authored_geometry(tmp_path: Path) -> None:
    canvas = Image.new("RGB", (160, 60), "white")
    with Image.open(THUMBNAIL) as source:
        diamond = source.convert("RGBA").resize((24, 24), Image.Resampling.NEAREST)
    canvas.paste(diamond, (60, 18), diamond)
    canvas.paste(diamond, (100, 18), diamond)
    canvas.putpixel((10, 10), (88, 104, 240))
    canvas.save(tmp_path / "two.png")
    capture = {
        "png": "two.png",
        "bounds": [{"text": "Pair 👩‍💻 👩‍💻", "bounds": [0, 0, 160, 60]}],
    }
    assert _diamond_count(tmp_path, capture, "Pair") == 2
