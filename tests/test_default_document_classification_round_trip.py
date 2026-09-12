"""Contained real-bot acceptance for default document classification."""

import hashlib
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from gramlab.runtime import RuntimeProfile, Sandbox


def stage_scenario(directory: Path, core: RuntimeProfile) -> None:
    shutil.copytree(
        "src/gramlab", directory / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (directory / "component-profile.json").write_text(json.dumps(asdict(core)))
    shutil.copy2(Path("tests/probes/component_bot.py"), directory / "component_bot.py")
    shutil.copy2(
        Path("tests/probes/default_document_classification_round_trip.py"),
        directory / "default_document_classification_round_trip.py",
    )
    shutil.copy2(
        Path("tests/fixtures/default_document_classification_bot.py"),
        directory / "default_document_classification_bot.py",
    )


def assert_scenario(observed: dict[str, Any]) -> None:
    ordinary_response = observed["bot"]["ordinary"]
    assert ordinary_response["status"] == 200
    digest = hashlib.sha256(b"contained ordinary text document").hexdigest()
    identity = json.dumps(
        ["document", digest, "ordinary.txt", "text/plain"],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    document = ordinary_response["body"]["result"]["document"]
    assert document["file_id"].startswith("gramlab_document_")
    expected_document = {
        "file_id": document["file_id"],
        "file_unique_id": "gramlab_document_unique_" + hashlib.sha256(identity).hexdigest(),
        "file_size": 32,
        "file_name": "ordinary.txt",
        "mime_type": "text/plain",
    }
    assert ordinary_response["body"] == {
        "ok": True,
        "result": {
            "message_id": 1,
            "from": {
                "id": 2,
                "is_bot": True,
                "first_name": "Files",
                "username": "gramlab_files_bot",
            },
            "chat": {"id": 1, "type": "private", "first_name": "Sara"},
            "date": 1_700_000_000,
            "document": expected_document,
        },
    }
    assert observed["bot"]["specialized"] == {
        "status": 400,
        "body": {
            "ok": False,
            "error_code": 400,
            "description": "GRAMLAB_UNSUPPORTED: default document content classification",
        },
    }
    assert observed["history"] == [
        {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1_700_000_000,
            "text": "",
            "document": {"document_id": "1"},
        }
    ]
    assert observed["descriptor"] == {
        "document_id": "1",
        "file_name": "ordinary.txt",
        "mime_type": "text/plain",
        "file_size": 32,
        "sha256": digest,
    }
    assert observed["stored_sha256"] == observed["ordinary_sha256"] == digest
    assert [event["type"] for event in observed["events"]] == [
        "user.created",
        "user.created",
        "chat.created",
        "message.created",
    ]


def test_contained_real_bot_admits_ordinary_and_rejects_specialized_document(
    tmp_path: Path,
) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    stage_scenario(tmp_path, profile)
    result = Sandbox(profile).supervise(
        [profile.python, "/work/default_document_classification_round_trip.py"],
        data=tmp_path,
        timeout=40,
    )
    (tmp_path / "default-document-classification-result.json").write_text(result.stdout)
    (tmp_path / "default-document-classification-stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert_scenario(json.loads(result.stdout))
