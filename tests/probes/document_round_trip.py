"""Real forced-document bot scenario shared by simulation and original Android."""

import hashlib
import http.client
import json
import selectors
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from component_bot import FixtureBot

from gramlab.bot_api import BotAPIServer
from gramlab.client_bridge import ClientBridge
from gramlab.world import World

DOCUMENT_BYTES = (
    b"%PDF-1.4\n% GramLab forced ordinary document\n"
    b"Persian-English filename; exact local bytes.\x00\xff\n%%EOF\n"
)
PHOTO_PATH = Path("replacement-photo.png")
REPLACEMENT_DOCUMENT_BYTES = (
    b"%PDF-1.4\n% GramLab replacement ordinary document\nDistinct D2 exact bytes.\x01\xfe\n%%EOF\n"
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
    "replacement_file_name": "ویرایش-English-2.pdf",
    "replacement_upload_name": "%D9%88%DB%8C%D8%B1%D8%A7%DB%8C%D8%B4-English-2.pdf",
    "edit_sequence": [
        {
            "operation": "editMessageCaption",
            "trigger_data": "document:reuse",
            "caption": "D1 caption edited / زیرنویس سند",
            "caption_entities": [{"type": "bold", "offset": 0, "length": 2}],
            "button_text": "Replace with photo / عکس",
            "callback_data": "document:photo",
            "answer_text": "Caption edited",
        },
        {
            "operation": "editMessageMedia",
            "trigger_data": "document:photo",
            "caption": "P1 initial / عکس نخست",
            "caption_entities": [{"type": "italic", "offset": 0, "length": 2}],
            "button_text": "Edit photo caption / زیرنویس",
            "callback_data": "photo:caption",
            "answer_text": "Photo replaced",
        },
        {
            "operation": "editMessageCaption",
            "trigger_data": "photo:caption",
            "caption": "P1 caption edited / عکس ویرایش شد",
            "caption_entities": [{"type": "bold", "offset": 0, "length": 2}],
            "button_text": "Replace with D2 / سند دوم",
            "callback_data": "photo:document",
            "answer_text": "Photo caption edited",
        },
        {
            "operation": "editMessageMedia",
            "trigger_data": "photo:document",
            "caption": "D2 final / سند نهایی",
            "caption_entities": [{"type": "italic", "offset": 0, "length": 2}],
            "button_text": "Complete / تمام",
            "callback_data": "document:complete",
            "answer_text": "Document replaced",
        },
    ],
}
for _step in SCENE["edit_sequence"]:
    _step["reply_markup"] = {
        "inline_keyboard": [
            [{"text": _step["button_text"], "callback_data": _step["callback_data"]}]
        ]
    }
CALLBACK_TAPS = (
    ("initial", SCENE["button_text"]),
    ("photo", SCENE["edit_sequence"][0]["button_text"]),
    ("photo_caption", SCENE["edit_sequence"][1]["button_text"]),
    ("document_final", SCENE["edit_sequence"][2]["button_text"]),
)


def run(
    show: Callable[[dict[str, Any]], str] | None = None,
    tap: Callable[[str, str], None] | None = None,
    observe: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    directory = Path("world")
    emoji_root = Path("custom-emoji")
    main = (emoji_root / "emoji-static.webp").read_bytes()
    thumbnail = (emoji_root / "emoji-thumbnail.webp").read_bytes()
    with World.create(directory, seed=105, now=1_700_000_000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Files", username="gramlab_files_bot", is_bot=True)
        world.create_user(first_name="Other", username="other_files_bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.open_private_chat(user_id=1, bot_id=3)
        world.register_custom_emoji(
            request_id="document-caption",
            main=main,
            thumbnail=thumbnail,
            fallback="👩‍💻",
            custom_emoji_id=1109,
            free=True,
            needs_repainting=False,
        )
        world.send_message(chat_id=1, sender_id=1, text=SCENE["request_text"])
        token = world.issue_bot_token(2)
        foreign_token = world.issue_bot_token(3)
        capability = world.issue_client_token(1)
        world_id = world.world_id

    records: dict[str, Any] = {}
    bridge_records: dict[str, Any] = {}
    client: dict[str, Any] = {}

    def read_record(bot: Any, expected: str) -> dict[str, Any]:
        assert bot.stdout is not None
        with selectors.DefaultSelector() as ready:
            ready.register(bot.stdout, selectors.EVENT_READ)
            if not ready.select(timeout=20):
                raise RuntimeError(f"Document bot did not reach {expected}")
        line = bot.stdout.readline()
        if not line:
            _, stderr = bot.communicate(timeout=5)
            raise RuntimeError(f"Document bot exited before {expected}: {stderr}")
        value = dict(json.loads(line))
        if value.get("event") != expected:
            raise RuntimeError(f"Expected {expected}, received another document bot event")
        return value

    def bridge_json(
        bridge: ClientBridge, path: str, body: dict[str, Any] | None = None
    ) -> tuple[int, dict[str, Any]]:
        endpoint = urlsplit(bridge.base_url)
        connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
        try:
            connection.request(
                "POST" if body is not None else "GET",
                path,
                json.dumps(body) if body is not None else None,
                {"Authorization": "Bearer " + capability, "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            return response.status, dict(json.loads(response.read()))
        finally:
            connection.close()

    def bridge_document(bridge: ClientBridge, document_id: str) -> dict[str, Any]:
        endpoint = urlsplit(bridge.base_url)
        connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
        try:
            connection.request(
                "GET",
                f"/v5/documents/{document_id}",
                headers={"Authorization": "Bearer " + capability},
            )
            response = connection.getresponse()
            payload = response.read()
            return {
                "status": response.status,
                "content_type": response.getheader("Content-Type"),
                "content_length": response.getheader("Content-Length"),
                "cache_control": response.getheader("Cache-Control"),
                "connection": response.getheader("Connection"),
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        finally:
            connection.close()

    def configuration(bridge: ClientBridge, stage: str) -> dict[str, Any]:
        return {
            "endpoint": bridge.base_url,
            "capability": capability,
            "world_id": world_id,
            "user_id": 1,
            "bridge_version": 5,
            "stage": stage,
        }

    fixture = FixtureBot("document_bot.py")
    (fixture.data / "ordinary-document.bin").write_bytes(DOCUMENT_BYTES)
    (fixture.data / "replacement-photo.png").write_bytes(PHOTO_PATH.read_bytes())
    (fixture.data / "ordinary-document-2.bin").write_bytes(REPLACEMENT_DOCUMENT_BYTES)
    environment = {
        "GRAMLAB_BOT_API": "",
        "GRAMLAB_BOT_TOKEN": token,
        "GRAMLAB_FOREIGN_BOT_TOKEN": foreign_token,
        "GRAMLAB_DOCUMENT_SCENE": json.dumps(SCENE, ensure_ascii=False),
    }
    with BotAPIServer(directory) as server, ClientBridge(directory) as bridge:
        environment["GRAMLAB_BOT_API"] = server.base_url
        with fixture.start(environment) as bot:
            records["published"] = read_record(bot, "published")["value"]
            bridge_records["initial_snapshot"] = bridge_json(bridge, "/v5/snapshot")[1]
            bridge_records["initial_changes"] = bridge_json(
                bridge, "/v5/changes?after=0&limit=100"
            )[1]
            document_id = bridge_records["initial_snapshot"]["documents"][0]["document_id"]
            bridge_records["initial_download"] = bridge_document(bridge, document_id)
            if show is not None:
                client["initial"] = show(configuration(bridge, "initial"))

            with World.open(directory) as world:
                world.advance_time(5)
            assert bot.stdin is not None
            bot.stdin.write("callback\n")
            bot.stdin.flush()
            if tap is None:
                callback_status, _ = bridge_json(
                    bridge,
                    "/v5/callbacks",
                    {
                        "request_id": "document-tap-1",
                        "chat_id": 1,
                        "message_id": 2,
                        "data": SCENE["callback_data"],
                    },
                )
                if callback_status != 200:
                    raise RuntimeError("v5 document callback creation failed")
            else:
                tap(*CALLBACK_TAPS[0])
            stage_events = ("document_caption", "photo", "photo_caption", "document_final")
            for index, event in enumerate(stage_events):
                if index:
                    with World.open(directory) as world:
                        world.advance_time(5)
                    bot.stdin.write("callback\n")
                    bot.stdin.flush()
                    step = SCENE["edit_sequence"][index]
                    if tap is None:
                        callback_status, _ = bridge_json(
                            bridge,
                            "/v5/callbacks",
                            {
                                "request_id": f"document-tap-{index + 1}",
                                "chat_id": 1,
                                "message_id": 2,
                                "data": step["trigger_data"],
                            },
                        )
                        if callback_status != 200:
                            raise RuntimeError("v5 media-edit callback creation failed")
                    else:
                        tap(*CALLBACK_TAPS[index])
                records[event] = read_record(bot, event)
                callback_id = records[event]["update"]["callback_query"]["id"]
                bridge_records[event + "_callback"] = bridge_json(
                    bridge, f"/v5/callbacks/{callback_id}"
                )[1]
                bridge_records[event + "_snapshot"] = bridge_json(bridge, "/v5/snapshot")[1]
                bridge_records[event + "_changes"] = bridge_json(
                    bridge, "/v5/changes?after=0&limit=100"
                )[1]
                if show is not None:
                    client[event] = show(configuration(bridge, event))
            _, stderr = bot.communicate(timeout=10)
            if bot.returncode != 0 or stderr:
                raise RuntimeError("Document bot failed after callback reuse")

    with BotAPIServer(directory), ClientBridge(directory) as reopened_bridge:
        bridge_records["restarted_snapshot"] = bridge_json(reopened_bridge, "/v5/snapshot")[1]
        bridge_records["restarted_changes"] = bridge_json(
            reopened_bridge, "/v5/changes?after=0&limit=100"
        )[1]
        bridge_records["restarted_callback"] = bridge_json(
            reopened_bridge, f"/v5/callbacks/{callback_id}"
        )[1]
        if show is not None:
            client["restart"] = show(configuration(reopened_bridge, "restart"))
        if observe is not None:
            client["observed"] = observe()

    with World.open(directory) as world:
        document_grants = []
        for retained_id in ("1", "2"):
            descriptor, data = world.granted_document(1, retained_id)
            document_grants.append(
                {
                    "descriptor": descriptor,
                    "file": world.document_file(2, retained_id),
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        photo_grant = world.granted_asset(1, 3)
        photo_file = world.photo_size(2, 3)
        result = {
            "world_id": world_id,
            "bot": records,
            "history": world.history(1),
            "events": world.events(),
            "pending": world.poll_updates(2),
            "grants": {
                "documents": document_grants,
                "photo": {
                    "asset": photo_grant[0],
                    "file": photo_file,
                    "size": len(photo_grant[1]),
                    "sha256": hashlib.sha256(photo_grant[1]).hexdigest(),
                },
            },
            "v5": bridge_records,
            "api": [json.loads(line) for line in Path("bot/api.jsonl").read_text().splitlines()],
            "client": client,
        }
    serialized = json.dumps(result, ensure_ascii=False)
    if token in serialized or foreign_token in serialized or capability in serialized:
        raise RuntimeError("Document evidence contains a capability")
    Path("document-round-trip.json").write_text(serialized)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
