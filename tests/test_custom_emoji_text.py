import pytest

from gramlab._emoji_text import is_single_emoji
from gramlab.entities import formatting_entities
from gramlab.rich_messages import rich_message


@pytest.mark.parametrize(
    "text",
    ["🙂", "❤", "❤️", "2⃣", "2️⃣", "👋🏽", "🇮🇷", "👩🏼‍❤‍💋‍👩🏻️", "👩‍🤝‍👨"],
)
def test_pinned_tdlib_single_emoji_policy(text: str) -> None:
    assert is_single_emoji(text)


@pytest.mark.parametrize("text", ["", "a", "🙂🙂", "👩‍a‍👨", "❤️️"])
def test_pinned_tdlib_policy_rejects_non_single_emoji(text: str) -> None:
    assert not is_single_emoji(text)


def test_ordinary_entity_normalizes_id_utf16_and_nested_style() -> None:
    assert formatting_entities(
        "الف🙂x",
        [
            {"type": "bold", "offset": 3, "length": 2},
            {"type": "custom_emoji", "offset": 3, "length": 2, "custom_emoji_id": 7},
            {"type": "custom_emoji", "offset": 3, "length": 2, "custom_emoji_id": "7"},
        ],
    ) == [
        {"type": "custom_emoji", "offset": 3, "length": 2, "custom_emoji_id": "7"},
        {"type": "bold", "offset": 3, "length": 2},
    ]


@pytest.mark.parametrize("identifier", [True, 0, -1, "01", "+1", " 1", 2**63])
def test_ordinary_entity_rejects_invalid_id(identifier: object) -> None:
    with pytest.raises(ValueError, match="Custom emoji ID"):
        formatting_entities(
            "🙂",
            [{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": identifier}],
        )


def test_rich_custom_emoji_preserves_cleaned_alternative_and_button_leaf() -> None:
    value = rich_message(
        {
            "skip_entity_detection": True,
            "blocks": [
                {
                    "type": "paragraph",
                    "text": {
                        "type": "custom_emoji",
                        "custom_emoji_id": 9,
                        "alternative_text": "x\t\u202e",
                    },
                },
                {
                    "type": "buttons",
                    "buttons": [
                        {
                            "text": [
                                "A",
                                {
                                    "type": "custom_emoji",
                                    "custom_emoji_id": "9",
                                    "alternative_text": "🙂",
                                },
                            ],
                            "disabled": {},
                        }
                    ],
                },
            ],
        }
    )
    assert value["blocks"][0]["text"] == {
        "type": "custom_emoji",
        "custom_emoji_id": "9",
        "alternative_text": "x ",
    }
    assert value["blocks"][1]["buttons"][0]["text"][1]["custom_emoji_id"] == "9"


def test_nested_custom_emoji_checks_every_active_ancestor() -> None:
    with pytest.raises(ValueError, match="cannot overlap"):
        formatting_entities(
            "👩‍👩",
            [
                {"type": "custom_emoji", "offset": 0, "length": 5, "custom_emoji_id": 1},
                {"type": "bold", "offset": 0, "length": 5},
                {"type": "custom_emoji", "offset": 3, "length": 2, "custom_emoji_id": 2},
            ],
        )
