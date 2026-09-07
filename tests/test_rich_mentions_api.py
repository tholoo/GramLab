import http.client
import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from test_bot_api import request

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


def test_json_send_projects_authoritative_user_and_accepts_output_noop(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=90) as world:
        recipient = world.create_user(first_name="Sara", language_code="fa")
        bot = world.create_user(first_name="Echo", is_bot=True, username="echo_bot")
        referenced = world.create_user(first_name="Mina", username="mina")
        world.open_private_chat(user_id=recipient["id"], bot_id=bot["id"])
        world.open_private_chat(user_id=referenced["id"], bot_id=bot["id"])
        token = world.issue_bot_token(bot["id"])
    supplied = {"id": referenced["id"], "first_name": "FORGED", "is_bot": True}
    content = {
        "skip_entity_detection": True,
        "blocks": [
            {
                "type": "paragraph",
                "text": {"type": "text_mention", "text": "Mina", "user": supplied},
            }
        ],
    }
    with BotAPIServer(directory) as server:
        status, body = request(
            server, token, "sendRichMessage", {"chat_id": recipient["id"], "rich_message": content}
        )
        expected_user = {
            "id": referenced["id"],
            "is_bot": False,
            "first_name": "Mina",
            "username": "mina",
        }
        expected_rich = {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {"type": "text_mention", "text": "Mina", "user": expected_user},
                }
            ]
        }
        assert (status, body) == (
            200,
            {
                "ok": True,
                "result": {
                    "message_id": 1,
                    "from": {
                        "id": bot["id"],
                        "is_bot": True,
                        "first_name": "Echo",
                        "username": "echo_bot",
                    },
                    "chat": {"id": recipient["id"], "type": "private", "first_name": "Sara"},
                    "date": 90,
                    "rich_message": expected_rich,
                },
            },
        )
        round_trip = {
            "skip_entity_detection": True,
            "blocks": [
                {"type": "paragraph", "text": body["result"]["rich_message"]["blocks"][0]["text"]}
            ],
        }
        assert request(
            server,
            token,
            "editMessageText",
            {"chat_id": recipient["id"], "message_id": 1, "rich_message": round_trip},
        ) == (400, {"ok": False, "error_code": 400, "description": "MESSAGE_NOT_MODIFIED"})


def test_form_send_uses_same_projection(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=1, now=5) as world:
        recipient = world.create_user(first_name="Sara")
        bot = world.create_user(first_name="Echo", is_bot=True)
        world.open_private_chat(user_id=recipient["id"], bot_id=bot["id"])
        token = world.issue_bot_token(bot["id"])
    content = {
        "skip_entity_detection": True,
        "blocks": [
            {"type": "footer", "text": {"type": "text_mention", "text": "", "user": {"id": 2}}}
        ],
    }
    encoded = urlencode({"chat_id": recipient["id"], "rich_message": json.dumps(content)})
    with BotAPIServer(directory) as server:
        url = urlsplit(server.base_url)
        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        connection.request(
            "POST",
            f"/bot{token}/sendRichMessage",
            encoded,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        connection.close()
    assert response.status == 200
    assert body["result"]["rich_message"] == {
        "blocks": [
            {
                "type": "footer",
                "text": {
                    "type": "text_mention",
                    "text": "",
                    "user": {"id": 2, "is_bot": True, "first_name": "Echo"},
                },
            }
        ]
    }
