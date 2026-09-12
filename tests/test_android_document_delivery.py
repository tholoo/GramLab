"""Original native document delivery; host controls certify only probe/oracle behavior."""

from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation

from gramlab.runtime import RuntimeProfile, Sandbox

sys.path.insert(0, str(Path("tests/probes").resolve()))
from android_document_delivery import (
    _retain_archive,
    decoded_archive,
    instrumentation_result,
    probe,
    unpack_evidence,
)

FIXTURE = Path("tests/fixtures/android_document_delivery")
BOOTSTRAP = Path("tests/probes/android_document_delivery.py").resolve()
CASE_REQUESTS: dict[str, list[tuple[str, str]]] = {
    "v5_snapshot_document_caption_keyboard": [("GET", "/v5/snapshot")],
    "v5_mixed_emoji_and_lookup": [
        ("GET", "/v5/snapshot"),
        ("POST", "/v5/custom-emoji-documents"),
    ],
    "rejected_snapshot_preserves_all_registries": [("GET", "/v5/snapshot")] * 2,
    "full_63bit_bindings": [],
    "missing_dependency_atomic": [("GET", "/v5/snapshot")],
    "mixed_carrier_atomic": [("GET", "/v5/snapshot")],
    "changed_metadata_atomic": [],
    "exact_event_dependencies": [
        ("GET", "/v5/snapshot"),
        ("GET", "/v5/changes?after=1&limit=100"),
        ("GET", "/v5/changes?after=1&limit=100"),
    ],
    "historical_callback_dependencies": [
        ("GET", "/v5/snapshot"),
        ("POST", "/v5/callbacks"),
        ("GET", "/v5/callbacks/frozen-callback"),
        ("POST", "/v5/callbacks"),
    ],
    "v4_unchanged_and_document_rejected": [("GET", "/v4/snapshot")] * 2,
    "v4_changes_callback_and_emoji": [
        ("GET", "/v4/snapshot"),
        ("GET", "/v4/changes?after=1&limit=100"),
        ("POST", "/v4/callbacks"),
        ("GET", "/v4/callbacks/v4-frozen"),
        ("POST", "/v4/custom-emoji-documents"),
    ],
    "v5_send_and_rejected_dependencies": [
        ("GET", "/v5/snapshot"),
        ("POST", "/v5/messages"),
        ("POST", "/v5/messages"),
    ],
    "world_persona_invalidation": [],
    "stale_response_epoch": [],
    "original_gif_classification": [],
    "production_document_rename": [],
    "document_entry_full_range": [
        ("GET", "/v5/documents/1"),
        ("GET", "/v5/documents/2147483648"),
        ("GET", "/v5/documents/9223372036854775807"),
    ],
    "v5_emoji_and_ordinary_namespaces": [
        ("GET", "/v5/snapshot"),
        ("GET", "/v5/assets/5"),
        ("GET", "/v5/documents/7"),
    ],
    "image_location_entry": [("GET", "/v5/documents/2147483648")],
    "unknown_reserved_ids_no_network": [],
    "encrypted_and_stream_rejected": [],
    "wrong_digest_then_retry": [("GET", "/v5/documents/1")] * 2,
    "wrong_length_then_retry": [("GET", "/v5/documents/1")] * 2,
    "truncation_then_retry": [("GET", "/v5/documents/1")] * 2,
    "wrong_mime_then_retry": [("GET", "/v5/documents/1")] * 2,
    "not_found_then_retry": [("GET", "/v5/documents/1")] * 2,
    "coalescing_cancel_retry": [("GET", "/v5/documents/1")] * 2,
    "coalesced_completion": [("GET", "/v5/documents/1")],
    "inflight_authority_change": [("GET", "/v5/documents/1")],
    "inflight_capability_rotation": [("GET", "/v5/documents/1")],
    "inflight_endpoint_rotation": [("GET", "/v5/documents/1")],
    "warm_keyed_cache": [("GET", "/v5/documents/1")],
    "cache10_exact_boundary_and_upgrade": [
        ("GET", "/v5/documents/201"),
        ("GET", "/v5/documents/202"),
    ],
    "saved_and_missing_paths": [("GET", "/v5/documents/1")],
    "presentation_collision_and_database_reopen": [
        ("GET", "/v5/snapshot"),
        ("GET", "/v5/documents/101"),
        ("GET", "/v5/documents/102"),
    ],
}
OBSERVATIONS = [
    {
        "case": "v5_snapshot_document_caption_keyboard",
        "document_id": "-1",
        "dc_id": -1,
        "caption": "Hello 🙂",
        "entity": "bold:0:5",
        "callback": "document:confirm",
    },
    {
        "case": "original_gif_classification",
        "mime_type": "image/gif",
        "is_gif": True,
        "attributes": ["filename"],
    },
    {
        "case": "production_document_rename",
        "implementation": "original_FileLoader_JNI",
        "external_root": "/storage/emulated/0/Android/data/org.gramlab.android/files",
        "root_exists": True,
        "root_is_directory": True,
        "root_can_write": True,
        "syscall": "renameat2",
        "flags": 1,
        "path_encoding": "UTF-8",
        "absent_errno": 0,
        "occupied_errno": 17,
        "invalid_errno_pairs": [[22, 22]] * 4,
        "missing_source_errno": 2,
        "unicode_errno": 0,
        "unicode_destination": ".target-ف-🚀.bin",
        "races": [{"left_errno": 0, "right_errno": 17}] * 8,
        "complete": True,
    },
    {
        "case": "presentation_collision_and_database_reopen",
        "new_names": ["same (1).bin", "same (2).bin"],
        "original_unchanged": True,
        "filesystem": "app_external_files",
    },
]


def test_fixture_initializes_android_utilities_before_native_logging() -> None:
    source = (FIXTURE / "DocumentDeliveryProbe.java").read_text()
    instrumented = source[source.index("public static JSONObject instrumented(") :]
    context = instrumented.index("ApplicationLoader.applicationContext=context;")
    utilities = instrumented.index("AndroidUtilities.getHelloWorld()")
    native = instrumented.index("NativeLoader.initNativeLibs(context)")
    assert context < utilities < native
    assert 'diagnosticStep="instrumentation.android_utilities"' in instrumented[:native]


def test_fixture_retains_a_bounded_recursive_initialization_failure() -> None:
    source = (FIXTURE / "DocumentDeliveryProbe.java").read_text()
    assert "private static JSONObject diagnosticThrowable(" in source
    assert "new IdentityHashMap<>()" in source
    assert "ExceptionInInitializerError" in source
    assert ".getException()" in source
    assert "diagnosticCause(actual)" in source
    assert "depth < 3" in source
    assert "Math.min(4,trace.length)" in source
    assert 'put("cause_cycle",true)' in source
    assert source.count("actual.getCause()") == 1


def test_fixture_initializes_the_original_file_database_without_a_latch_leak() -> None:
    source = (FIXTURE / "DocumentDeliveryProbe.java").read_text()
    setup = source[
        source.index("private static void loadSetup()") : source.index(
            "private static Result await()"
        )
    ]
    created = setup.index("loader = new FileLoader(3);")
    barrier = setup.index("databaseBarrier(loader.getFileDatabase());")
    assert created < barrier
    implementation = source[
        source.index("private static void databaseBarrier(") : source.index(
            "private static void noPartials()"
        )
    ]
    assert "AtomicReference<Throwable>" in implementation
    assert "database.ensureDatabaseCreated();" in implementation
    assert "catch(Throwable error)" in implementation
    assert "finally" in implementation
    assert "drained.countDown();" in implementation
    assert "drained.await(8,TimeUnit.SECONDS)" in implementation
    assert "throw (Exception)error;" in implementation
    assert "throw (Error)error;" in implementation


def test_fixture_retains_durable_final_case_boundaries() -> None:
    source = (FIXTURE / "DocumentDeliveryProbe.java").read_text()
    collision = source[
        source.index('run("presentation_collision_and_database_reopen"') : source.index(
            "private static void filesystemCases()"
        )
    ]
    assert "private static void diagnosticAdvance(" in source
    for stage in (
        "collision.setup_complete",
        "collision.runtime_initialized",
        "collision.external_directory",
        "collision.documents_projected",
        "collision.message_objects",
        "collision.load_submit",
        "collision.first_completion",
        "collision.second_completion",
        "collision.database_barrier",
        "collision.database_reopen",
    ):
        assert f'diagnosticAdvance("{stage}")' in collision
    assert "GramLabRuntime.initialize(ApplicationLoader.applicationContext)" in source
    assert 'require(GramLabRuntime.now()==100,"original_runtime_time")' in source
    assert 'require(Files.deleteIfExists(input.toPath()),"remove_runtime_configuration")' in source


def assert_native_suite(value: dict[str, Any], *, restart: bool = False) -> None:
    expected = {"cold_process_saved_destinations": []} if restart else CASE_REQUESTS
    assert set(value) == {
        "schema",
        "cases",
        "observations",
        "requests",
        "passed",
        "failed",
        "runtime",
    }
    runtime = value["runtime"]
    assert set(runtime) == {
        "pid",
        "uid",
        "apk_sha256",
        "native_loaded",
        "activated_accounts",
        "package",
        "application_package",
        "application_context_same",
        "attribution_package",
        "attribution_uid",
        "execution",
        "application_on_create_suppressed",
        "process_context",
        "current_application",
    }
    assert (
        runtime["package"]
        == runtime["application_package"]
        == runtime["attribution_package"]
        == "org.gramlab.android"
    )
    assert type(runtime["attribution_uid"]) is int and runtime["attribution_uid"] == runtime["uid"]
    assert runtime["execution"] == "target_instrumentation"
    assert runtime["application_on_create_suppressed"] is True
    process = runtime["process_context"]
    assert set(process) == {
        "Uid",
        "Gid",
        "Groups",
        "mount_namespace",
        "mountinfo_sha256",
        "selinux_context",
    }
    assert process["Uid"].split() == [str(runtime["uid"])] * 4
    assert process["Gid"].split() == [str(runtime["uid"])] * 4
    assert process["Groups"].split() and all(
        group.isdecimal() for group in process["Groups"].split()
    )
    assert re.fullmatch(r"mnt:\[[0-9]+\]", process["mount_namespace"])
    assert re.fullmatch(r"[0-9a-f]{64}", process["mountinfo_sha256"])
    assert process["selinux_context"].startswith("u:r:untrusted_app")
    assert runtime["application_context_same"] is True
    assert runtime["current_application"] == "org.telegram.messenger.ApplicationLoader"
    assert type(runtime["pid"]) is int and runtime["pid"] > 0
    assert type(runtime["uid"]) is int and runtime["uid"] >= 10000
    assert re.fullmatch(r"[0-9a-f]{64}", runtime["apk_sha256"])
    assert runtime["native_loaded"] is True and runtime["activated_accounts"] == 0
    assert value["schema"] == 1
    assert value["passed"] == len(expected) and value["failed"] == 0
    assert value["cases"] == [{"name": name, "status": "passed"} for name in expected]
    observations = copy.deepcopy(value["observations"])
    if not restart:
        assert len(observations) == len(OBSERVATIONS)
        races = observations[2]["races"]
        assert isinstance(races, list) and len(races) == 8
        for race in races:
            assert set(race) == {"left_errno", "right_errno"}
            assert all(type(code) is int for code in race.values())
            assert (race["left_errno"], race["right_errno"]) in ((0, 17), (17, 0))
        observations[2]["races"] = OBSERVATIONS[2]["races"]
    assert observations == ([] if restart else OBSERVATIONS)
    actual: dict[str, list[tuple[str, str]]] = {name: [] for name in expected}
    order = {name: index for index, name in enumerate(expected)}
    last = -1
    for row in value["requests"]:
        assert set(row) == {"case", "method", "path", "authorized"}
        assert row["authorized"] is True
        assert row["case"] in expected
        index = order[row["case"]]
        assert index >= last
        last = index
        actual[row["case"]].append((row["method"], row["path"]))
    # The two independently queued equal-name downloads may reach the peer in either order.
    collision = "presentation_collision_and_database_reopen"
    if collision in actual:
        actual[collision][1:] = sorted(actual[collision][1:])
    assert actual == expected


def _transcript(*, restart: bool = False) -> dict[str, Any]:
    """Independently authored oracle input, never a claimed native recording."""
    expected = {"cold_process_saved_destinations": []} if restart else CASE_REQUESTS
    return {
        "schema": 1,
        "cases": [{"name": name, "status": "passed"} for name in expected],
        "observations": [] if restart else copy.deepcopy(OBSERVATIONS),
        "requests": [
            {"case": name, "method": method, "path": path, "authorized": True}
            for name, calls in expected.items()
            for method, path in calls
        ],
        "passed": len(expected),
        "failed": 0,
        "runtime": {
            "pid": 102 if restart else 101,
            "uid": 10001,
            "apk_sha256": "a" * 64,
            "native_loaded": True,
            "activated_accounts": 0,
            "package": "org.gramlab.android",
            "application_package": "org.gramlab.android",
            "application_context_same": True,
            "attribution_package": "org.gramlab.android",
            "attribution_uid": 10001,
            "execution": "target_instrumentation",
            "application_on_create_suppressed": True,
            "process_context": {
                "Uid": "10001 10001 10001 10001",
                "Gid": "10001 10001 10001 10001",
                "Groups": "10001 20001",
                "mount_namespace": "mnt:[123]",
                "mountinfo_sha256": "b" * 64,
                "selinux_context": "u:r:untrusted_app:s0:c1",
            },
            "current_application": "org.telegram.messenger.ApplicationLoader",
        },
    }


def _archive(path: Path, values: list[tuple[str, bytes | str]]) -> None:
    with tarfile.open(path, "w:gz") as target:
        for name, payload in values:
            member = tarfile.TarInfo(name)
            if isinstance(payload, str):
                member.type = tarfile.SYMTYPE
                member.linkname = payload
                target.addfile(member)
            else:
                member.size = len(payload)
                target.addfile(member, io.BytesIO(payload))


def test_oracle_accepts_both_actual_orderings_of_concurrent_requests() -> None:
    value = _transcript()
    assert_native_suite(value)
    value["requests"][-2:] = reversed(value["requests"][-2:])
    assert_native_suite(value)
    assert_native_suite(_transcript(restart=True), restart=True)


def test_production_rename_oracle_accepts_either_single_winner() -> None:
    value = _transcript()
    value["observations"][2]["races"][3] = {"left_errno": 17, "right_errno": 0}
    assert_native_suite(value)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("implementation", "fixture_syscall"),
        ("occupied_errno", 0),
        ("unicode_errno", 2),
        ("complete", False),
        ("races", [{"left_errno": 0, "right_errno": 0}] * 8),
        ("races", [{"left_errno": 17, "right_errno": 17}] * 8),
        ("races", [{"left_errno": 0, "right_errno": 17}] * 7),
    ],
)
def test_production_rename_oracle_rejects_weakened_capability(field: str, bad: Any) -> None:
    value = _transcript()
    value["observations"][2][field] = bad
    with pytest.raises(AssertionError):
        assert_native_suite(value)


@pytest.mark.parametrize(
    "fault",
    ["missing_case", "failure", "wrong_id", "extra_request", "unauthorized", "gif_rewritten"],
)
def test_oracle_rejects_semantic_and_transport_regressions(fault: str) -> None:
    value = _transcript()
    if fault == "missing_case":
        value["cases"].pop()
    elif fault == "failure":
        value["cases"][0]["status"] = "failed"
    elif fault == "wrong_id":
        value["requests"][-1]["path"] = "/v5/assets/102"
    elif fault == "extra_request":
        value["requests"].append(copy.deepcopy(value["requests"][-1]))
    elif fault == "unauthorized":
        value["requests"][0]["authorized"] = False
    else:
        value["observations"][1]["mime_type"] = "application/octet-stream"
    with pytest.raises(AssertionError):
        assert_native_suite(value)


@pytest.mark.parametrize(
    "values",
    [
        [("../outside", b"bad")],
        [("/absolute", b"bad")],
        [("document-delivery-probe/a", "../../outside")],
        [("unrelated/value", b"bad")],
        [("document-delivery-probe/a", b"a"), ("document-delivery-probe/a", b"b")],
        [("document-delivery-probe/a", b"gramlab-client_" + b"d" * 43)],
        [("document-delivery-probe/a", b"a"), ("document-delivery-probe//a", b"b")],
        [("document-delivery-probe/a", b"a"), ("document-delivery-probe/a/child", b"b")],
    ],
)
def test_native_archive_rejects_unsafe_or_secret_evidence(
    tmp_path: Path, values: list[tuple[str, bytes | str]]
) -> None:
    archive = tmp_path / "native.tar.gz"
    _archive(archive, values)
    destination = tmp_path / "unpacked"
    with pytest.raises(ValueError):
        unpack_evidence(archive, destination)
    assert not destination.exists()


def test_archive_bounds_expansion_before_publication(tmp_path: Path) -> None:
    archive = tmp_path / "native.tar.gz"
    archive.write_bytes(gzip.compress(b"\0" * (16 * 1024 * 1024 + 1)))
    with pytest.raises(ValueError, match="expanded bound"):
        unpack_evidence(archive, tmp_path / "unpacked")
    assert not (tmp_path / "unpacked").exists()


def test_archive_retains_original_unicode_paths_and_bytes(tmp_path: Path) -> None:
    archive = tmp_path / "native.tar.gz"
    payload = b"\x00original\xff"
    _archive(archive, [("document-delivery-probe/files/گزارش.pdf", payload)])
    unpack_evidence(archive, tmp_path / "unpacked")
    assert (tmp_path / "unpacked/document-delivery-probe/files/گزارش.pdf").read_bytes() == payload


def test_app_owned_archive_commands_run_with_real_posix_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    guest_root = tmp_path / "guest"
    evidence = guest_root / "files/document-delivery-diagnostics"
    evidence.mkdir(parents=True)
    payload = b'{"schema":1,"event":"case_start","phase":"original_case"}'
    (evidence / "suite-123-event-001.json").write_bytes(payload)
    calls: list[list[str]] = []

    def guest(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert args[:2] == ("shell", "-T") and kwargs == {"timeout": 30}
        command = shlex.split(args[2])
        assert command[:4] == ["run-as", "org.gramlab.android", "sh", "-c"]
        calls.append(command)
        # Real POSIX archive/encoding tools; host permissions do not certify Android run-as.
        return subprocess.run(  # noqa: S603 — reviewed probe shell in an isolated host directory.
            command[2:], cwd=guest_root, capture_output=True, text=True, timeout=30
        )

    _retain_archive(guest)
    assert len(calls) == 2
    assert "head -c 4194305" in calls[1][-1]
    assert (
        tmp_path / "document-delivery-native/document-delivery-diagnostics/suite-123-event-001.json"
    ).read_bytes() == payload
    assert json.loads(Path("document-delivery-archive-status.json").read_text())["returncode"] == 0
    pulled = json.loads(Path("document-delivery-pull-status.json").read_text())
    encoded = base64.encodebytes(Path("native.tar.gz").read_bytes())
    assert pulled["returncode"] == 0 and "stdout" not in pulled
    assert pulled["stdout_encoded_bytes"] == len(encoded)
    assert pulled["stdout_sha256"] == hashlib.sha256(encoded).hexdigest()


def test_encoded_archive_retains_exact_diagnostic_bytes(tmp_path: Path) -> None:
    archive = tmp_path / "transport.tar.gz"
    payload = b'{"schema":1,"phase":"initialization","threads":[]}'
    _archive(archive, [("document-delivery-diagnostics/suite-123-event-001.json", payload)])
    original = archive.read_bytes()
    assert decoded_archive(base64.encodebytes(original).decode()) == original
    unpack_evidence(archive, tmp_path / "retained")
    assert (
        tmp_path / "retained/document-delivery-diagnostics/suite-123-event-001.json"
    ).read_bytes() == payload


@pytest.mark.parametrize("encoded", ["not!base64", "YQ", "YQ==Yg==", "é"])
def test_encoded_archive_rejects_malformed_framing(encoded: str) -> None:
    with pytest.raises(ValueError):
        decoded_archive(encoded)


def test_encoded_archive_rejects_byte_and_encoded_overflow() -> None:
    with pytest.raises(ValueError, match="compressed bound"):
        decoded_archive(base64.b64encode(b"x" * (4 * 1024 * 1024 + 1)).decode())
    with pytest.raises(ValueError, match="encoded bound"):
        decoded_archive("A" * (6 * 1024 * 1024))


@pytest.mark.parametrize("archive_throws", [False, True])
def test_probe_timeout_retains_original_failure_and_archive_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, archive_throws: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    secret = "gramlab-client_" + "d" * 43
    original = subprocess.TimeoutExpired(
        "am instrument", 240, output=b"partial status", stderr=secret.encode()
    )
    retention = subprocess.TimeoutExpired(
        "tar", 30, output=b"partial archive", stderr=b"archive timeout"
    )

    def guest(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        joined = " ".join(args)
        if "am instrument" in joined:
            raise original
        if "tar " in joined:
            if archive_throws:
                raise retention
            return subprocess.CompletedProcess(
                args, 1, "partial archive", "permission denied " + secret
            )
        if args[0] == "pull" or "base64" in joined:
            return subprocess.CompletedProcess(args, 2, "", "archive unavailable")
        return subprocess.CompletedProcess(args, 0, "", "")

    with pytest.raises(subprocess.TimeoutExpired) as caught:
        probe(guest)
    assert caught.value is original
    process = json.loads(Path("document-delivery-suite-process.json").read_text())
    assert process["exception"] == "TimeoutExpired" and process["timeout"] == 240
    assert process["stdout"] == "partial status" and process["stderr"] == "[REDACTED]"
    packed = json.loads(Path("document-delivery-archive-status.json").read_text())
    assert packed["stdout"] == "partial archive"
    assert packed["stderr"] == (
        "archive timeout" if archive_throws else "permission denied [REDACTED]"
    )
    assert secret not in "".join(path.read_text() for path in tmp_path.glob("*.json"))


def test_probe_retains_crash_buffer_and_exit_reason_before_rejecting_framing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    calls: list[tuple[str, ...]] = []
    secret = "gramlab-client_" + "d" * 43

    def guest(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        joined = " ".join(args)
        if "am instrument" in joined:
            return subprocess.CompletedProcess(
                args,
                0,
                "INSTRUMENTATION_RESULT: shortMsg=Process crashed.\nINSTRUMENTATION_CODE: 0\n",
                "",
            )
        if "logcat -b crash" in joined:
            return subprocess.CompletedProcess(args, 0, f"fatal {secret}", "")
        if "dumpsys activity exit-info" in joined:
            return subprocess.CompletedProcess(args, 0, "REASON_CRASH_NATIVE status=11", "")
        if "base64" in joined:
            _archive(
                Path("transport.tar.gz"),
                [("document-delivery-diagnostics/suite-1-event-001.json", b"{}")],
            )
            return subprocess.CompletedProcess(
                args, 0, base64.encodebytes(Path("transport.tar.gz").read_bytes()).decode(), ""
            )
        return subprocess.CompletedProcess(args, 0, "", "")

    with pytest.raises(ValueError, match="Malformed instrumentation result framing"):
        probe(guest)
    crash = json.loads(Path("document-delivery-suite-crash-log.json").read_text())
    exit_info = json.loads(Path("document-delivery-suite-exit-info.json").read_text())
    assert crash["stdout"] == "fatal [REDACTED]"
    assert exit_info["stdout"] == "REASON_CRASH_NATIVE status=11"
    crash_call = next(i for i, call in enumerate(calls) if "logcat -b crash" in " ".join(call))
    archive_call = next(i for i, call in enumerate(calls) if "tar -czf" in " ".join(call))
    assert crash_call < archive_call


@pytest.mark.parametrize("disagree", [False, True])
@pytest.mark.parametrize("failure_code", [0, 1])
def test_probe_uses_target_processes_and_checks_retained_summaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, disagree: bool, failure_code: int
) -> None:
    monkeypatch.chdir(tmp_path)
    calls: list[tuple[str, ...]] = []
    suite, restart = _transcript(), _transcript(restart=True)
    if failure_code:
        suite["cases"][0]["status"] = "failed"
        suite["failed"] = 1
        suite["passed"] -= 1

    def guest(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if "am instrument" in " ".join(args):
            value = restart if "-e mode restart " in args[-1] else suite
            framed = (
                "INSTRUMENTATION_RESULT: document_delivery="
                + json.dumps(value)
                + f"\nINSTRUMENTATION_CODE: {failure_code}\n"
            )
            return subprocess.CompletedProcess(args, 0, framed, "")
        if "base64" in args[-1]:
            retained_suite = {"schema": 0} if disagree else suite
            _archive(
                Path("transport.tar.gz"),
                [
                    (
                        "document-delivery-probe/suite-summary.json",
                        json.dumps(retained_suite).encode(),
                    ),
                    ("document-delivery-probe/restart-summary.json", json.dumps(restart).encode()),
                ],
            )
            return subprocess.CompletedProcess(
                args, 0, base64.encodebytes(Path("transport.tar.gz").read_bytes()).decode(), ""
            )
        return subprocess.CompletedProcess(args, 0, "", "")

    if disagree:
        with pytest.raises(RuntimeError, match="disagrees"):
            probe(guest)
    else:
        value = probe(guest)
        expected = {
            "suite": {"returncode": 0, "instrumentation_code": failure_code, "result": suite}
        }
        if not failure_code:
            expected["restart"] = {"returncode": 0, "instrumentation_code": 0, "result": restart}
        assert value["processes"] == expected
        assert value["bootstrap_sha256"] == hashlib.sha256(BOOTSTRAP.read_bytes()).hexdigest()
    native_calls = [call for call in calls if "am instrument" in " ".join(call)]
    assert len(native_calls) == (1 if failure_code else 2)
    assert "-e mode suite " in native_calls[0][-1]
    if not failure_code:
        assert "-e mode restart " in native_calls[1][-1]
    assert all(call[:2] == ("shell", "-T") and "run-as" not in call[-1] for call in native_calls)
    assert ("install", "-t", "-r", "/work/document-delivery-probe.apk") in calls
    assert not any("native_init" in " ".join(call) for call in calls)


@pytest.mark.parametrize(
    "framed",
    [
        "INSTRUMENTATION_RESULT: document_delivery={}\n",
        "INSTRUMENTATION_RESULT: document_delivery={}\nINSTRUMENTATION_CODE: 0\nextra\n",
        "INSTRUMENTATION_RESULT: document_delivery={}\nINSTRUMENTATION_CODE: -1\n",
        "INSTRUMENTATION_RESULT: document_delivery=[]\nINSTRUMENTATION_CODE: 0\n",
        "INSTRUMENTATION_RESULT: document_delivery={oops}\nINSTRUMENTATION_CODE: 0\n",
    ],
)
def test_instrumentation_result_rejects_incomplete_or_unrelated_frames(framed: str) -> None:
    with pytest.raises(ValueError):
        instrumentation_result(framed)


def test_instrumentation_failure_code_is_preserved() -> None:
    assert instrumentation_result(
        'INSTRUMENTATION_RESULT: document_delivery={"failed":1}\nINSTRUMENTATION_CODE: 1\n'
    ) == (1, {"failed": 1})


@pytest.mark.android
def test_actual_document_bridge_loader_and_cold_process_cache(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    client_apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    probe_apk = os.environ.get("GRAMLAB_ANDROID_DOCUMENT_DELIVERY_PROBE_APK")
    inputs = os.environ.get("GRAMLAB_ANDROID_DOCUMENT_DELIVERY_PROBE_INPUTS")
    if not all((manifest, client_apk, probe_apk, inputs)) or not os.access(
        "/dev/kvm", os.R_OK | os.W_OK
    ):
        pytest.skip("Requires reviewed native delivery probe, APK, inputs, Android profile and KVM")
    assert manifest is not None and client_apk is not None and probe_apk is not None
    assert inputs is not None
    metadata = json.loads(Path(inputs).read_text())
    for name, path in {
        "source": FIXTURE / "DocumentDeliveryProbe.java",
        "compile_script": FIXTURE / "compile.sh",
        "instrumentation_source": FIXTURE / "DocumentDeliveryInstrumentation.java",
        "rename_java": FIXTURE / "RenameNoReplaceProbe.java",
        "rename_c": FIXTURE / "RenameNoReplaceProbe.c",
        "instrumentation_manifest": FIXTURE / "AndroidManifest.xml",
        "instrumentation_compile_script": FIXTURE / "compile-instrumentation.sh",
        "probe_apk": Path(probe_apk),
    }.items():
        assert metadata["files"][name]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert metadata["execution"] == "target_instrumentation"
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["signer_certificate_sha256"])
    profile = RuntimeProfile.load(Path(manifest))
    shutil.copy2(client_apk, tmp_path / "client.apk")
    shutil.copy2(probe_apk, tmp_path / "document-delivery-probe.apk")
    shutil.copy2("tests/assets/custom-emoji/emoji-static.webp", tmp_path / "emoji-static.webp")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_document_delivery.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    staged = {
        name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
        for name in ("client.apk", "document-delivery-probe.apk", "emoji-static.webp")
    }
    (tmp_path / "delivery-inputs.json").write_text(json.dumps(staged, indent=2) + "\n")
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_document_delivery.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image,
        ],
        data=tmp_path,
        kvm=True,
        timeout=600,
    )
    (tmp_path / "document-delivery-result.json").write_text(result.stdout)
    (tmp_path / "document-delivery-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]
    assert observed["bootstrap_sha256"] == hashlib.sha256(BOOTSTRAP.read_bytes()).hexdigest()
    assert (
        observed["archive_sha256"]
        == hashlib.sha256((tmp_path / "native.tar.gz").read_bytes()).hexdigest()
    )
    assert set(observed["processes"]) == {"suite", "restart"}
    for mode in ("suite", "restart"):
        assert observed["processes"][mode]["returncode"] == 0
        assert observed["processes"][mode]["instrumentation_code"] == 0
        assert_native_suite(observed["processes"][mode]["result"], restart=mode == "restart")
        assert (
            observed["processes"][mode]["result"]["runtime"]["apk_sha256"] == staged["client.apk"]
        )
    initial = observed["processes"]["suite"]["result"]["runtime"]
    restarted = observed["processes"]["restart"]["result"]["runtime"]
    assert initial["pid"] != restarted["pid"] and initial["uid"] == restarted["uid"]
