"""Public runner version selection for ordinary document scenarios."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_android_rich_button_host import ExternalGuest

from gramlab import __main__ as cli
from gramlab._android import (
    Android,
    _android_file_size,
    _document_accessibility_header,
    _inline_fragments,
    _inline_matches,
)
from gramlab._interactions import Interactions
from gramlab.documents import DocumentUpload
from gramlab.runner import run
from gramlab.runtime import RuntimeProfile
from gramlab.world import World

ASSETS = Path(__file__).parent / "assets"
DOCUMENT = (
    b"%PDF-1.4\n% GramLab runner document\n"
    b"Persian-English filename; exact local bytes.\x00\xff\n%%EOF\n"
)
SCENE: dict[str, Any] = {
    "request_text": "Send the forced document / فایل را بفرست",
    "file_name": "گزارش-English.pdf",
    "upload_name": "%DA%AF%D8%B2%D8%A7%D8%B1%D8%B4-English.pdf",
    "caption": "فایل Report 👩‍💻",
    "caption_entities": [
        {"type": "bold", "offset": 5, "length": 6},
        {"type": "custom_emoji", "offset": 12, "length": 5, "custom_emoji_id": "1109"},
    ],
    "button_text": "Reuse / استفاده دوباره",
    "callback_data": "document:reuse",
    "answer_text": "دریافت شد / Received",
    "reuse_caption": "Same file / همان فایل",
}

BOT = r"""import hashlib
import http.client
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

if Path("/work/world").exists() or Path("/proc/1/root/work/world").exists():
    raise RuntimeError("Bot can see the authoritative World")
endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
token = os.environ["GRAMLAB_BOT_TOKEN"]
scene = json.loads(Path("scene.json").read_text())
payload = Path("ordinary-document.bin").read_bytes()

def call(method, parameters, *, upload=None):
    headers = {}
    if upload is None:
        body = json.dumps(parameters, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    else:
        boundary = "gramlab-document-runner-v5"
        chunks = []
        for name, value in parameters.items():
            encoded = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value)
            )
            chunks.append(
                (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
                 f'\r\n\r\n{encoded}\r\n').encode()
            )
        chunks.append(
            (f'--{boundary}\r\nContent-Disposition: form-data; name="upload"; '
             f'filename="{scene["upload_name"]}"\r\n'
             'Content-Type: application/octet-stream\r\n\r\n').encode()
            + upload + b"\r\n"
        )
        chunks.append(f"--{boundary}--\r\n".encode())
        body = b"".join(chunks)
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
    try:
        connection.request("POST", f"/bot{token}/{method}", body, headers)
        response = connection.getresponse()
        result = {"status": response.status, "body": json.loads(response.read())}
    finally:
        connection.close()
    if result["status"] != 200 or result["body"].get("ok") is not True:
        raise RuntimeError("Bot API request failed: " + method)
    return result["body"]["result"]

deadline = time.monotonic() + 15
updates = []
while not updates and time.monotonic() < deadline:
    updates = call("getUpdates", {"timeout": 10})
if len(updates) != 1 or updates[0]["message"]["text"] != scene["request_text"]:
    raise RuntimeError("Expected one document request")
chat = updates[0]["message"]["chat"]["id"]
keyboard = {
    "inline_keyboard": [[{
        "text": scene["button_text"], "callback_data": scene["callback_data"]
    }]]
}
sent = call("sendDocument", {
    "chat_id": chat,
    "document": "attach://upload",
    "disable_content_type_detection": True,
    "caption": scene["caption"],
    "caption_entities": scene["caption_entities"],
    "reply_markup": keyboard,
}, upload=payload)
file_id = sent["document"]["file_id"]
first = call("getFile", {"file_id": file_id})
second = call("getFile", {"file_id": file_id})
if first != second:
    raise RuntimeError("Repeated getFile changed the document path")
connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=15)
try:
    connection.request("GET", f"/file/bot{token}/{first['file_path']}")
    response = connection.getresponse()
    downloaded = response.read()
    download = {
        "status": response.status,
        "content_type": response.getheader("Content-Type"),
        "content_length": response.getheader("Content-Length"),
        "cache_control": response.getheader("Cache-Control"),
        "sha256": hashlib.sha256(downloaded).hexdigest(),
        "size": len(downloaded),
    }
finally:
    connection.close()
if response.status != 200 or downloaded != payload:
    raise RuntimeError("Downloaded document differs from upload")
print(json.dumps(
    {"event": "published", "sent": sent, "get_file": first, "download": download},
    ensure_ascii=False,
), flush=True)

offset = updates[0]["update_id"] + 1
# A native scenario may capture and relaunch the original client before tapping.
# Keep the bot's long-poll lifetime inside the runner timeout instead of racing
# that trusted Android orchestration.
deadline = time.monotonic() + 180
while time.monotonic() < deadline:
    incoming = call("getUpdates", {"offset": offset, "timeout": 10})
    if not incoming:
        continue
    if (
        len(incoming) != 1
        or incoming[0].get("callback_query", {}).get("data") != scene["callback_data"]
    ):
        raise RuntimeError("Expected one document callback")
    callback = incoming[0]["callback_query"]
    if callback["message"] != sent:
        raise RuntimeError("Document callback lost its original message")
    answer = call("answerCallbackQuery", {
        "callback_query_id": callback["id"], "text": scene["answer_text"]
    })
    reused = call("sendDocument", {
        "chat_id": chat, "document": file_id, "caption": scene["reuse_caption"]
    })
    print(json.dumps(
        {"event": "callback", "update": incoming[0], "answer": answer, "reused": reused},
        ensure_ascii=False,
    ), flush=True)
    break
else:
    raise RuntimeError("Document callback did not arrive")
"""

SCENARIO = r"""import json
import time
from pathlib import Path
from gramlab.scenario import Scenario

scene = json.loads(Path("scene.json").read_text())
lab = Scenario.from_environment()
lab.register_custom_emoji(
    request_id="document-caption",
    custom_emoji_id="1109",
    main=Path("emoji-static.webp").read_bytes(),
    thumbnail=Path("emoji-thumbnail.webp").read_bytes(),
    fallback="👩‍💻",
)
user = lab.create_user(first_name="Sara", language_code="fa")
bot = lab.bots()["files"]
chat = lab.open_private_chat(user_id=user["id"], bot_id=bot)
request = lab.send_message(chat_id=chat["id"], sender_id=user["id"], text=scene["request_text"])
deadline = time.monotonic() + 15
while len(lab.history(chat["id"])) != 2:
    assert time.monotonic() < deadline, "Document was not published"
    time.sleep(0.02)
message = lab.history(chat["id"])[1]
assert message == {
    "id": 2,
    "chat_id": chat["id"],
    "sender_id": bot,
    "date": 1700000000,
    "text": "",
    "reply_markup": {"inline_keyboard": [[{
        "text": scene["button_text"], "callback_data": scene["callback_data"]
    }]]},
    "document": {"document_id": "1"},
    "caption": scene["caption"],
    "caption_entities": scene["caption_entities"],
}
capture = lab.capture_chat(
    chat_id=chat["id"], label="ordinary-document", contains=[scene["caption"]]
)
before = lab.events()
interaction = lab.tap_inline_button(
    chat_id=chat["id"], message_id=message["id"], row=0, column=0
)
callback = interaction["callback"]
assert callback["message"] == message and callback["data"] == scene["callback_data"]
deadline = time.monotonic() + 15
while (
    len(lab.history(chat["id"])) != 3
    or lab.get_callback(user_id=user["id"], callback_id=callback["id"])["answer"] is None
):
    assert time.monotonic() < deadline, "Document callback did not complete"
    time.sleep(0.02)
answer = lab.get_callback(user_id=user["id"], callback_id=callback["id"])["answer"]
assert answer["text"] == scene["answer_text"]
assert lab.events()[:len(before)] == before
reused_capture = lab.capture_chat(
    chat_id=chat["id"], label="ordinary-document-reused", contains=[scene["reuse_caption"]]
)
print(json.dumps(
    {
        "request": request,
        "message": message,
        "capture": capture,
        "callback": callback,
        "answer": answer,
        "reused_capture": reused_capture,
    },
    ensure_ascii=False,
))
"""


class VersionedGuest(ExternalGuest):
    """External native boundary that publishes a callback at the selected bridge version."""

    def touch(self, *arguments: str, **_keywords: Any) -> None:
        if "callback_data" not in self.selected_button:
            super().touch(*arguments, **_keywords)
            return
        assert arguments[:3] == ("shell", "input", "tap")
        self.touches += 1
        assert self.touches == 1
        effect = self.files["rich-button-effect.json"]
        effect.update(
            generation=7,
            uptime_ms=10001,
            state="complete",
            touch={"down_uptime_ms": 10000, "up_uptime_ms": 10001, "path": effect["path"]},
        )
        with World.open(Path("world")) as world:
            callback = world.create_callback(
                user_id=effect["user_id"],
                chat_id=effect["chat_id"],
                message_id=effect["message_id"],
                data=self.selected_button["callback_data"],
                request_id="http-exact-v5",
                version=self.android._bridge_version,
            )
        effect.update(
            action="callback",
            clipboard=None,
            requests=[
                {
                    "native_request_token": 19,
                    "request_id": "http-exact-v5",
                    "callback_id": callback["id"],
                    "message_revision": effect["revision"],
                }
            ],
        )
        self.now = 10010
        if self.after_touch is not None:
            self.after_touch(effect)


def mixed_rich_guest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    version: int,
    kind: str,
) -> tuple[VersionedGuest, dict[str, Any], dict[str, Any], dict[str, Any]]:
    monkeypatch.chdir(tmp_path)
    main = (ASSETS / "custom-emoji/emoji-static.webp").read_bytes()
    thumbnail = (ASSETS / "custom-emoji/emoji-thumbnail.webp").read_bytes()
    photo_bytes = (ASSETS / "rich-media/photo-square-16x16.png").read_bytes()
    with World.create(Path("world"), seed=107, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara", language_code="fa")
        bot = world.create_user(first_name="Files", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        world.register_custom_emoji(
            request_id="mixed",
            custom_emoji_id=1109,
            main=main,
            thumbnail=thumbnail,
            fallback="👩‍💻",
        )
        emoji = world.send_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            text="Emoji 👩‍💻",
            entities=[
                {
                    "type": "custom_emoji",
                    "offset": 6,
                    "length": 5,
                    "custom_emoji_id": "1109",
                }
            ],
        )
        photo = world.send_photo(
            chat_id=chat["id"],
            sender_id=bot["id"],
            photo={"type": "photo", "media": "attach://photo"},
            uploads={"photo": photo_bytes},
            caption="Photo / تصویر",
        )
        document = None
        if version == 5:
            document = world.send_document(
                chat_id=chat["id"],
                sender_id=bot["id"],
                document={"media": "attach://document"},
                uploads={"document": DocumentUpload(b"mixed document", "mixed.pdf")},
                caption="Document / فایل",
            )
        action: dict[str, Any] = (
            {"callback_data": "mixed:callback"}
            if kind == "callback"
            else ({"copy_text": {"text": "برداشت / copy"}} if kind == "copy" else {"disabled": {}})
        )
        target = world.send_rich_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            rich_message={
                "skip_entity_detection": True,
                "blocks": [{"type": "buttons", "buttons": [{"text": "Same", **action}]}],
            },
        )
        snapshot = world.client_snapshot(user["id"], version=version)
        revision = next(
            item["revision"]
            for item in snapshot["message_revisions"]
            if item["message_id"] == target["id"]
        )
        record = {"chat": chat, "message": target, "revision": revision}
        world_id = world.world_id

    expected_messages = [emoji, photo, *([document] if document is not None else []), target]
    assert snapshot == {
        "schema": version,
        "world_id": world_id,
        "user_id": user["id"],
        "cursor": revision,
        "now": 1_700_000_000,
        "users": [user, bot],
        "chats": [chat],
        "messages": expected_messages,
        "message_revisions": [
            {"chat_id": 1, "message_id": index, "revision": index + 3}
            for index in range(1, len(expected_messages) + 1)
        ],
        "sends": [],
        "message_position": len(expected_messages),
        "assets": [
            {
                "asset_id": asset_id,
                "mime_type": mime_type,
                "file_size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "width": size,
                "height": size,
            }
            for asset_id, mime_type, data, size in (
                (1, "image/webp", main, 100),
                (2, "image/webp", thumbnail, 16),
                (3, "image/png", photo_bytes, 16),
            )
        ],
        "custom_emoji": [
            {
                "custom_emoji_id": "1109",
                "fallback": "👩‍💻",
                "free": True,
                "needs_repainting": False,
                "main_asset_id": 1,
                "thumbnail_asset_id": 2,
                "duration_ms": 0,
            }
        ],
        **(
            {
                "documents": [
                    {
                        "document_id": "1",
                        "file_name": "mixed.pdf",
                        "mime_type": "application/pdf",
                        "file_size": len(b"mixed document"),
                        "sha256": hashlib.sha256(b"mixed document").hexdigest(),
                    }
                ]
            }
            if version == 5
            else {}
        ),
    }
    android = Android(profile(), deadline=time.monotonic() + 5, secrets=[], bridge_version=version)
    guest = VersionedGuest(android, record, world_id)
    monkeypatch.setattr(android, "_open_chat", guest.launch)
    monkeypatch.setattr(android, "_adb", guest.touch)
    nonce = guest.observe(record)
    receipt: dict[str, Any] = {
        "operation_id": f"operation-{version}-{kind}",
        "target": {
            "target_id": "target-one",
            "chat_id": chat["id"],
            "message_id": target["id"],
            "message_revision": revision,
            "path": copy.deepcopy(guest.selected_path),
            "button": copy.deepcopy(guest.selected_button),
            "label": "Same",
        },
        "status": "in_progress",
        "dispatch": "not_dispatched",
        "effect": None,
        "reason": None,
        "evidence": {
            "mode": "headless-android",
            "world_event_sequences": [],
            "clipboard_observation": None,
            "native": {"observation": None, "effect": None, "captures": []},
        },
    }
    assert nonce == "process-original"
    return guest, receipt, snapshot, record


def profile() -> RuntimeProfile:
    return RuntimeProfile(bubblewrap="", python="", store_paths=())


def require_android() -> tuple[Path, Path, Path]:
    runtime = os.environ.get("GRAMLAB_RUNTIME_PROFILE")
    android = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if (
        runtime is None
        or android is None
        or apk is None
        or not os.access("/dev/kvm", os.R_OK | os.W_OK)
    ):
        pytest.skip("Requires provisioned runtime profiles, reviewed Android APK and KVM")
    return Path(runtime), Path(android), Path(apk)


def stage_public_scenario(project: Path) -> None:
    project.mkdir()
    (project / "run.toml").write_text(
        'schema = 1\nmode = "simulation-only"\nseed = 107\nnow = 1700000000\n'
        'timeout = 30\n[scenario]\nentry = "scenario.py"\n'
        'files = ["scenario.py", "scene.json", "emoji-static.webp", '
        '"emoji-thumbnail.webp"]\n[bots.files]\nentry = "bot.py"\n'
        'files = ["bot.py", "scene.json", "ordinary-document.bin"]\n'
    )
    (project / "scenario.py").write_text(SCENARIO)
    (project / "bot.py").write_text(BOT)
    (project / "scene.json").write_text(json.dumps(SCENE, ensure_ascii=False))
    (project / "ordinary-document.bin").write_bytes(DOCUMENT)
    for name in ("emoji-static.webp", "emoji-thumbnail.webp"):
        (project / name).write_bytes((ASSETS / "custom-emoji" / name).read_bytes())


def assert_public_result(recorded: dict[str, Any], *, native: bool = False) -> None:
    bot = {"id": 1, "is_bot": True, "first_name": "files"}
    user = {"id": 2, "is_bot": False, "first_name": "Sara", "language_code": "fa"}
    chat = {"id": 1, "type": "private", "user_id": 2, "bot_id": 1}
    api_chat = {"id": 2, "type": "private", "first_name": "Sara"}
    keyboard = {
        "inline_keyboard": [
            [{"text": SCENE["button_text"], "callback_data": SCENE["callback_data"]}]
        ]
    }
    bot_lines = [
        json.loads(line) for line in recorded["processes"]["bot:files"]["stdout"].splitlines()
    ]
    assert [line["event"] for line in bot_lines] == ["published", "callback"]
    published, completed = bot_lines
    document = published["sent"]["document"]
    digest = hashlib.sha256(DOCUMENT).hexdigest()
    identity = json.dumps(
        ["document", digest, SCENE["file_name"], "application/pdf"],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    assert document == {
        "file_id": document["file_id"],
        "file_unique_id": "gramlab_document_unique_" + hashlib.sha256(identity).hexdigest(),
        "file_size": len(DOCUMENT),
        "file_name": SCENE["file_name"],
        "mime_type": "application/pdf",
    }
    sent = {
        "message_id": 2,
        "from": bot,
        "chat": api_chat,
        "date": 1_700_000_000,
        "document": document,
        "caption": SCENE["caption"],
        "caption_entities": SCENE["caption_entities"],
        "reply_markup": keyboard,
    }
    assert published == {
        "event": "published",
        "sent": sent,
        "get_file": {
            "file_id": document["file_id"],
            "file_unique_id": document["file_unique_id"],
            "file_size": len(DOCUMENT),
            "file_path": f"documents/{document['file_id']}",
        },
        "download": {
            "status": 200,
            "content_type": "application/pdf",
            "content_length": str(len(DOCUMENT)),
            "cache_control": "no-store",
            "sha256": digest,
            "size": len(DOCUMENT),
        },
    }
    request = {
        "id": 1,
        "chat_id": 1,
        "sender_id": 2,
        "date": 1_700_000_000,
        "text": SCENE["request_text"],
    }
    world_sent = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1_700_000_000,
        "text": "",
        "reply_markup": keyboard,
        "document": {"document_id": "1"},
        "caption": SCENE["caption"],
        "caption_entities": SCENE["caption_entities"],
    }
    reused = {
        "id": 3,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1_700_000_000,
        "text": "",
        "document": {"document_id": "1"},
        "caption": SCENE["reuse_caption"],
    }
    api_reused = {
        "message_id": 3,
        "from": bot,
        "chat": api_chat,
        "date": 1_700_000_000,
        "document": document,
        "caption": SCENE["reuse_caption"],
    }
    callback_update = completed["update"]
    callback = callback_update["callback_query"]
    callback_id = callback["id"]
    world_id = recorded["run_id"]
    chat_instance = hashlib.sha256(f"{world_id}:1".encode()).hexdigest()
    assert callback_update == {
        "update_id": 2,
        "callback_query": {
            "id": callback_id,
            "from": user,
            "message": sent,
            "chat_instance": chat_instance,
            "data": SCENE["callback_data"],
        },
    }
    assert completed == {
        "event": "callback",
        "update": callback_update,
        "answer": True,
        "reused": api_reused,
    }
    answer = {"text": SCENE["answer_text"], "show_alert": False, "cache_time": 0}
    frozen = {
        "id": callback_id,
        "user_id": 2,
        "chat_id": 1,
        "message": world_sent,
        "data": SCENE["callback_data"],
        "chat_instance": chat_instance,
    }
    assert recorded["histories"] == {"1": [request, world_sent, reused]}
    assert recorded["world"] == {
        "schema": 1,
        "seed": 107,
        "now": 1_700_000_000,
        "users": [bot, user],
        "chats": [chat],
    }
    assert recorded["events"] == [
        {"sequence": 1, "type": "user.created", "data": bot},
        {"sequence": 2, "type": "user.created", "data": user},
        {"sequence": 3, "type": "chat.created", "data": chat},
        {"sequence": 4, "type": "message.created", "data": request},
        {"sequence": 5, "type": "message.created", "data": world_sent},
        {"sequence": 6, "type": "callback.created", "data": frozen},
        {
            "sequence": 7,
            "type": "callback.answered",
            "data": {"id": callback_id, "user_id": 2, "answer": answer},
        },
        {"sequence": 8, "type": "message.created", "data": reused},
    ]
    assert len(recorded["interactions"]) == 1
    interaction = recorded["interactions"][0]
    assert {key: value for key, value in interaction.items() if key != "android"} == {
        "chat_id": 1,
        "message_id": 2,
        "row": 0,
        "column": 0,
        "native": native,
        "callback": frozen | {"answer": None},
    }
    assert ("android" in interaction) is native
    first_capture = {
        "chat_id": 1,
        "label": "ordinary-document",
        "history": [request, world_sent],
        "rendered": native,
    }
    reused_capture = {
        "chat_id": 1,
        "label": "ordinary-document-reused",
        "history": [request, world_sent, reused],
        "rendered": native,
    }
    assert [
        {key: value for key, value in capture.items() if key != "android"}
        for capture in recorded["captures"]
    ] == [first_capture, reused_capture]
    assert all(("android" in capture) is native for capture in recorded["captures"])
    scenario = json.loads(recorded["processes"]["scenario"]["stdout"])
    assert scenario == {
        "request": request,
        "message": world_sent,
        "capture": recorded["captures"][0],
        "callback": frozen | {"answer": None},
        "answer": answer,
        "reused_capture": recorded["captures"][1],
    }


def test_runner_and_android_admit_explicit_v5_before_reading_run_inputs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run(
            tmp_path / "missing.toml",
            tmp_path / "output",
            profile=profile(),
            bridge_version=5,
        )
    assert (
        Android(
            profile(), deadline=time.monotonic() + 5, secrets=[], bridge_version=5
        )._bridge_version
        == 5
    )


def test_simulated_document_callback_uses_latest_world_contract(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    keyboard = {
        "inline_keyboard": [[{"text": "Reuse / استفاده دوباره", "callback_data": "document:reuse"}]]
    }
    with World.create(directory, seed=107, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Files", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://document"},
            uploads={"document": DocumentUpload(b"ordinary document", "report.pdf")},
            caption="فایل Report",
            reply_markup=keyboard,
        )

    interaction = Interactions(directory, lock=threading.Lock()).tap_inline_button(
        chat_id=chat["id"], message_id=message["id"], row=0, column=0
    )
    callback = interaction["callback"]
    assert callback["message"] == message
    assert callback["data"] == "document:reuse"
    with World.open(directory) as world:
        assert world.callback_dependencies(user["id"], callback, version=5)["documents"] == [
            world.granted_document(user["id"], "1")[0]
        ]


def test_public_cli_runs_real_document_bot_and_simulated_callback_at_v5(tmp_path: Path) -> None:
    project = tmp_path / "project"
    stage_public_scenario(project)
    output = tmp_path / "run"
    result = subprocess.run(  # noqa: S603 - tested CLI inside the outer network namespace
        [
            sys.executable,
            "-m",
            "gramlab",
            "run",
            str(project / "run.toml"),
            "--output",
            str(output),
            "--bridge-version",
            "5",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env=os.environ.copy(),
    )
    (tmp_path / "runner.stdout.log").write_text(result.stdout)
    (tmp_path / "runner.stderr.log").write_text(result.stderr)
    assert result.returncode == 0, (output / "result.json").read_text()
    recorded = json.loads((output / "result.json").read_text())
    assert recorded["outcome"] == "passed"
    assert recorded["mode"] == "simulation-only"
    assert recorded["failure"] is None
    assert recorded["android"] == {}
    assert_public_result(recorded)
    assert recorded["configuration"] == {
        "schema": 1,
        "mode": "simulation-only",
        "seed": 107,
        "now": 1_700_000_000,
        "timeout": 30,
        "scenario": {
            "entry": "scenario.py",
            "files": [
                "scenario.py",
                "scene.json",
                "emoji-static.webp",
                "emoji-thumbnail.webp",
            ],
        },
        "bots": {
            "files": {
                "entry": "bot.py",
                "files": ["bot.py", "scene.json", "ordinary-document.bin"],
            }
        },
    }
    expected_sources: dict[str, dict[str, str]] = {}
    for component, names in {
        "scenario": [
            "scenario.py",
            "scene.json",
            "emoji-static.webp",
            "emoji-thumbnail.webp",
        ],
        "bots/files": ["bot.py", "scene.json", "ordinary-document.bin"],
    }.items():
        expected_sources[component] = {
            name: hashlib.sha256((project / name).read_bytes()).hexdigest() for name in names
        }
    assert recorded["sources"] == expected_sources


@pytest.mark.android
def test_public_cli_runs_document_callback_in_original_android_at_v5(tmp_path: Path) -> None:
    runtime, android_profile, apk = require_android()
    project = tmp_path / "project"
    stage_public_scenario(project)
    manifest = project / "run.toml"
    manifest.write_text(
        manifest.read_text()
        .replace('mode = "simulation-only"', 'mode = "headless-android"')
        .replace("timeout = 30", "timeout = 300")
    )
    output = tmp_path / "run"
    result = subprocess.run(  # noqa: S603 — public CLI inside the offline test boundary
        [
            sys.executable,
            "-m",
            "gramlab",
            "run",
            str(manifest),
            "--output",
            str(output),
            "--profile",
            str(runtime),
            "--android-profile",
            str(android_profile),
            "--android-apk",
            str(apk),
            "--bridge-version",
            "5",
        ],
        capture_output=True,
        text=True,
        timeout=420,
        env=os.environ.copy(),
    )
    (tmp_path / "runner.stdout.log").write_text(result.stdout)
    (tmp_path / "runner.stderr.log").write_text(result.stderr)
    assert result.returncode == 0, (output / "result.json").read_text()
    recorded = json.loads((output / "result.json").read_text())
    assert_public_result(recorded, native=True)
    assert recorded["outcome"] == "passed" and recorded["failure"] is None
    assert recorded["mode"] == "headless-android"
    assert recorded["configuration"]["android"]["bridge_version"] == 5
    assert (
        recorded["configuration"]["android"]["apk_sha256"]
        == hashlib.sha256(apk.read_bytes()).hexdigest()
    )
    observed = recorded["android"]
    assert observed["api"] == "36" and observed["abi"] == "x86_64"
    assert observed["network"] == {"ipv4": 1, "ipv6": 1}
    assert observed["filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "scenario_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    assert recorded["interactions"][0]["android"]["target"]["text"] == SCENE["button_text"]
    for capture in recorded["captures"]:
        native = capture["android"]
        assert "Accounts: 0" in native["accounts"]
        assert SCENE["file_name"] in native["ui"]
        png = output / "captures" / f"{capture['label']}.png"
        assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert SCENE["button_text"] in recorded["captures"][0]["android"]["ui"]
    assert SCENE["reuse_caption"] in recorded["captures"][1]["android"]["ui"]
    assert (output / "report.html").read_text().count("data:image/png;base64,") == 2


@pytest.mark.parametrize(("argument", "expected"), [(None, 3), ("3", 3), ("4", 4), ("5", 5)])
def test_cli_preserves_default_and_explicit_bridge_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    argument: str | None,
    expected: int,
) -> None:
    selected: dict[str, Any] = {}

    def fake_run(
        manifest: Path,
        output: Path,
        *,
        profile: RuntimeProfile,
        android_profile: RuntimeProfile | None,
        android_apk: Path | None,
        bridge_version: int,
    ) -> str:
        selected.update(
            manifest=manifest,
            output=output,
            profile=profile,
            android_profile=android_profile,
            android_apk=android_apk,
            bridge_version=bridge_version,
        )
        return "passed"

    monkeypatch.setattr(cli, "run", fake_run)
    monkeypatch.setattr(RuntimeProfile, "load", lambda _path: profile())
    arguments = [
        "gramlab",
        "run",
        str(tmp_path / "run.toml"),
        "--output",
        str(tmp_path / "output"),
        "--profile",
        str(tmp_path / "profile.json"),
    ]
    if argument is not None:
        arguments.extend(("--bridge-version", argument))
    monkeypatch.setattr(sys, "argv", arguments)
    assert cli.main() == 0
    assert selected == {
        "manifest": tmp_path / "run.toml",
        "output": tmp_path / "output",
        "profile": profile(),
        "android_profile": None,
        "android_apk": None,
        "bridge_version": expected,
    }


@pytest.mark.parametrize("version", [True, False, 2, 6, 4.0, "5"])
def test_runner_and_android_strictly_reject_invalid_version_types(
    tmp_path: Path, version: Any
) -> None:
    with pytest.raises(ValueError, match="Android bridge version must be 3, 4 or 5"):
        run(
            tmp_path / "missing.toml",
            tmp_path / "output",
            profile=profile(),
            bridge_version=version,
        )
    with pytest.raises(ValueError, match="Android bridge version must be 3, 4 or 5"):
        Android(profile(), deadline=time.monotonic() + 5, secrets=[], bridge_version=version)


def test_android_v5_writes_selected_app_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with World.create(Path("world"), seed=107, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Files", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        world_id = world.world_id
    android = Android(profile(), deadline=time.monotonic() + 5, secrets=[], bridge_version=5)
    monkeypatch.setattr(android, "_guest", SimpleNamespace(poll=lambda: None))
    monkeypatch.setattr(android, "_bridge", SimpleNamespace(base_url="http://127.0.0.1:12345"))
    calls: list[tuple[tuple[str, ...], dict[str, Any]]] = []

    def boundary(*arguments: str, **keywords: Any) -> subprocess.CompletedProcess[str]:
        calls.append((arguments, keywords))
        stdout = "Success" if arguments[:3] == ("shell", "pm", "clear") else "Status: ok"
        return subprocess.CompletedProcess(arguments, 0, stdout=stdout)

    monkeypatch.setattr(android, "_adb", boundary)
    android._open_chat(chat)
    writes = [
        (arguments, keywords)
        for arguments, keywords in calls
        if arguments[:3] == ("shell", "-T", "run-as")
    ]
    assert len(writes) == 1
    assert "config.json" in writes[0][0][-1]
    configuration = json.loads(writes[0][1]["input"])
    assert configuration == {
        "endpoint": "http://10.0.2.2:12345",
        "capability": configuration["capability"],
        "world_id": world_id,
        "user_id": user["id"],
        "bridge_version": 5,
    }
    assert configuration["capability"] in android.secrets


@pytest.mark.parametrize("version", [4, 5])
@pytest.mark.parametrize("kind", ["callback", "copy", "disabled"])
def test_rich_input_uses_selected_version_for_complete_mixed_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version: int,
    kind: str,
) -> None:
    snapshot_versions: list[int] = []
    dependency_versions: list[int] = []
    original_snapshot = World.client_snapshot
    original_dependencies = World.callback_dependencies

    def tracked_snapshot(world: World, user_id: int, *, version: int = 1) -> dict[str, Any]:
        snapshot_versions.append(version)
        return original_snapshot(world, user_id, version=version)

    def tracked_dependencies(
        world: World, user_id: int, callback: dict[str, Any], *, version: int = 1
    ) -> dict[str, Any]:
        dependency_versions.append(version)
        return original_dependencies(world, user_id, callback, version=version)

    monkeypatch.setattr(World, "client_snapshot", tracked_snapshot)
    monkeypatch.setattr(World, "callback_dependencies", tracked_dependencies)
    guest, receipt, before, record = mixed_rich_guest(
        tmp_path, monkeypatch, version=version, kind=kind
    )
    guest.baseline = "clipboard before"
    prepared = guest.prepare(receipt, client_nonce="process-original")
    assert prepared["context"]["world_before"] == before
    assert guest.files["rich-button-observe.json"]["schema"] == 1
    assert guest.files["rich-button-arm.json"]["schema"] == 1
    result = guest.dispatch(receipt, prepared)
    assert result["status"] == "succeeded"
    assert result["dispatch"] == "dispatched"
    with World.open(Path("world")) as world:
        after = world.client_snapshot(record["chat"]["user_id"], version=version)
        if kind == "callback":
            callback = result["effect"]["callback"]
            dependencies = world.callback_dependencies(
                record["chat"]["user_id"], callback, version=version
            )
            assert result["effect"] == {
                "kind": "callback",
                "callback": callback,
                "event_sequence": before["cursor"] + 1,
            }
            assert callback == {
                "id": callback["id"],
                "user_id": record["chat"]["user_id"],
                "chat_id": record["chat"]["id"],
                "message": record["message"],
                "data": "mixed:callback",
                "chat_instance": callback["chat_instance"],
                "answer": None,
            }
            assert dependencies["message_revision"] == record["revision"]
            assert dependencies == {
                "users": before["users"],
                "assets": [],
                "message_revision": record["revision"],
                "custom_emoji": [],
                **({"documents": []} if version == 5 else {}),
            }
            assert after == before | {"cursor": before["cursor"] + 1}
        else:
            assert result["effect"] == (
                {"kind": "copy", "text": "برداشت / copy"}
                if kind == "copy"
                else {"kind": "none", "reason": "disabled"}
            )
            assert after == before
            assert result["evidence"]["world_event_sequences"] == []
    assert set(snapshot_versions) == {version}
    assert set(dependency_versions) <= {version}
    assert (dependency_versions != []) == (kind == "callback")


def test_rich_input_keeps_v3_explicitly_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with World.create(Path("world"), seed=107, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Files", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_rich_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            rich_message={
                "skip_entity_detection": True,
                "blocks": [
                    {
                        "type": "buttons",
                        "buttons": [{"text": "Selected", "callback_data": "callback"}],
                    }
                ],
            },
        )
        record = {
            "chat": chat,
            "message": message,
            "revision": world.client_snapshot(user["id"], version=3)["message_revisions"][0][
                "revision"
            ],
        }
        world_id = world.world_id
    android = Android(profile(), deadline=time.monotonic() + 5, secrets=[], bridge_version=3)
    guest = VersionedGuest(android, record, world_id)
    with pytest.raises(ValueError, match="target_unavailable"):
        guest.observe(record)


def test_document_inline_identity_requires_its_exact_caption() -> None:
    message = {
        "text": "",
        "document": {"document_id": "1"},
        "caption": "فایل Report 👩‍💻",
    }
    descriptor = {
        "document_id": "1",
        "file_name": "report.pdf",
        "mime_type": "application/pdf",
        "file_size": 85,
        "sha256": "a" * 64,
    }
    label = "PDF file, report.pdf, 85 B\nفایل Report 👩‍💻\nReceived at 10:13 PM\n"  # noqa: RUF001
    assert _inline_fragments(message) == ["فایل Report 👩‍💻"]
    assert _inline_matches(message, label, descriptor)
    assert not _inline_matches(
        message,
        "PDF file, report.pdf, 85 B\nDifferent\nReceived at 10:13 PM\n",
        descriptor,
    )
    assert not _inline_matches(message, "فایل Report 👩‍💻\nReceived at 10:13 PM\n", descriptor)
    assert not _inline_matches(message, label)
    del message["caption"]
    assert _inline_fragments(message) == []
    assert not _inline_matches(
        message, "PDF file, report.pdf, 85 B\nReceived at 10:13 PM\n", descriptor
    )


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0 KB"),
        (1, "1 B"),
        (1023, "1023 B"),
        (1024, "1.0 KB"),
        (1280, "1.3 KB"),
        (1024 * 1024 - 1, "1024.0 KB"),
        (1024 * 1024, "1.0 MB"),
        (1024 * 1024 + 256 * 1024, "1.3 MB"),
        (50_000_000, "47.7 MB"),
    ],
)
def test_document_accessibility_size_uses_pinned_english_boundaries(
    size: int, expected: str
) -> None:
    assert _android_file_size(size) == expected


def test_document_accessibility_type_uses_filename_then_original_mime_fallback() -> None:
    assert (
        _document_accessibility_header(
            {"file_name": "report.PdF", "mime_type": "application/zip", "file_size": 85}
        )
        == "PDF file, report.PdF, 85 B"
    )
    assert (
        _document_accessibility_header(
            {"file_name": "archive", "mime_type": "video/x-matroska", "file_size": 1024}
        )
        == "MKV file, archive, 1.0 KB"
    )
    assert (
        _document_accessibility_header(
            {"file_name": "archive", "mime_type": "application/octet-stream", "file_size": 1024}
        )
        == "archive, 1.0 KB"
    )
    assert (
        _document_accessibility_header(
            {"file_name": "گزارش-English.pdf", "mime_type": "application/pdf", "file_size": 88}
        )
        == "PDF file,گزارش-English.pdf, 88 B"
    )


@pytest.mark.parametrize(
    "native_text",
    [
        "ZIP file, report.pdf, 85 B\nSame caption\nReceived at 10:13 PM\n",
        "PDF file, report.pdf, 999 GB\nSame caption\nReceived at 10:13 PM\n",
    ],
)
def test_document_dispatch_rejects_wrong_native_type_or_size_before_tap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    native_text: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    keyboard = {"inline_keyboard": [[{"text": "Open", "callback_data": "open"}]]}
    with World.create(Path("world"), seed=107, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Files", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://document"},
            uploads={"document": DocumentUpload(b"x" * 85, "report.pdf")},
            caption="Same caption",
            reply_markup=keyboard,
        )
    cell = (
        '<hierarchy><node package="org.gramlab.android" text="'
        + native_text.replace("\n", "&#10;")
        + '"><node class="android.widget.Button" text="Open" bounds="[10,100][90,130]" '
        'clickable="true" enabled="true" /></node></hierarchy>'
    )
    android = Android(profile(), deadline=time.monotonic() + 2, secrets=[], bridge_version=5)
    monkeypatch.setattr(android, "_open_chat", lambda _chat: None)
    monkeypatch.setattr(android, "_wait_ui", lambda _contains: cell)
    taps: list[tuple[str, ...]] = []

    def dispatch(*arguments: str, **_keywords: Any) -> Any:
        taps.append(arguments)
        raise AssertionError("A mismatched document row reached native input")

    monkeypatch.setattr(android, "_adb", dispatch)
    with pytest.raises(RuntimeError, match="did not become accessible"):
        android._tap_inline_button(chat, message, 0, 0)
    assert taps == []


def test_document_dispatch_waits_for_transiently_missing_keyboard_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    keyboard = {"inline_keyboard": [[{"text": "Open", "callback_data": "open"}]]}
    with World.create(Path("world"), seed=107, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Files", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://document"},
            uploads={"document": DocumentUpload(b"x" * 85, "report.pdf")},
            caption="Same caption",
            reply_markup=keyboard,
        )
    native_text = "PDF file, report.pdf, 85 B\nSame caption\nReceived at 10:13 PM\n"
    row = (
        '<node package="org.gramlab.android" text="'
        + native_text.replace("\n", "&#10;")
        + '">{} </node>'
    )
    incomplete = "<hierarchy>" + row.format("") + "</hierarchy>"
    complete = (
        "<hierarchy>"
        + row.format(
            '<node class="android.widget.Button" text="Open" bounds="[10,100][90,130]" '
            'clickable="true" enabled="true" />'
        )
        + "</hierarchy>"
    )
    android = Android(profile(), deadline=time.monotonic() + 2, secrets=[], bridge_version=5)
    monkeypatch.setattr(android, "_open_chat", lambda _chat: None)
    dumps = iter((incomplete, complete))
    monkeypatch.setattr(android, "_wait_ui", lambda _contains: next(dumps))

    class NativeInputReached(Exception):
        pass

    monkeypatch.setattr(
        android,
        "_adb",
        lambda *_arguments, **_keywords: (_ for _ in ()).throw(NativeInputReached),
    )
    with pytest.raises(NativeInputReached):
        android._tap_inline_button(chat, message, 0, 0)


def test_document_dispatch_distinguishes_descriptors_and_rejects_indistinguishable_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    keyboard = {"inline_keyboard": [[{"text": "Open", "callback_data": "open"}]]}
    with World.create(Path("world"), seed=107, now=1_700_000_000) as world:
        user = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Files", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        target = world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://target"},
            uploads={"target": DocumentUpload(b"a" * 85, "report.pdf")},
            caption="Same caption",
            reply_markup=keyboard,
        )
        world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://distinct"},
            uploads={"distinct": DocumentUpload(b"b" * 85, "archive.zip")},
            caption="Same caption",
            reply_markup=keyboard,
        )
    native_text = "PDF file, report.pdf, 85 B\nSame caption\nReceived at 10:13 PM\n"
    cell = (
        '<hierarchy><node package="org.gramlab.android" text="'
        + native_text.replace("\n", "&#10;")
        + '"><node class="android.widget.Button" text="Open" bounds="[10,100][90,130]" '
        'clickable="true" enabled="true" /></node></hierarchy>'
    )
    android = Android(profile(), deadline=time.monotonic() + 2, secrets=[], bridge_version=5)
    monkeypatch.setattr(android, "_open_chat", lambda _chat: None)
    monkeypatch.setattr(android, "_wait_ui", lambda _contains: cell)

    class NativeInputReached(Exception):
        pass

    monkeypatch.setattr(
        android,
        "_adb",
        lambda *_arguments, **_keywords: (_ for _ in ()).throw(NativeInputReached),
    )
    with pytest.raises(NativeInputReached):
        android._tap_inline_button(chat, target, 0, 0)

    with World.open(Path("world")) as world:
        world.send_document(
            chat_id=chat["id"],
            sender_id=bot["id"],
            document={"media": "attach://indistinguishable"},
            uploads={"indistinguishable": DocumentUpload(b"c" * 85, "report.pdf")},
            caption="Same caption",
            reply_markup=keyboard,
        )
    with pytest.raises(RuntimeError, match="text is ambiguous"):
        android._tap_inline_button(chat, target, 0, 0)
