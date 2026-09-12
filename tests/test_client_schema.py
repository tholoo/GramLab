"""Public World coverage for the centralized client bridge version matrix."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gramlab.world import World

_VERSIONS = (1, 2, 3, 4, 5, 6)
_ADMITTED = {
    "snapshot": frozenset(_VERSIONS),
    "changes": frozenset((2, 3, 4, 5, 6)),
    "message": frozenset((2, 4, 5, 6)),
    "callback": frozenset((1, 3, 4, 5, 6)),
}


@pytest.mark.parametrize(
    ("operation", "version"),
    [(operation, version) for operation in _ADMITTED for version in _VERSIONS],
)
def test_public_world_uses_one_exact_client_version_matrix(
    tmp_path: Path, operation: str, version: int
) -> None:
    with World.create(tmp_path / f"{operation}-{version}", seed=1, now=1) as world:
        user = world.create_user(first_name="User")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        message = world.send_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            text="callback",
            reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "data"}]]},
        )
        operations: dict[str, Any] = {
            "snapshot": lambda: world.client_snapshot(user["id"], version=version),
            "changes": lambda: world.client_changes(user["id"], after=0, version=version),
            "message": lambda: world.send_client_message(
                user_id=user["id"],
                chat_id=chat["id"],
                request_id="send",
                text="hello",
                version=version,
            ),
            "callback": lambda: world.create_callback(
                user_id=user["id"],
                chat_id=chat["id"],
                message_id=message["id"],
                data="data",
                request_id="callback",
                version=version,
            ),
        }

        if version in _ADMITTED[operation]:
            assert isinstance(operations[operation](), dict)
        else:
            with pytest.raises(ValueError, match=f"Unsupported client {operation} version"):
                operations[operation]()
