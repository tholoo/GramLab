"""Canonical rich-button occurrence traversal stays independent of native layout."""

import copy
from pathlib import Path
from typing import Any

import pytest

from gramlab._rich_buttons import occurrences
from gramlab.world import World


def button(text: Any, payload: str) -> dict[str, Any]:
    return {"type": "button", "button": {"text": text, "callback_data": payload}}


def test_occurrences_walk_every_admitted_container_in_canonical_order(tmp_path: Path) -> None:
    emoji = {
        "type": "custom_emoji",
        "custom_emoji_id": "7",
        "alternative_text": "",
    }
    payload = {
        "skip_entity_detection": True,
        "blocks": [
            {"type": "paragraph", "text": ["p", button("paragraph", "p")]},
            {
                "type": "heading",
                "size": 2,
                "text": {"type": "bold", "text": button("heading", "h")},
            },
            {"type": "pre", "text": button("pre", "pre")},
            {"type": "footer", "text": button("footer", "footer")},
            {"type": "divider"},
            {
                "type": "blockquote",
                "blocks": [{"type": "paragraph", "text": button("quote body", "qb")}],
                "credit": button("quote credit", "qc"),
            },
            {
                "type": "expandable_blockquote",
                "text": button("expandable body", "eb"),
                "credit": button("expandable credit", "ec"),
            },
            {
                "type": "pullquote",
                "text": button("pull body", "pb"),
                "credit": button("pull credit", "pc"),
            },
            {
                "type": "table",
                "caption": button("table caption", "tc"),
                "cells": [
                    [{"text": button("cell one", "c1")}],
                    [{"text": ["x", button("cell two", "c2")]}],
                ],
            },
            {
                "type": "details",
                "summary": button("details summary", "ds"),
                "blocks": [{"type": "paragraph", "text": button("hidden body", "db")}],
                "is_open": False,
            },
            {
                "type": "list",
                "items": [{"blocks": [{"type": "paragraph", "text": button("list body", "lb")}]}],
            },
            {
                "type": "buttons",
                "buttons": [
                    {
                        "text": ["same", [emoji, {**emoji, "alternative_text": " alt"}]],
                        "style": "PRIMARY",
                        "callback_data": "duplicate",
                    },
                    {"text": "same", "callback_data": "duplicate"},
                ],
            },
            {
                "type": "photo",
                "photo": {"type": "photo", "media": "attach://photo"},
                "caption": {
                    "text": button("photo text", "pt"),
                    "credit": button("photo credit", "pc2"),
                },
            },
        ],
    }
    fixture = Path("tests/assets/custom-emoji")
    with World.create(tmp_path / "world", seed=7, now=20) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        world.register_custom_emoji(
            request_id="emoji",
            main=(fixture / "emoji-static.webp").read_bytes(),
            thumbnail=(fixture / "emoji-thumbnail.webp").read_bytes(),
            fallback="catalog fallback",
            custom_emoji_id="7",
        )
        message = world.send_rich_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            rich_message=payload,
            uploads={"photo": Path("tests/assets/rich-media/photo-square-16x16.png").read_bytes()},
        )

    content = message["rich_message"]
    before = copy.deepcopy(content)
    found = occurrences(content)
    assert [(item["path"], item["label"]) for item in found] == [
        (["blocks", 0, "text", 1, "button"], "paragraph"),
        (["blocks", 1, "text", "text", "button"], "heading"),
        (["blocks", 2, "text", "button"], "pre"),
        (["blocks", 3, "text", "button"], "footer"),
        (["blocks", 5, "blocks", 0, "text", "button"], "quote body"),
        (["blocks", 5, "credit", "button"], "quote credit"),
        (["blocks", 6, "text", "button"], "expandable body"),
        (["blocks", 6, "credit", "button"], "expandable credit"),
        (["blocks", 7, "text", "button"], "pull body"),
        (["blocks", 7, "credit", "button"], "pull credit"),
        (["blocks", 8, "caption", "button"], "table caption"),
        (["blocks", 8, "cells", 0, 0, "text", "button"], "cell one"),
        (["blocks", 8, "cells", 1, 0, "text", 1, "button"], "cell two"),
        (["blocks", 9, "summary", "button"], "details summary"),
        (["blocks", 9, "blocks", 0, "text", "button"], "hidden body"),
        (["blocks", 10, "items", 0, "blocks", 0, "text", "button"], "list body"),
        (["blocks", 11, "buttons", 0], "same alt"),
        (["blocks", 11, "buttons", 1], "same"),
        (["blocks", 12, "caption", "text", "button"], "photo text"),
        (["blocks", 12, "caption", "credit", "button"], "photo credit"),
    ]
    assert found[16]["button"] == {
        "text": [
            "same",
            [
                {"type": "custom_emoji", "custom_emoji_id": "7", "alternative_text": ""},
                {
                    "type": "custom_emoji",
                    "custom_emoji_id": "7",
                    "alternative_text": " alt",
                },
            ],
        ],
        "style": "primary",
        "callback_data": "duplicate",
    }
    found[0]["button"]["text"] = "changed"
    found[0]["path"].append("changed")
    assert content == before


@pytest.mark.parametrize(
    "content",
    [
        {"blocks": [{"type": "future", "text": button("lost", "x")}]},
        {"blocks": [{"type": "paragraph", "text": {"type": "future", "text": "x"}}]},
        {
            "blocks": [
                {
                    "type": "buttons",
                    "buttons": [
                        {"text": {"type": "bold", "text": "not canonical"}, "disabled": {}}
                    ],
                }
            ]
        },
    ],
)
def test_occurrences_reject_unsupported_canonical_structures(content: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="Unsupported canonical rich"):
        occurrences(content)
