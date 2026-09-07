"""Structured URL, email-address and phone-number rich text boundaries."""

import copy
import http.client
import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import pytest

from gramlab.bot_api import BotAPIServer
from gramlab.world import World


def world_at(directory: Path) -> World:
    world = World.create(directory, seed=29, now=100)
    world.create_user(first_name="Human")
    world.create_user(first_name="Bot", is_bot=True)
    world.open_private_chat(user_id=1, bot_id=2)
    return world


def rich(text: object) -> dict[str, object]:
    return {
        "blocks": [{"type": "paragraph", "text": text}],
        "skip_entity_detection": True,
    }


def request(
    server: BotAPIServer,
    token: str,
    method: str,
    parameters: dict[str, object],
    *,
    form: bool = False,
) -> tuple[int, dict[str, object]]:
    url = urlsplit(server.base_url)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    body = (
        urlencode(
            {
                key: json.dumps(value) if isinstance(value, (dict, list)) else value
                for key, value in parameters.items()
            }
        )
        if form
        else json.dumps(parameters)
    )
    content_type = "application/x-www-form-urlencoded" if form else "application/json"
    try:
        connection.request("POST", f"/bot{token}/{method}", body, {"Content-Type": content_type})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def linked_text() -> list[object]:
    return [
        {
            "type": "url",
            "url": "https://exa\u202emple.test/a\tb",
            "text": {"type": "bold", "text": "پیوند\tLink"},
        },
        " | ",
        {
            "type": "italic",
            "text": {
                "type": "email_address",
                "email_address": "not\u0333 an address",
                "text": "نامه",
            },
        },
        {
            "type": "phone_number",
            "phone_number": "",
            "text": [" ", {"type": "underline", "text": "+۹۸"}],
        },
    ]


def canonical_text() -> list[object]:
    return [
        {
            "type": "url",
            "url": "https://example.test/a b",
            "text": {"type": "bold", "text": "پیوند Link"},
        },
        " | ",
        {
            "type": "italic",
            "text": {
                "type": "email_address",
                "email_address": "not an address",
                "text": "نامه",
            },
        },
        {
            "type": "phone_number",
            "phone_number": "",
            "text": [" ", {"type": "underline", "text": "+۹۸"}],
        },
    ]


def test_world_round_trip_cleaning_noop_reopen_and_complete_observations(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    payload = rich(linked_text())
    pristine = copy.deepcopy(payload)
    expected_rich = {"blocks": [{"type": "paragraph", "text": canonical_text()}]}

    with world_at(directory) as world:
        created = world.send_rich_message(chat_id=1, sender_id=2, rich_message=payload)
        assert payload == pristine
        assert created["rich_message"] == expected_rich
        assert world.history(1) == [created]
        assert world.client_snapshot(1, version=2)["messages"] == [created]
        assert world.client_changes(1, after=0)["changes"] == [
            {"position": 1, "type": "message.created", "data": created}
        ]
        before = world.client_snapshot(1, version=2), world.events()
        with pytest.raises(ValueError, match="MESSAGE_NOT_MODIFIED"):
            world.edit_message(
                chat_id=1,
                message_id=1,
                bot_id=2,
                rich_message={**expected_rich, "skip_entity_detection": True},
            )
        assert (world.client_snapshot(1, version=2), world.events()) == before

    with World.open(directory) as world:
        assert world.history(1) == [created]
        assert world.client_snapshot(1, version=2)["messages"] == [created]


@pytest.mark.parametrize("form", [False, True])
def test_http_send_and_edit_preserve_complete_link_shapes(tmp_path: Path, form: bool) -> None:
    directory = tmp_path / "world"
    with world_at(directory) as world:
        token = world.issue_bot_token(2)
    initial = {"blocks": [{"type": "paragraph", "text": canonical_text()}]}
    edited_text = {
        "type": "url",
        "url": "relative\tvalue",
        "text": {"type": "phone_number", "phone_number": "none", "text": "Edited"},
    }
    edited = {"blocks": [{"type": "paragraph", "text": {**edited_text, "url": "relative value"}}]}

    with BotAPIServer(directory) as server:
        status, response = request(
            server,
            token,
            "sendRichMessage",
            {"chat_id": 1, "rich_message": {**initial, "skip_entity_detection": True}},
            form=form,
        )
        assert status == 200
        assert response["ok"] is True
        assert response["result"]["rich_message"] == initial  # type: ignore[index]
        with World.open(directory) as world:
            world.advance_time(5)
        status, response = request(
            server,
            token,
            "editMessageText",
            {
                "chat_id": 1,
                "message_id": 1,
                "rich_message": rich(edited_text),
            },
            form=form,
        )
        assert status == 200
        assert response["ok"] is True
        assert response["result"]["rich_message"] == edited  # type: ignore[index]
        with World.open(directory) as world:
            before_noop = world.client_snapshot(1, version=2), world.events()
        status, response = request(
            server,
            token,
            "editMessageText",
            {
                "chat_id": 1,
                "message_id": 1,
                "rich_message": {**edited, "skip_entity_detection": True},
            },
            form=form,
        )
        assert status == 400
        assert response["ok"] is False
        assert "MESSAGE_NOT_MODIFIED" in response["description"]  # type: ignore[operator]
        with World.open(directory) as world:
            assert (world.client_snapshot(1, version=2), world.events()) == before_noop

    with World.open(directory) as world:
        message = world.history(1)[0]
        assert message["rich_message"] == edited
        message_events = [
            event["type"] for event in world.events() if event["type"].startswith("message.")
        ]
        assert message_events == [
            "message.created",
            "message.edited",
        ]


def test_world_text_to_rich_link_transition_is_durable(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    link = rich({"type": "email_address", "email_address": "", "text": "Contact"})
    with world_at(directory) as world:
        initial = world.send_message(chat_id=1, sender_id=2, text="Plain")
        world.advance_time(3)
        edited = world.edit_message(
            chat_id=1, message_id=initial["id"], bot_id=2, rich_message=link
        )
        assert edited["text"] == ""
        assert edited["rich_message"] == {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {
                        "type": "email_address",
                        "email_address": "",
                        "text": "Contact",
                    },
                }
            ]
        }
    with World.open(directory) as world:
        assert world.history(1) == [edited]


@pytest.mark.parametrize(
    "text",
    [
        {"type": "url", "text": "x"},
        {"type": "url", "text": "x", "url": 3},
        {"type": "url", "text": "x", "url": "x", "extra": True},
        {"type": "email_address", "text": "x", "url": "x"},
        {"type": "phone_number", "text": "x", "phone_number": None},
        {"type": "address", "text": "x", "address": "x"},
        {"type": "url", "text": "x", "url": "\ud800"},
    ],
)
def test_invalid_link_nodes_reject_atomically_at_world_and_http(
    tmp_path: Path, text: object
) -> None:
    directory = tmp_path / "world"
    with world_at(directory) as world:
        token = world.issue_bot_token(2)
        original = world.send_message(chat_id=1, sender_id=2, text="Original")
        before = world.client_snapshot(1, version=2), world.events()
        with pytest.raises(ValueError):
            world.send_rich_message(chat_id=1, sender_id=2, rich_message=rich(text))
        assert (world.client_snapshot(1, version=2), world.events()) == before
        with pytest.raises(ValueError):
            world.edit_message(
                chat_id=1, message_id=original["id"], bot_id=2, rich_message=rich(text)
            )
        assert (world.client_snapshot(1, version=2), world.events()) == before

    with BotAPIServer(directory) as server:
        for method, extra in (("sendRichMessage", {}), ("editMessageText", {"message_id": 1})):
            status, response = request(
                server,
                token,
                method,
                {"chat_id": 1, "rich_message": rich(text), **extra},
            )
            assert status == 400
            assert response["ok"] is False
            with World.open(directory) as world:
                assert (world.client_snapshot(1, version=2), world.events()) == before
    with World.open(directory) as world:
        assert (world.client_snapshot(1, version=2), world.events()) == before


def test_link_metadata_uses_the_existing_per_string_utf8_limit(tmp_path: Path) -> None:
    metadata = "a" * 34_995 + "💡tail"
    with world_at(tmp_path / "world") as world:
        message = world.send_rich_message(
            chat_id=1,
            sender_id=2,
            rich_message=rich({"type": "url", "url": metadata, "text": "x"}),
        )
    assert message["rich_message"] == {
        "blocks": [
            {
                "type": "paragraph",
                "text": {"type": "url", "url": "a" * 34_995 + "💡", "text": "x"},
            }
        ]
    }
