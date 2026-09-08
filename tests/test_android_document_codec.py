"""Strict ordinary-document descriptors projected through original Android carriers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation

from gramlab.runtime import RuntimeProfile, Sandbox

sys.path.insert(0, str(Path("tests/probes").resolve()))
from android_document_codec import probe

MAX_ID = "9223372036854775807"
CASE_NAMES = (
    "numeric_ordering_and_projection",
    "empty_array",
    "identifier_boundaries",
    "identifier_rejections",
    "row_not_object",
    "missing_fields",
    "extra_field",
    "document_id_wrong_type",
    "duplicate_id",
    "out_of_order_id",
    "file_name_wrong_type",
    "file_name_empty",
    "file_name_too_long",
    "file_name_slash",
    "file_name_backslash",
    "file_name_nul",
    "file_name_high_surrogate",
    "file_name_low_surrogate",
    "mime_wrong_type",
    "mime_parameters",
    "mime_whitespace",
    "mime_missing_slash",
    "mime_non_ascii",
    "mime_too_long",
    "size_string",
    "size_float",
    "size_boolean",
    "size_negative",
    "size_zero",
    "size_above_limit",
    "sha_wrong_type",
    "sha_uppercase",
    "sha_wrong_length",
    "sha_non_hex",
)


EXPECTED_DOCUMENTS: list[dict[str, Any]] = [
    {
        "kind": "TL_document",
        "flags": 0,
        "id": "-1",
        "dc_id": -1,
        "access_hash": 0,
        "file_reference_bytes": 0,
        "date": 0,
        "mime_type": "application/pdf",
        "size": 1,
        "thumbs": 0,
        "video_thumbs": 0,
        "attributes": [{"kind": "TL_documentAttributeFilename", "file_name": "گزارش🙂.pdf"}],
        "key": "-1_-1",
        "attach_file_name": "-1_-1.pdf",
        "serialized_bytes": 92,
    },
    {
        "kind": "TL_document",
        "flags": 0,
        "id": "-2",
        "dc_id": -1,
        "access_hash": 0,
        "file_reference_bytes": 0,
        "date": 0,
        "mime_type": "",
        "size": 50000000,
        "thumbs": 0,
        "video_thumbs": 0,
        "attributes": [
            {
                "kind": "TL_documentAttributeFilename",
                "file_name": (
                    "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                    "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx🙂"
                ),
            }
        ],
        "key": "-1_-2",
        "attach_file_name": "-1_-2",
        "serialized_bytes": 148,
    },
    {
        "kind": "TL_document",
        "flags": 0,
        "id": "-10",
        "dc_id": -1,
        "access_hash": 0,
        "file_reference_bytes": 0,
        "date": 0,
        "mime_type": "application/x-tar",
        "size": 2,
        "thumbs": 0,
        "video_thumbs": 0,
        "attributes": [{"kind": "TL_documentAttributeFilename", "file_name": "archive.tar"}],
        "key": "-1_-10",
        "attach_file_name": "-1_-10.tar",
        "serialized_bytes": 88,
    },
    {
        "kind": "TL_document",
        "flags": 0,
        "id": "-2147483648",
        "dc_id": -1,
        "access_hash": 0,
        "file_reference_bytes": 0,
        "date": 0,
        "mime_type": "application/octet-stream",
        "size": 123,
        "thumbs": 0,
        "video_thumbs": 0,
        "attributes": [{"kind": "TL_documentAttributeFilename", "file_name": "sentinel.bin"}],
        "key": "-1_-2147483648",
        "attach_file_name": "-1_-2147483648.bin",
        "serialized_bytes": 100,
    },
    {
        "kind": "TL_document",
        "flags": 0,
        "id": "-9223372036854775807",
        "dc_id": -1,
        "access_hash": 0,
        "file_reference_bytes": 0,
        "date": 0,
        "mime_type": "",
        "size": 50000000,
        "thumbs": 0,
        "video_thumbs": 0,
        "attributes": [{"kind": "TL_documentAttributeFilename", "file_name": "maximum"}],
        "key": "-1_-9223372036854775807",
        "attach_file_name": "-1_-9223372036854775807",
        "serialized_bytes": 68,
    },
]


def expected_native() -> dict[str, Any]:
    return {
        "schema": 1,
        "passed": len(CASE_NAMES),
        "failed": 0,
        "total": len(CASE_NAMES),
        "custom_emoji_ids": ["2147483648", MAX_ID],
        "documents": EXPECTED_DOCUMENTS,
        "cases": [{"name": name, "passed": True} for name in CASE_NAMES],
    }


def test_patch_and_fixture_freeze_the_bounded_document_codec() -> None:
    patch = Path("clients/android/patches/0029-ordinary-document-codec.patch").read_text()
    fixture = Path("tests/fixtures/android_document_codec/DocumentCodecProbe.java").read_text()
    assert patch.count("diff --git ") == 1
    assert patch.count("GramLabDocument.java") == 3
    assert "new file mode 100644" in patch
    series = Path("clients/android/patches/series").read_text().splitlines()
    assert series[28] == "0029-ordinary-document-codec.patch"
    assert series.count("0029-ordinary-document-codec.patch") == 1
    assert "public static long identifier(Object value)" in patch
    assert "public static Map<Long, Entry> parse(JSONArray rows)" in patch
    assert "public static TLRPC.TL_document project(Entry entry)" in patch
    assert "document.id = -entry.id;" in patch
    assert "document.dc_id = -1;" in patch
    assert "document.flags = 0;" in patch
    assert "document.attributes.add(filename);" in patch
    assert "50_000_000" in patch
    assert all(
        forbidden not in patch
        for forbidden in (
            "java.io",
            "java.net",
            "android.content",
            "FileLoader",
            "ImageLocation",
            "postDelayed",
        )
    )
    assert fixture.startswith("// SPDX-License-Identifier: GPL-2.0-or-later\n")
    assert 'Class.forName("org.telegram.gramlab.GramLabDocument")' in fixture
    assert fixture.index('Class.forName("org.telegram.gramlab.GramLabDocument")') < (
        fixture.index("System.load(")
    )
    assert 'Class.forName("org.telegram.tgnet.NativeByteBuffer")' in fixture
    assert 'Class.forName("org.telegram.tgnet.TLRPC$Document")' in fixture
    assert 'Class.forName("org.telegram.messenger.ImageLocation")' in fixture
    assert 'Class.forName("org.telegram.messenger.FileLoader")' in fixture
    assert "nativeBufferConstructor.newInstance" in fixture
    assert "deserialize.invoke" in fixture
    assert 'entry.getField("id")' in fixture
    assert 'entry.getField("size")' in fixture
    assert 'entry.getField("fileName")' in fixture
    assert 'entry.getField("mimeType")' in fixture
    assert 'entry.getField("sha256")' in fixture
    assert "retained != decoded" in Path("tests/probes/android_document_codec.py").read_text()


def test_probe_collects_the_actual_app_process_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    calls: list[tuple[str, ...]] = []
    expected = expected_native()

    def guest(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        if "/system/bin/app_process" in arguments:
            return subprocess.CompletedProcess(arguments, 0, json.dumps(expected), "")
        if arguments[0] == "pull":
            retained = Path("document-codec-native")
            retained.mkdir()
            (retained / "summary.json").write_text(json.dumps(expected, indent=2))
        return subprocess.CompletedProcess(arguments, 0, "", "")

    observed = probe(guest)
    assert observed == {"returncode": 0, "result": expected}
    assert any("/system/bin/app_process" in call for call in calls)
    assert any("/work/libtmessages.49.so" in call for call in calls)
    retained = json.loads(Path("document-codec-process.json").read_text())
    assert retained == {"returncode": 0, "stdout": json.dumps(expected), "stderr": ""}
    assert json.loads(Path("document-codec-native/summary.json").read_text()) == expected


def test_probe_rejects_disagreement_between_process_and_pulled_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    expected = expected_native()

    def guest(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "/system/bin/app_process" in arguments:
            return subprocess.CompletedProcess(arguments, 0, json.dumps(expected), "")
        if arguments[0] == "pull":
            retained = Path("document-codec-native")
            retained.mkdir()
            (retained / "summary.json").write_text('{"schema": 0}')
        return subprocess.CompletedProcess(arguments, 0, "", "")

    with pytest.raises(RuntimeError, match="summary disagrees with process output"):
        probe(guest)


@pytest.mark.android
def test_actual_document_codec_uses_original_native_carriers(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    client_apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    probe_apk = os.environ.get("GRAMLAB_ANDROID_DOCUMENT_CODEC_PROBE_APK")
    if (
        manifest is None
        or client_apk is None
        or probe_apk is None
        or not os.access("/dev/kvm", os.R_OK | os.W_OK)
    ):
        pytest.skip("Requires the Android profile, reviewed client/probe APKs and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    shutil.copy2(client_apk, tmp_path / "client.apk")
    shutil.copy2(probe_apk, tmp_path / "document-codec-probe.apk")
    with zipfile.ZipFile(tmp_path / "client.apk") as archive:
        native = archive.getinfo("lib/x86_64/libtmessages.49.so")
        assert 0 < native.file_size <= 64 * 1024 * 1024
        with archive.open(native) as source, (tmp_path / "libtmessages.49.so").open("xb") as target:
            shutil.copyfileobj(source, target)
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_document_codec.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_document_codec.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    (tmp_path / "document-codec-result.json").write_text(result.stdout)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]
    assert observed["returncode"] == 0, observed
    assert observed["result"] == expected_native()
