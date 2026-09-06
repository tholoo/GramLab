"""Observable world rich-message invariants, normalization and rejection boundaries."""

import copy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gramlab.world import World


def world_at(directory):
    world = World.create(directory, seed=9, now=123)
    world.create_user(first_name="Human")
    world.create_user(first_name="Bot", is_bot=True)
    world.open_private_chat(user_id=1, bot_id=2)
    return world


def rich(blocks, **fields):
    return {"blocks": blocks, "skip_entity_detection": True, **fields}


def test_list_items_are_normalized_through_the_world_boundary(tmp_path):
    payload = rich(
        [
            {
                "type": "list",
                "items": [
                    {
                        "blocks": [{"type": "paragraph", "text": "First"}],
                        "type": "A",
                        "value": 1,
                        "has_checkbox": True,
                        "is_checked": True,
                    },
                    {"blocks": [], "type": "i", "value": 4},
                ],
            }
        ]
    )
    expected = {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "label": "A.",
                        "blocks": [{"type": "paragraph", "text": "First"}],
                        "has_checkbox": True,
                        "is_checked": True,
                        "type": "A",
                        "value": 1,
                    },
                    {"label": "iv.", "blocks": [], "type": "i", "value": 4},
                ],
            }
        ]
    }

    with world_at(tmp_path / "world") as world:
        sent = world.send_rich_message(chat_id=1, sender_id=2, rich_message=payload)

    assert sent["rich_message"] == expected


def test_ordered_list_labels_cover_case_boundaries_and_signed_values(tmp_path):
    payload = rich(
        [
            {
                "type": "list",
                "items": [
                    {"blocks": [], "type": "a", "value": 1},
                    {"blocks": [], "type": "a", "value": 26},
                    {"blocks": [], "type": "a", "value": 27},
                    {"blocks": [], "type": "a", "value": 0},
                    {"blocks": [], "type": "A", "value": 26},
                    {"blocks": [], "type": "A", "value": 27},
                    {"blocks": [], "type": "A", "value": -5},
                    {"blocks": [], "type": "A"},
                    {"blocks": [], "type": "i", "value": 1},
                    {"blocks": [], "type": "i", "value": 0},
                    {"blocks": [], "type": "i", "value": 3999},
                    {"blocks": [], "type": "i", "value": 4000},
                    {"blocks": [], "type": "I", "value": 4},
                    {"blocks": [], "type": "I", "value": -8},
                    {"blocks": [], "type": "I", "value": 3999},
                    {"blocks": [], "type": "I", "value": 4000},
                    {"blocks": [], "type": "1"},
                    {"blocks": [], "type": "1", "value": -1},
                    {"blocks": [], "type": "1", "value": -(2**31)},
                    {"blocks": [], "type": "1", "value": 2**31 - 1},
                ],
            }
        ]
    )
    expected_items = [
        {"label": "a.", "blocks": [], "type": "a", "value": 1},
        {"label": "z.", "blocks": [], "type": "a", "value": 26},
        {"label": "aa.", "blocks": [], "type": "a", "value": 27},
        {"label": "0.", "blocks": [], "type": "a", "value": 0},
        {"label": "Z.", "blocks": [], "type": "A", "value": 26},
        {"label": "AA.", "blocks": [], "type": "A", "value": 27},
        {"label": "-5.", "blocks": [], "type": "A", "value": -5},
        {"label": "0.", "blocks": [], "type": "A", "value": 0},
        {"label": "i.", "blocks": [], "type": "i", "value": 1},
        {"label": "0.", "blocks": [], "type": "i", "value": 0},
        {"label": "mmmcmxcix.", "blocks": [], "type": "i", "value": 3999},
        {"label": "4000.", "blocks": [], "type": "i", "value": 4000},
        {"label": "IV.", "blocks": [], "type": "I", "value": 4},
        {"label": "-8.", "blocks": [], "type": "I", "value": -8},
        {"label": "MMMCMXCIX.", "blocks": [], "type": "I", "value": 3999},
        {"label": "4000.", "blocks": [], "type": "I", "value": 4000},
        {"label": "0.", "blocks": [], "type": "1", "value": 0},
        {"label": "-1.", "blocks": [], "type": "1", "value": -1},
        {"label": "-2147483648.", "blocks": [], "type": "1", "value": -(2**31)},
        {"label": "2147483647.", "blocks": [], "type": "1", "value": 2**31 - 1},
    ]

    with world_at(tmp_path / "world") as world:
        sent = world.send_rich_message(chat_id=1, sender_id=2, rich_message=payload)

    assert sent["rich_message"] == {"blocks": [{"type": "list", "items": expected_items}]}


def test_list_marker_and_checkbox_changes_create_visible_edits(tmp_path):
    blocks = [{"type": "paragraph", "text": "Same body"}]
    initial = rich(
        [
            {
                "type": "list",
                "items": [{"blocks": blocks, "type": "a", "value": 1}],
            }
        ]
    )
    changed = rich(
        [
            {
                "type": "list",
                "items": [
                    {
                        "blocks": blocks,
                        "type": "A",
                        "value": 1,
                        "has_checkbox": True,
                        "is_checked": True,
                    }
                ],
            }
        ]
    )

    with world_at(tmp_path / "world") as world:
        sent = world.send_rich_message(chat_id=1, sender_id=2, rich_message=initial)
        edited = world.edit_message(
            chat_id=1,
            message_id=sent["id"],
            bot_id=2,
            rich_message=changed,
        )
        assert edited["rich_message"] == {
            "blocks": [
                {
                    "type": "list",
                    "items": [
                        {
                            "label": "A.",
                            "blocks": [{"type": "paragraph", "text": "Same body"}],
                            "has_checkbox": True,
                            "is_checked": True,
                            "type": "A",
                            "value": 1,
                        }
                    ],
                }
            ]
        }
        assert [change["type"] for change in world.client_changes(1, after=0)["changes"]] == [
            "message.created",
            "message.edited",
        ]


def test_unordered_lists_normalize_flags_and_recurse_through_nested_blocks(tmp_path):
    payload = rich(
        [
            {
                "type": "list",
                "items": [
                    {
                        "blocks": [
                            {
                                "type": "blockquote",
                                "credit": {"type": "italic", "text": "نویسنده"},
                                "blocks": [
                                    {
                                        "type": "list",
                                        "items": [
                                            {
                                                "blocks": [
                                                    {
                                                        "type": "paragraph",
                                                        "text": [
                                                            "راست ",
                                                            {"type": "bold", "text": "left"},
                                                        ],
                                                    }
                                                ],
                                                "type": "I",
                                                "value": 9,
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                        "value": -(2**31),
                        "type": "",
                        "has_checkbox": False,
                        "is_checked": True,
                    },
                    {
                        "blocks": [],
                        "value": 2**31 - 1,
                        "has_checkbox": True,
                        "is_checked": False,
                    },
                    {"blocks": [], "is_checked": True},
                    {
                        "blocks": [{"type": "footer", "text": "پایان end"}],
                        "has_checkbox": True,
                        "is_checked": True,
                    },
                ],
            }
        ],
        is_rtl=True,
    )
    expected = {
        "blocks": [
            {
                "type": "list",
                "items": [
                    {
                        "label": "•",
                        "blocks": [
                            {
                                "type": "blockquote",
                                "credit": {"type": "italic", "text": "نویسنده"},
                                "blocks": [
                                    {
                                        "type": "list",
                                        "items": [
                                            {
                                                "label": "IX.",
                                                "blocks": [
                                                    {
                                                        "type": "paragraph",
                                                        "text": [
                                                            "راست ",
                                                            {"type": "bold", "text": "left"},
                                                        ],
                                                    }
                                                ],
                                                "type": "I",
                                                "value": 9,
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    },
                    {"label": "•", "blocks": [], "has_checkbox": True},
                    {"label": "•", "blocks": []},
                    {
                        "label": "•",
                        "blocks": [{"type": "footer", "text": "پایان end"}],
                        "has_checkbox": True,
                        "is_checked": True,
                    },
                ],
            }
        ],
        "is_rtl": True,
    }
    pristine = copy.deepcopy(payload)

    with world_at(tmp_path / "world") as world:
        sent = world.send_rich_message(chat_id=1, sender_id=2, rich_message=payload)
        assert payload == pristine
        assert sent["rich_message"] == expected
        payload["blocks"].clear()
        sent["rich_message"]["blocks"].clear()
        assert world.get_message(1, 1)["rich_message"] == expected


@pytest.mark.parametrize(
    "block",
    [
        {"type": "list", "items": []},
        {"type": "list", "items": None},
        {"type": "list", "items": {}},
        {"type": "list", "items": ["item"]},
        {"type": "list", "items": [{}]},
        {"type": "list", "items": [{"blocks": None}]},
        {"type": "list", "items": [{"blocks": "text"}]},
        {"type": "list", "items": [{"blocks": [], "label": "•"}]},
        {"type": "list", "items": [{"blocks": [], "unknown": True}]},
        {"type": "list", "items": [{"blocks": [], "type": None}]},
        {"type": "list", "items": [{"blocks": [], "type": True}]},
        {"type": "list", "items": [{"blocks": [], "type": "x"}]},
        {"type": "list", "items": [{"blocks": [], "type": "aa"}]},
        {"type": "list", "items": [{"blocks": [], "value": None}]},
        {"type": "list", "items": [{"blocks": [], "value": True}]},
        {"type": "list", "items": [{"blocks": [], "value": "1"}]},
        {"type": "list", "items": [{"blocks": [], "value": -(2**31) - 1}]},
        {"type": "list", "items": [{"blocks": [], "value": 2**31}]},
        {"type": "list", "items": [{"blocks": [], "has_checkbox": 1}]},
        {"type": "list", "items": [{"blocks": [], "is_checked": "true"}]},
        {
            "type": "list",
            "items": [{"blocks": []}, {"blocks": [], "type": "1"}],
        },
        {
            "type": "list",
            "items": [{"blocks": [], "type": ""}, {"blocks": [], "type": "A"}],
        },
        {"type": "list", "items": [{"blocks": []}], "unknown": True},
    ],
)
def test_invalid_list_input_and_edits_leave_world_state_and_ids_unchanged(tmp_path, block):
    with world_at(tmp_path / "world") as world:
        message = world.send_rich_message(
            chat_id=1,
            sender_id=2,
            rich_message=rich([{"type": "paragraph", "text": "Original"}]),
        )
        before = (
            world.history(1),
            world.client_snapshot(1, version=2),
            world.client_changes(1, after=0),
            world.events(),
        )
        with pytest.raises(ValueError):
            world.send_rich_message(chat_id=1, sender_id=2, rich_message=rich([block]))
        with pytest.raises(ValueError):
            world.edit_message(
                chat_id=1,
                message_id=message["id"],
                bot_id=2,
                rich_message=rich([block]),
            )
        assert (
            world.history(1),
            world.client_snapshot(1, version=2),
            world.client_changes(1, after=0),
            world.events(),
        ) == before
        assert world.send_message(chat_id=1, sender_id=2, text="After rejection")["id"] == 2


def test_list_expansion_cannot_exceed_existing_node_budget(tmp_path):
    payload = rich([{"type": "list", "items": [{"blocks": []} for _ in range(2000)]}])
    with world_at(tmp_path / "world") as world:
        before = world.client_snapshot(1, version=2), world.events()
        with pytest.raises(ValueError, match="GRAMLAB_UNSUPPORTED: rich content node limit"):
            world.send_rich_message(chat_id=1, sender_id=2, rich_message=payload)
        assert (world.client_snapshot(1, version=2), world.events()) == before


def test_canonical_table_defaults_flags_and_detached_inputs(tmp_path):
    original = rich(
        [
            {
                "type": "table",
                "cells": [
                    [
                        {"text": "Header", "is_header": True, "rowspan": 0, "colspan": 1},
                        {"is_header": False, "text": ""},
                        {
                            "text": "Value",
                            "align": "right",
                            "valign": "bottom",
                            "rowspan": 3,
                            "colspan": 2,
                        },
                    ]
                ],
                "is_bordered": False,
                "is_striped": False,
                "is_compact": False,
                "caption": "",
            },
            {"type": "pre", "text": "code", "language": ""},
            {
                "type": "details",
                "summary": "",
                "is_open": False,
                "blocks": [{"type": "paragraph", "text": "More"}],
            },
        ],
        is_rtl=False,
    )
    expected = {
        "blocks": [
            {
                "type": "table",
                "cells": [
                    [
                        {
                            "text": "Header",
                            "is_header": True,
                            "align": "center",
                            "valign": "middle",
                        },
                        {"align": "left", "valign": "middle"},
                        {
                            "text": "Value",
                            "align": "right",
                            "valign": "bottom",
                            "rowspan": 3,
                            "colspan": 2,
                        },
                    ]
                ],
            },
            {"type": "pre", "text": "code"},
            {"type": "details", "summary": "", "blocks": [{"type": "paragraph", "text": "More"}]},
        ]
    }
    pristine = copy.deepcopy(original)
    with world_at(tmp_path / "world") as world:
        sent = world.send_rich_message(chat_id=1, sender_id=2, rich_message=original)
        assert original == pristine
        assert sent["rich_message"] == expected
        original["blocks"].clear()
        sent["rich_message"]["blocks"].clear()
        assert world.get_message(1, 1)["rich_message"] == expected
        with pytest.raises(ValueError, match="MESSAGE_NOT_MODIFIED"):
            world.edit_message(
                chat_id=1,
                message_id=1,
                bot_id=2,
                rich_message={**expected, "skip_entity_detection": True},
            )
        assert world.client_snapshot(1, version=2)["message_position"] == 1


@pytest.mark.parametrize(
    "block",
    [
        {"type": "heading", "size": 0, "text": "x"},
        {"type": "heading", "size": 7, "text": "x"},
        {"type": "heading", "size": "2", "text": "x"},
        {"type": "paragraph", "text": []},
        {"type": "paragraph", "text": ["x", None]},
        {"type": "paragraph", "text": {"type": "bold"}},
        {"type": "paragraph", "text": {"type": "bold", "text": "x", "url": "ignored"}},
        {"type": "paragraph", "text": "x\x00y"},
        {"type": "pre", "text": "x", "language": 1},
        {"type": "divider", "text": "ignored"},
        {"type": "details", "summary": "x", "blocks": [], "is_open": True},
        {"type": "details", "summary": "x", "blocks": [{"type": "divider"}], "is_open": 1},
        {"type": "table", "cells": []},
        {"type": "table", "cells": [[]]},
        {"type": "table", "cells": [[{"text": "x", "align": "justify"}]]},
        {"type": "table", "cells": [[{"text": "x", "valign": False}]]},
        {"type": "table", "cells": [[{"text": "x", "rowspan": -1}]]},
        {"type": "table", "cells": [[{"text": "x", "colspan": True}]]},
        {"type": "table", "cells": [[{"text": "x", "rowspan": 2**31}]]},
        {"type": "table", "cells": [[{"text": "x", "rowspan": 101}]]},
    ],
)
def test_invalid_nested_content_never_allocates_ids_or_events(tmp_path, block):
    with world_at(tmp_path / "world") as world:
        before = world.client_snapshot(1, version=2), world.events()
        with pytest.raises(ValueError):
            world.send_rich_message(chat_id=1, sender_id=2, rich_message=rich([block]))
        assert (world.client_snapshot(1, version=2), world.events()) == before
        assert world.send_message(chat_id=1, sender_id=2, text="After rejection")["id"] == 1


def test_bounded_tree_rejection_preserves_world(tmp_path):
    deep = "x"
    for _ in range(40):
        deep = {"type": "bold", "text": deep}
    with world_at(tmp_path / "world") as world:
        for text in (deep, ["x"] * 10_001, "🌍" * 16_384):
            with pytest.raises(ValueError, match="GRAMLAB_UNSUPPORTED"):
                world.send_rich_message(
                    chat_id=1, sender_id=2, rich_message=rich([{"type": "paragraph", "text": text}])
                )
        assert world.history(1) == []
        assert world.client_snapshot(1, version=2)["message_position"] == 0


def test_rich_messages_world_scope_and_bot_authority(tmp_path):
    with world_at(tmp_path / "first") as first, world_at(tmp_path / "second") as second:
        body = rich([{"type": "paragraph", "text": "Only first world"}])
        with pytest.raises(ValueError, match="Only bots"):
            first.send_rich_message(chat_id=1, sender_id=1, rich_message=body)
        message = first.send_rich_message(chat_id=1, sender_id=2, rich_message=body)
        assert first.client_changes(1, after=0)["changes"][0]["data"] == message
        assert second.history(1) == []
        assert second.client_changes(1, after=0)["changes"] == []


@settings(max_examples=25)
@given(st.text(alphabet=st.characters(blacklist_categories=("Cs", "Cc")), min_size=1, max_size=80))
def test_unicode_nested_text_round_trip_uses_complete_content(tmp_path_factory, text):
    directory = tmp_path_factory.mktemp("unicode") / "world"
    payload = rich(
        [
            {
                "type": "paragraph",
                "text": [text, {"type": "bold", "text": {"type": "italic", "text": text}}],
            }
        ],
        is_rtl=True,
    )
    with world_at(directory) as world:
        expected = world.send_rich_message(chat_id=1, sender_id=2, rich_message=payload)
        assert expected["rich_message"] == {"blocks": payload["blocks"], "is_rtl": True}
    with World.open(directory) as world:
        assert world.history(1) == [expected]
        assert world.client_snapshot(1, version=2)["messages"] == [expected]


@pytest.mark.parametrize(
    "cells",
    [
        [[{"text": "Narrow"}], [{"text": "Wider", "colspan": 2}]],
        [[{"text": "Huge", "colspan": 100, "rowspan": 100}, {"text": "Overflow"}]],
    ],
)
def test_unsupported_table_extent_is_rejected_before_mutation(tmp_path, cells):
    with world_at(tmp_path / "world") as world:
        with pytest.raises(ValueError, match="GRAMLAB_UNSUPPORTED: table layout extent"):
            world.send_rich_message(
                chat_id=1, sender_id=2, rich_message=rich([{"type": "table", "cells": cells}])
            )
        assert world.history(1) == []
        assert world.client_snapshot(1, version=2)["message_position"] == 0


def test_canonical_defaults_cannot_exceed_bridge_node_budget(tmp_path):
    # Input cells are small; adding the required output alignments crosses the budget.
    with world_at(tmp_path / "world") as world:
        with pytest.raises(ValueError, match="GRAMLAB_UNSUPPORTED: rich content node limit"):
            world.send_rich_message(
                chat_id=1,
                sender_id=2,
                rich_message=rich([{"type": "table", "cells": [[{} for _ in range(2200)]]}]),
            )
        assert world.history(1) == []
