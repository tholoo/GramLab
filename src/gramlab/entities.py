"""Independently specified Bot API formatting ranges; no client schema dependency."""

from typing import Any

from gramlab._emoji_text import is_single_emoji


def canonical_custom_emoji_id(value: Any) -> str:
    if type(value) is int:
        number = value
    elif (
        isinstance(value, str)
        and value.isascii()
        and value.isdecimal()
        and (value == "0" or not value.startswith("0"))
    ):
        number = int(value)
    else:
        raise ValueError("Custom emoji ID must be a canonical positive signed 64-bit integer")
    if not 0 < number < 2**63:
        raise ValueError("Custom emoji ID must be a canonical positive signed 64-bit integer")
    return str(number)


def formatting_entities(
    text: str, entities: list[dict[str, Any]] | None
) -> list[dict[str, Any]] | None:
    if entities is None:
        return None
    if not isinstance(entities, list):
        raise ValueError("entities must be an array")
    boundaries = {0}
    positions = {0: 0}
    position = 0
    for index, character in enumerate(text, 1):
        position += 2 if ord(character) > 0xFFFF else 1
        boundaries.add(position)
        positions[position] = index
    normalized: list[dict[str, Any]] = []
    seen = set()
    for entity in entities:
        if not isinstance(entity, dict) or not {"type", "offset", "length"} <= entity.keys():
            raise ValueError("Formatting entity requires type, offset and length")
        kind, offset, length = entity["type"], entity["offset"], entity["length"]
        if not isinstance(kind, str) or kind not in {
            "bold",
            "italic",
            "underline",
            "strikethrough",
            "spoiler",
            "code",
            "pre",
            "blockquote",
            "expandable_blockquote",
            "custom_emoji",
        }:
            raise ValueError("GRAMLAB_UNSUPPORTED: formatting entity type")
        if (
            entity.keys()
            - {"type", "offset", "length"}
            - (
                {"language"}
                if kind == "pre"
                else ({"custom_emoji_id"} if kind == "custom_emoji" else set())
            )
        ):
            raise ValueError("GRAMLAB_UNSUPPORTED: formatting entity fields")
        language = entity.get("language", "")
        if not isinstance(language, str):
            raise ValueError("Preformatted language must be text")
        language.encode("utf-8", errors="strict")
        if (
            type(offset) is not int
            or type(length) is not int
            or length <= 0
            or offset not in boundaries
            or offset + length not in boundaries
        ):
            raise ValueError("Entity range must fit UTF-16 character boundaries")
        custom_emoji_id = None
        if kind == "custom_emoji":
            custom_emoji_id = canonical_custom_emoji_id(entity.get("custom_emoji_id"))
            covered = text[positions[offset] : positions[offset + length]]
            if not is_single_emoji(covered):
                raise ValueError("Custom emoji entity must cover one emoji")
        key = (kind, offset, length, language, custom_emoji_id)
        if key not in seen:
            seen.add(key)
            record: dict[str, Any] = {"type": kind, "offset": offset, "length": length}
            if language:
                record["language"] = language
            if custom_emoji_id is not None:
                record["custom_emoji_id"] = custom_emoji_id
            normalized.append(record)
    quotations = {"blockquote", "expandable_blockquote"}
    normalized.sort(
        key=lambda entity: (
            entity["offset"],
            -entity["length"],
            0 if entity["type"] in quotations else (1 if entity["type"] == "custom_emoji" else 2),
            entity["type"],
        )
    )
    active: list[dict[str, Any]] = []
    quote_depth = 0
    continuous = {"custom_emoji"}
    for entity in normalized:
        start, end = entity["offset"], entity["offset"] + entity["length"]
        while active and active[-1]["offset"] + active[-1]["length"] <= start:
            if active.pop()["type"] in quotations:
                quote_depth -= 1
        if active:
            parent = active[-1]
            if end > parent["offset"] + parent["length"]:
                raise ValueError("Entity ranges must be disjoint or fully nested")
            if parent["type"] in {"code", "pre"}:
                raise ValueError("Code entities cannot overlap other formatting")
            if entity["type"] in continuous and parent["type"] in continuous:
                raise ValueError("Custom emoji entities cannot overlap")
            if parent["type"] == "custom_emoji" and entity["type"] in quotations:
                raise ValueError("Custom emoji cannot contain a blockquote")
        if entity["type"] in {"code", "pre"} and any(
            ancestor["type"] not in quotations for ancestor in active
        ):
            raise ValueError("Code entities may only be contained by blockquotes")
        if entity["type"] in quotations:
            if quote_depth:
                raise ValueError("Blockquote entities cannot be nested")
            quote_depth += 1
        active.append(entity)
    return normalized or None
