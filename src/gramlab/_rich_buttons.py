"""Canonical rich-button occurrence traversal independent of native layout."""

from __future__ import annotations

import copy
from typing import Any

_WRAPPERS = frozenset(
    "bold italic underline strikethrough spoiler subscript superscript marked code".split()
)
_LINK_FIELDS = {"url": "url", "email_address": "email_address", "phone_number": "phone_number"}
_GENERATED_TEXT = frozenset(("mention", "hashtag", "cashtag", "bot_command", "bank_card_number"))
_ACTIONS = frozenset(("callback_data", "copy_text", "disabled"))

Path = list[str | int]
Occurrence = dict[str, Any]


def _mapping(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Unsupported canonical rich {context}")
    return value


def _array(value: Any, *, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"Unsupported canonical rich {context}")
    return value


def _fields(value: dict[str, Any], allowed: set[str], required: set[str], context: str) -> None:
    if value.keys() - allowed or required - value.keys():
        raise ValueError(f"Unsupported canonical rich {context}")


def _label(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if not value:
            raise ValueError("Unsupported canonical rich button label")
        return "".join(_label(item) for item in value)
    item = _mapping(value, context="button label")
    _fields(
        item,
        {"type", "custom_emoji_id", "alternative_text"},
        {"type", "custom_emoji_id", "alternative_text"},
        "button label",
    )
    if item["type"] != "custom_emoji" or not isinstance(item["alternative_text"], str):
        raise ValueError("Unsupported canonical rich button label")
    return item["alternative_text"]


def _button(value: Any, path: Path, result: list[Occurrence]) -> None:
    item = _mapping(value, context="button")
    _fields(item, {"text", "style", *_ACTIONS}, {"text"}, "button")
    if len(item.keys() & _ACTIONS) != 1:
        raise ValueError("Unsupported canonical rich button")
    if "style" in item and not isinstance(item["style"], str):
        raise ValueError("Unsupported canonical rich button")
    action = next(iter(item.keys() & _ACTIONS))
    if action == "callback_data" and not isinstance(item[action], str):
        raise ValueError("Unsupported canonical rich button")
    if action == "copy_text":
        copied = _mapping(item[action], context="button")
        _fields(copied, {"text"}, {"text"}, "button")
        if not isinstance(copied["text"], str):
            raise ValueError("Unsupported canonical rich button")
    if action == "disabled" and item[action] != {}:
        raise ValueError("Unsupported canonical rich button")
    result.append(
        {"path": list(path), "button": copy.deepcopy(item), "label": _label(item["text"])}
    )


def _text(value: Any, path: Path, result: list[Occurrence]) -> None:
    if isinstance(value, str):
        return
    if isinstance(value, list):
        if not value:
            raise ValueError("Unsupported canonical rich text")
        for index, child in enumerate(value):
            _text(child, [*path, index], result)
        return
    item = _mapping(value, context="text")
    kind = item.get("type")
    if kind == "button":
        _fields(item, {"type", "button"}, {"type", "button"}, "text")
        _button(item["button"], [*path, "button"], result)
        return
    if kind == "custom_emoji":
        _fields(
            item,
            {"type", "custom_emoji_id", "alternative_text"},
            {"type", "custom_emoji_id", "alternative_text"},
            "text",
        )
        if not isinstance(item["alternative_text"], str):
            raise ValueError("Unsupported canonical rich text")
        return
    if kind in _WRAPPERS:
        _fields(item, {"type", "text"}, {"type", "text"}, "text")
    elif kind in _LINK_FIELDS:
        metadata = _LINK_FIELDS[kind]
        _fields(item, {"type", "text", metadata}, {"type", "text", metadata}, "text")
    elif kind == "text_mention":
        _fields(item, {"type", "text", "user_id"}, {"type", "text", "user_id"}, "text")
    elif kind in _GENERATED_TEXT:
        _fields(item, {"type", "text"}, {"type", "text"}, "text")
    else:
        raise ValueError("Unsupported canonical rich text")
    _text(item["text"], [*path, "text"], result)


def _blocks(value: Any, path: Path, result: list[Occurrence]) -> None:
    blocks = _array(value, context="blocks")
    for index, value_block in enumerate(blocks):
        block = _mapping(value_block, context="block")
        block_path = [*path, index]
        kind = block.get("type")
        if kind == "paragraph":
            _fields(block, {"type", "text"}, {"type", "text"}, "block")
            _text(block["text"], [*block_path, "text"], result)
        elif kind == "heading":
            _fields(block, {"type", "text", "size"}, {"type", "text", "size"}, "block")
            _text(block["text"], [*block_path, "text"], result)
        elif kind == "pre":
            _fields(block, {"type", "text", "language"}, {"type", "text"}, "block")
            _text(block["text"], [*block_path, "text"], result)
        elif kind == "footer":
            _fields(block, {"type", "text"}, {"type", "text"}, "block")
            _text(block["text"], [*block_path, "text"], result)
        elif kind == "divider":
            _fields(block, {"type"}, {"type"}, "block")
        elif kind == "blockquote":
            _fields(block, {"type", "blocks", "credit"}, {"type", "blocks"}, "block")
            _blocks(block["blocks"], [*block_path, "blocks"], result)
            if "credit" in block:
                _text(block["credit"], [*block_path, "credit"], result)
        elif kind in ("expandable_blockquote", "pullquote"):
            _fields(block, {"type", "text", "credit"}, {"type", "text"}, "block")
            _text(block["text"], [*block_path, "text"], result)
            if "credit" in block:
                _text(block["credit"], [*block_path, "credit"], result)
        elif kind == "table":
            _fields(
                block,
                {
                    "type",
                    "cells",
                    "caption",
                    "is_bordered",
                    "is_striped",
                    "is_compact",
                },
                {"type", "cells"},
                "block",
            )
            if "caption" in block:
                _text(block["caption"], [*block_path, "caption"], result)
            rows = _array(block["cells"], context="table rows")
            for row_index, value_row in enumerate(rows):
                row = _array(value_row, context="table row")
                for column_index, value_cell in enumerate(row):
                    cell = _mapping(value_cell, context="table cell")
                    _fields(
                        cell,
                        {
                            "text",
                            "colspan",
                            "rowspan",
                            "align",
                            "valign",
                            "is_header",
                        },
                        {"align", "valign"},
                        "table cell",
                    )
                    if "text" in cell:
                        _text(
                            cell["text"],
                            [*block_path, "cells", row_index, column_index, "text"],
                            result,
                        )
        elif kind == "details":
            _fields(
                block,
                {"type", "summary", "blocks", "is_open"},
                {"type", "summary", "blocks"},
                "block",
            )
            _text(block["summary"], [*block_path, "summary"], result)
            _blocks(block["blocks"], [*block_path, "blocks"], result)
        elif kind == "list":
            _fields(block, {"type", "items"}, {"type", "items"}, "block")
            items = _array(block["items"], context="list items")
            for item_index, value_item in enumerate(items):
                item = _mapping(value_item, context="list item")
                _fields(
                    item,
                    {"label", "blocks", "type", "value", "has_checkbox", "is_checked"},
                    {"label", "blocks"},
                    "list item",
                )
                _blocks(item["blocks"], [*block_path, "items", item_index, "blocks"], result)
        elif kind == "buttons":
            _fields(block, {"type", "buttons", "align"}, {"type", "buttons"}, "block")
            buttons = _array(block["buttons"], context="button row")
            for button_index, value_button in enumerate(buttons):
                _button(value_button, [*block_path, "buttons", button_index], result)
        elif kind == "photo":
            _fields(block, {"type", "asset_id", "caption"}, {"type", "asset_id"}, "block")
            if "caption" in block:
                caption = _mapping(block["caption"], context="photo caption")
                _fields(caption, {"text", "credit"}, set(), "photo caption")
                for name in ("text", "credit"):
                    if name in caption:
                        _text(caption[name], [*block_path, "caption", name], result)
        else:
            raise ValueError("Unsupported canonical rich block")


def occurrences(content: dict[str, Any]) -> list[dict[str, Any]]:
    """Return detached canonical button occurrences in document order."""

    item = _mapping(content, context="content")
    _fields(item, {"blocks", "is_rtl"}, {"blocks"}, "content")
    result: list[Occurrence] = []
    _blocks(item["blocks"], ["blocks"], result)
    return result
