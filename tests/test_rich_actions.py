"""Public World boundaries for rich callback, copy, and disabled buttons."""

import copy

import pytest

from gramlab.world import World


def world_at(directory):
    world = World.create(directory, seed=14, now=200)
    world.create_user(first_name="Human")
    world.create_user(first_name="Bot", is_bot=True)
    world.create_user(first_name="Other", is_bot=True)
    world.open_private_chat(user_id=1, bot_id=2)
    world.open_private_chat(user_id=1, bot_id=3)
    return world


def rich(blocks):
    return {"blocks": blocks, "skip_entity_detection": True}


def action_blocks():
    return [
        {
            "type": "buttons",
            "buttons": [
                {
                    "text": "Choose\tamber",
                    "style": "PrImArY",
                    "callback_data": "pick:\t\u202eamber",
                },
                {
                    "text": ["Copy ", ["nested", " label"]],
                    "style": "DEFAULT",
                    "copy_text": {"text": "Amber\t42"},
                },
                {"text": "Later", "style": "", "disabled": {}},
            ],
        },
        {
            "type": "buttons",
            "buttons": [{"text": "Danger", "style": "DANGER", "callback_data": "danger"}],
            "align": "left",
        },
        {
            "type": "paragraph",
            "text": [
                "Before ",
                {
                    "type": "button",
                    "button": {
                        "text": ["Open", " callback"],
                        "style": "LINK",
                        "callback_data": "💡" * 16,
                    },
                },
            ],
        },
        {
            "type": "details",
            "summary": {"type": "button", "button": {"text": "Done", "disabled": {}}},
            "blocks": [
                {
                    "type": "buttons",
                    "buttons": [
                        {"text": "Safe", "style": "SUCCESS", "copy_text": {"text": "💡" * 256}}
                    ],
                    "align": "right",
                }
            ],
        },
    ]


def canonical_blocks():
    return [
        {
            "type": "buttons",
            "buttons": [
                {
                    "text": "Choose amber",
                    "style": "primary",
                    "callback_data": "pick:\t\u202eamber",
                },
                {
                    "text": ["Copy ", ["nested", " label"]],
                    "copy_text": {"text": "Amber 42"},
                },
                {"text": "Later", "disabled": {}},
            ],
        },
        {
            "type": "buttons",
            "buttons": [{"text": "Danger", "style": "danger", "callback_data": "danger"}],
            "align": "left",
        },
        {
            "type": "paragraph",
            "text": [
                "Before ",
                {
                    "type": "button",
                    "button": {
                        "text": ["Open", " callback"],
                        "style": "link",
                        "callback_data": "💡" * 16,
                    },
                },
            ],
        },
        {
            "type": "details",
            "summary": {"type": "button", "button": {"text": "Done", "disabled": {}}},
            "blocks": [
                {
                    "type": "buttons",
                    "buttons": [
                        {"text": "Safe", "style": "success", "copy_text": {"text": "💡" * 256}}
                    ],
                    "align": "right",
                }
            ],
        },
    ]


def test_rich_actions_normalize_detach_edit_and_reopen(tmp_path):
    directory = tmp_path / "world"
    payload = rich(action_blocks())
    expected_rich = {"blocks": canonical_blocks()}
    pristine = copy.deepcopy(payload)
    with world_at(directory) as world:
        sent = world.send_rich_message(chat_id=1, sender_id=2, rich_message=payload)
        expected = {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 200,
            "text": "",
            "rich_message": expected_rich,
        }
        assert sent == expected
        assert payload == pristine
        callback = world.create_callback(
            user_id=1,
            chat_id=1,
            message_id=1,
            data="pick:\t\u202eamber",
            request_id="rich-action",
        )
        assert callback["message"] == expected
        assert world.get_callback(user_id=1, callback_id=callback["id"])["message"] == expected

        payload["blocks"][0]["buttons"][0]["text"] = "mutated input"
        payload["blocks"][0]["buttons"][1]["copy_text"]["text"] = "mutated copy"
        sent["rich_message"]["blocks"][0]["buttons"][0]["callback_data"] = "mutated output"
        sent["rich_message"]["blocks"][0]["buttons"][1]["text"][1][0] = "mutated label"
        assert world.get_message(1, 1) == expected
        assert world.get_callback(user_id=1, callback_id=callback["id"])["message"] == expected

        before_invalid = world.client_snapshot(1, version=2), world.events()
        with pytest.raises(ValueError):
            world.edit_message(
                chat_id=1,
                message_id=1,
                bot_id=2,
                rich_message=rich(
                    [{"type": "buttons", "buttons": [{"text": "invalid", "disabled": []}]}]
                ),
            )
        assert (world.client_snapshot(1, version=2), world.events()) == before_invalid
        with pytest.raises(ValueError, match="MESSAGE_NOT_MODIFIED"):
            world.edit_message(
                chat_id=1, message_id=1, bot_id=2, rich_message=rich(action_blocks())
            )
        assert world.client_changes(1, after=0)["changes"] == [
            {"position": 1, "type": "message.created", "data": expected}
        ]
    with World.open(directory) as world:
        assert world.history(1) == [expected]
        assert [
            event["data"] for event in world.events() if event["type"] == "message.created"
        ] == [expected]


def test_eight_button_fill_row_omits_empty_alignment_and_default_styles(tmp_path):
    buttons = [
        {"text": "", "style": "DeFaUlT" if index % 2 else "", "callback_data": str(index)}
        for index in range(8)
    ]
    expected_buttons = [{"text": "", "callback_data": str(index)} for index in range(8)]
    with world_at(tmp_path / "world") as world:
        sent = world.send_rich_message(
            chat_id=1,
            sender_id=2,
            rich_message=rich([{"type": "buttons", "buttons": buttons, "align": ""}]),
        )

    assert sent["rich_message"] == {"blocks": [{"type": "buttons", "buttons": expected_buttons}]}


@pytest.mark.parametrize(
    "block",
    [
        {"type": "buttons", "buttons": []},
        {"type": "buttons", "buttons": [{"text": "x", "disabled": {}}] * 9},
        {"type": "buttons", "buttons": [{"text": "x", "disabled": {}}], "align": "LEFT"},
        {"type": "buttons", "buttons": [{"text": "x", "disabled": {}}], "align": True},
        {"type": "buttons", "buttons": [{}]},
        {"type": "buttons", "buttons": [{"text": "x"}]},
        {"type": "buttons", "buttons": [{"text": {"type": "bold", "text": "x"}, "disabled": {}}]},
        {"type": "buttons", "buttons": [{"text": [], "disabled": {}}]},
        {"type": "buttons", "buttons": [{"text": ["x", []], "disabled": {}}]},
        {"type": "buttons", "buttons": [{"text": "x", "callback_data": ""}]},
        {"type": "buttons", "buttons": [{"text": "x", "callback_data": "💡" * 16 + "a"}]},
        {"type": "buttons", "buttons": [{"text": "x", "callback_data": 1}]},
        {"type": "buttons", "buttons": [{"text": "x", "callback_data": "a", "disabled": {}}]},
        {"type": "buttons", "buttons": [{"text": "x", "copy_text": {}}]},
        {"type": "buttons", "buttons": [{"text": "x", "copy_text": {"text": ""}}]},
        {"type": "buttons", "buttons": [{"text": "x", "copy_text": {"text": "x" * 257}}]},
        {"type": "buttons", "buttons": [{"text": "x", "copy_text": {"text": "\u202e"}}]},
        {"type": "buttons", "buttons": [{"text": "x", "copy_text": {"text": "x", "extra": 1}}]},
        {"type": "buttons", "buttons": [{"text": "x", "disabled": {"value": True}}]},
        {"type": "buttons", "buttons": [{"text": "x", "disabled": []}]},
        {"type": "buttons", "buttons": [{"text": "x", "style": "unknown", "disabled": {}}]},
        {
            "type": "buttons",
            "buttons": [{"text": "x", "style": "link", "copy_text": {"text": "x"}}],
        },
        {"type": "buttons", "buttons": [{"text": "x", "style": 1, "disabled": {}}]},
        {"type": "buttons", "buttons": [{"text": "x", "disabled": {}, "extra": True}]},
        {"type": "paragraph", "text": {"type": "button", "button": None}},
        {
            "type": "paragraph",
            "text": {"type": "button", "button": {"text": "x", "disabled": {}}, "extra": 1},
        },
    ],
)
def test_invalid_rich_actions_leave_world_unchanged(tmp_path, block):
    with world_at(tmp_path / "world") as world:
        before = world.client_snapshot(1, version=2), world.events()
        with pytest.raises(ValueError):
            world.send_rich_message(chat_id=1, sender_id=2, rich_message=rich([block]))
        assert (world.client_snapshot(1, version=2), world.events()) == before


def test_rich_action_existing_limits_and_ownership_remain_enforced(tmp_path):
    with world_at(tmp_path / "world") as world:
        with pytest.raises(ValueError, match="control-character"):
            world.send_rich_message(
                chat_id=1,
                sender_id=2,
                rich_message=rich(
                    [{"type": "buttons", "buttons": [{"text": "x", "callback_data": "a\x01b"}]}]
                ),
            )
        with pytest.raises(ValueError, match="UTF-8 byte limit"):
            world.send_rich_message(
                chat_id=1,
                sender_id=2,
                rich_message=rich(
                    [{"type": "buttons", "buttons": [{"text": "x" * 65_500, "disabled": {}}]}]
                ),
            )
        with pytest.raises(ValueError, match="Only bots"):
            world.send_rich_message(
                chat_id=1,
                sender_id=1,
                rich_message=rich(
                    [{"type": "buttons", "buttons": [{"text": "x", "disabled": {}}]}]
                ),
            )
        sent = world.send_rich_message(
            chat_id=1,
            sender_id=2,
            rich_message=rich([{"type": "buttons", "buttons": [{"text": "x", "disabled": {}}]}]),
        )
        with pytest.raises(ValueError, match="not available"):
            world.edit_message(
                chat_id=1,
                message_id=sent["id"],
                bot_id=3,
                rich_message=rich(
                    [{"type": "buttons", "buttons": [{"text": "y", "disabled": {}}]}]
                ),
            )
