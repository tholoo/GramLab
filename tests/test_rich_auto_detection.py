"""Approved deterministic rich-text automatic-detection contract."""

import copy
import http.client
import json
from itertools import permutations
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from gramlab.bot_api import BotAPIServer
from gramlab.rich_messages import rich_message
from gramlab.world import World


def paragraph(text: Any, **fields: Any) -> dict[str, Any]:
    return {"blocks": [{"type": "paragraph", "text": text}], **fields}


def entity(kind: str, text: Any, **metadata: Any) -> dict[str, Any]:
    return {"type": kind, "text": text, **metadata}


def setup_world(directory: Path) -> tuple[str, int]:
    with World.create(directory, seed=119, now=1_700_000_119) as world:
        user = world.create_user(first_name="Sara", language_code="fa")
        bot = world.create_user(first_name="Detector", is_bot=True, username="detector_bot")
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        token = world.issue_bot_token(bot["id"])
    return token, chat["id"]


def request(
    server: BotAPIServer, token: str, method: str, parameters: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    url = urlsplit(server.base_url)
    assert url.hostname is not None
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
    try:
        connection.request(
            "POST",
            f"/bot{token}/{method}",
            json.dumps(parameters),
            {"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "https://example.test/a",
            entity("url", "https://example.test/a", url="https://example.test/a"),
        ),
        (
            "www.example.test/x",
            entity("url", "www.example.test/x", url="https://www.example.test/x"),
        ),
        ("مثال.ایران", entity("url", "مثال.ایران", url="https://مثال.ایران")),
        (
            "team@example.test",
            entity("email_address", "team@example.test", email_address="team@example.test"),
        ),
        (
            "+98 (21) 1234-5678",
            entity("phone_number", "+98 (21) 1234-5678", phone_number="+982112345678"),
        ),
        ("@gramlab_1", entity("mention", "@gramlab_1")),
        ("#آزمایش_۱۲", entity("hashtag", "#آزمایش_۱۲")),
        ("$GRAM", entity("cashtag", "$GRAM")),
        ("/start@detector_bot", entity("bot_command", "/start@detector_bot")),
        ("4111 1111 1111 1111", entity("bank_card_number", "4111 1111 1111 1111")),
    ],
)
def test_each_candidate_family_and_canonical_metadata(raw: str, expected: dict[str, Any]) -> None:
    assert rich_message(paragraph(raw)) == paragraph(expected)
    assert rich_message(paragraph(raw, skip_entity_detection=False)) == paragraph(expected)
    assert rich_message(paragraph(raw, skip_entity_detection=True)) == paragraph(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "ftp:localhost",
        "http://-",
        "name..dots@localhost",
        "+12 34",
        "+12 )3456( 789",
        "@1starts_wrong",
        "#",
        "$usd",
        "/",
        "4111 1111 1111 1112",
        "پیش@example.testپس",
        "a#tag",
        "a/bot",
    ],
)
def test_invalid_near_candidates_remain_plain(raw: str) -> None:
    assert rich_message(paragraph(raw)) == paragraph(raw)


def test_punctuation_balancing_and_unicode_boundaries() -> None:
    raw = "(https://example.test/a_(b)). [www.example.test/x], واژه#نه؛ #بله!"
    assert rich_message(paragraph(raw)) == paragraph(
        [
            "(",
            entity("url", "https://example.test/a_(b)", url="https://example.test/a_(b)"),
            "). [",
            entity("url", "www.example.test/x", url="https://www.example.test/x"),
            "], واژه#نه؛ ",
            entity("hashtag", "#بله"),
            "!",
        ]
    )


def test_cleaning_happens_before_detection() -> None:
    assert rich_message(paragraph("\twww.exa\u030ample.test")) == paragraph(
        [" ", entity("url", "www.example.test", url="https://www.example.test")]
    )


def test_matched_url_quotes_are_retained_and_unmatched_closing_quotes_are_trimmed() -> None:
    raw = "https://example.test/\u2018x\u2019 https://example.test/y\u2019"
    assert rich_message(paragraph(raw)) == paragraph(
        [
            entity(
                "url",
                "https://example.test/\u2018x\u2019",
                url="https://example.test/\u2018x\u2019",
            ),
            " ",
            entity("url", "https://example.test/y", url="https://example.test/y"),
            "\u2019",
        ]
    )


CANDIDATES = (
    ("email_address", "a@example.test"),
    ("url", "example.test"),
    ("phone_number", "+1 202 555 0100"),
    ("mention", "@alpha"),
    ("hashtag", "#برچسب"),
    ("cashtag", "$GRAM"),
    ("bot_command", "/start"),
    ("bank_card_number", "4111-1111-1111-1111"),
)


@pytest.mark.parametrize("left,right", permutations(CANDIDATES, 2))
def test_every_candidate_precedence_pair_preserves_earliest_then_later(
    left: tuple[str, str], right: tuple[str, str]
) -> None:
    result = rich_message(paragraph(f"{left[1]} | {right[1]}"))["blocks"][0]["text"]
    assert isinstance(result, list)
    assert [part["type"] for part in result if isinstance(part, dict)] == [left[0], right[0]]


def test_styles_are_preserved_and_opaque_author_boundaries_are_not_scanned() -> None:
    raw = paragraph(
        [
            {"type": "bold", "text": "Go example.test"},
            {"type": "code", "text": "example.test"},
            {"type": "url", "text": "@visible", "url": "https://example.test"},
            {
                "type": "email_address",
                "text": "+1 202 555 0100",
                "email_address": "a@example.test",
            },
            {
                "type": "phone_number",
                "text": "www.example.test",
                "phone_number": "+12025550100",
            },
            {"type": "text_mention", "text": "#named", "user": 2},
            {
                "type": "custom_emoji",
                "custom_emoji_id": "1",
                "alternative_text": "example.test",
            },
            {"type": "button", "button": {"text": "example.test", "callback_data": "example.test"}},
        ]
    )
    resolved = rich_message(raw, mention_resolver=lambda value: {"user_id": value})
    assert resolved == paragraph(
        [
            {
                "type": "bold",
                "text": ["Go ", entity("url", "example.test", url="https://example.test")],
            },
            {"type": "code", "text": "example.test"},
            {"type": "url", "text": "@visible", "url": "https://example.test"},
            {
                "type": "email_address",
                "text": "+1 202 555 0100",
                "email_address": "a@example.test",
            },
            {
                "type": "phone_number",
                "text": "www.example.test",
                "phone_number": "+12025550100",
            },
            {"type": "text_mention", "text": "#named", "user_id": 2},
            {
                "type": "custom_emoji",
                "custom_emoji_id": "1",
                "alternative_text": "example.test",
            },
            {"type": "button", "button": {"text": "example.test", "callback_data": "example.test"}},
        ]
    )
    assert rich_message({"blocks": [{"type": "pre", "text": "example.test", "language": "x"}]}) == {
        "blocks": [{"type": "pre", "text": "example.test", "language": "x"}]
    }


def test_split_siblings_never_join_and_explicit_generated_nodes_round_trip() -> None:
    split = ["https://exa", "mple.test", {"type": "bold", "text": ["@al", "pha"]}]
    detected = rich_message(paragraph(split))
    assert detected["blocks"][0]["text"] != entity(
        "url", "https://example.test", url="https://example.test"
    )
    assert "https://example.test" not in json.dumps(detected)
    generated = paragraph(
        [
            entity("mention", "@alpha"),
            entity("hashtag", "#tag"),
            entity("cashtag", "$USD"),
            entity("bot_command", "/go"),
            entity("bank_card_number", "4111111111111111"),
        ],
        skip_entity_detection=True,
    )
    assert rich_message(generated) == paragraph(generated["blocks"][0]["text"])


def test_all_approved_text_roles_are_scanned_but_button_labels_remain_plain() -> None:
    blocks = [
        {"type": "paragraph", "text": "p.test"},
        {"type": "heading", "size": 2, "text": "h.test"},
        {"type": "footer", "text": "f.test"},
        {"type": "expandable_blockquote", "text": "e.test", "credit": "ec.test"},
        {"type": "pullquote", "text": "q.test", "credit": "qc.test"},
        {
            "type": "blockquote",
            "blocks": [{"type": "paragraph", "text": "b.test"}],
            "credit": "bc.test",
        },
        {
            "type": "details",
            "summary": "s.test",
            "blocks": [{"type": "paragraph", "text": "d.test"}],
        },
        {"type": "table", "caption": "t.test", "cells": [[{"text": "c.test"}]]},
        {"type": "list", "items": [{"blocks": [{"type": "paragraph", "text": "l.test"}]}]},
        {
            "type": "photo",
            "photo": "fixture",
            "caption": {"text": "pc.test", "credit": "pcc.test"},
        },
        {"type": "buttons", "buttons": [{"text": "button.test", "callback_data": "x"}]},
    ]
    result = rich_message({"blocks": blocks}, photo_resolver=lambda _: {"asset_id": 1})
    serialized = json.dumps(result, ensure_ascii=False)
    for hostname in (
        "p.test",
        "h.test",
        "f.test",
        "e.test",
        "ec.test",
        "q.test",
        "qc.test",
        "b.test",
        "bc.test",
        "s.test",
        "d.test",
        "t.test",
        "c.test",
        "l.test",
        "pc.test",
        "pcc.test",
    ):
        assert f'"url": "https://{hostname}"' in serialized
    assert '"text": "button.test"' in serialized
    assert '"url": "https://button.test"' not in serialized


def test_world_send_edit_noop_reopen_and_event_equality(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    token, chat_id = setup_world(directory)
    initial = paragraph("Visit example.test")
    expected_initial = paragraph(
        ["Visit ", entity("url", "example.test", url="https://example.test")]
    )
    with World.open(directory) as world:
        sent = world.send_rich_message(chat_id=chat_id, sender_id=2, rich_message=initial)
        assert sent["rich_message"] == expected_initial
        with pytest.raises(ValueError, match="MESSAGE_NOT_MODIFIED"):
            world.edit_message(
                chat_id=chat_id,
                message_id=1,
                bot_id=2,
                rich_message=paragraph("Visit example.test", skip_entity_detection=False),
            )
        edited = world.edit_message(
            chat_id=chat_id, message_id=1, bot_id=2, rich_message=paragraph("Mail a@example.test")
        )
        expected_edited = paragraph(
            ["Mail ", entity("email_address", "a@example.test", email_address="a@example.test")]
        )
        assert edited["rich_message"] == expected_edited
        plain = world.send_rich_message(
            chat_id=chat_id,
            sender_id=2,
            rich_message=paragraph("Later example.test", skip_entity_detection=True),
        )
        enriched = world.edit_message(
            chat_id=chat_id,
            message_id=plain["id"],
            bot_id=2,
            rich_message=paragraph("Later example.test"),
        )
        assert enriched["rich_message"] == paragraph(
            ["Later ", entity("url", "example.test", url="https://example.test")]
        )
    with World.open(directory) as world:
        assert world.get_message(chat_id, 1) == edited
        assert world.history(chat_id) == [edited, enriched]
        changes = world.client_changes(1, after=0)["changes"]
        assert [change["data"] for change in changes if change["type"] == "message.edited"] == [
            edited,
            enriched,
        ]
    assert token


def test_http_response_update_and_reopen_are_identical(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    token, chat_id = setup_world(directory)
    with BotAPIServer(directory) as server:
        status, response = request(
            server,
            token,
            "sendRichMessage",
            {"chat_id": chat_id, "rich_message": paragraph("Go example.test")},
        )
        assert status == 200
        canonical = response["result"]["rich_message"]
    with World.open(directory) as world:
        assert world.get_message(chat_id, 1)["rich_message"] == canonical
        assert world.client_changes(1, after=0)["changes"][0]["data"]["rich_message"] == canonical


def test_post_expansion_limit_failure_is_atomic(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    _, chat_id = setup_world(directory)
    # The input is under the node limit, while one generated node per leaf exceeds it.
    value = ["a.test" for _ in range(3_400)]
    with World.open(directory) as world:
        before = world.client_snapshot(1), world.events()
        with pytest.raises(ValueError, match="node limit"):
            world.send_rich_message(chat_id=chat_id, sender_id=2, rich_message=paragraph(value))
        assert (world.client_snapshot(1), world.events()) == before
        assert world.history(chat_id) == []


def test_post_expansion_utf8_and_depth_limits_are_rechecked() -> None:
    long_urls = [f"x.test/{'a' * 300}" for _ in range(110)]
    with pytest.raises(ValueError, match="UTF-8 byte limit"):
        rich_message(paragraph(long_urls))

    nested: Any = "x.test"
    for _ in range(29):
        nested = {"type": "bold", "text": nested}
    with pytest.raises(ValueError, match="nesting or node limit"):
        rich_message(paragraph(nested))


def test_input_is_not_mutated() -> None:
    payload = paragraph("\twww.example.test")
    pristine = copy.deepcopy(payload)
    rich_message(payload)
    assert payload == pristine


def test_maximum_plain_leaf_without_candidates_is_processed_unchanged() -> None:
    value = "a" * 34_996
    assert rich_message(paragraph(value)) == paragraph(value)
