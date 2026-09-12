"""The additive scenario-flow interface uses the real loopback control seam."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from gramlab._captures import Captures
from gramlab._control import WorldControl
from gramlab._interactions import Interactions
from gramlab.world import World


def test_public_flow_binds_people_conversations_messages_and_callbacks(tmp_path: Path) -> None:
    from gramlab import (
        Bot,
        BotStatus,
        Callback,
        Capture,
        Conversation,
        InlineAction,
        InlineButton,
        Message,
        Scenario,
        User,
    )

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        bot_id = world.create_user(first_name="Echo", is_bot=True)["id"]
    interactions = Interactions(directory, lock=threading.Lock())
    captures = Captures(directory)

    def bot_status(name: str) -> dict[str, object]:
        return {"name": name, "generation": 1, "state": "exited", "exit_code": 0}

    def type_message(*, chat_id: int, text: str) -> dict[str, object]:
        return {"operation": "type_message", "chat_id": chat_id, "text": text}

    def start_bot_chat(*, chat_id: int) -> dict[str, object]:
        return {"operation": "start_bot_chat", "chat_id": chat_id}

    with WorldControl(
        directory,
        bots={"echo": bot_id},
        capture_chat=captures.capture_chat,
        tap_inline_button=interactions.tap_inline_button,
        bot_status=bot_status,
        type_message=type_message,
        start_bot_chat=start_bot_chat,
    ) as control:
        lab = Scenario(control.base_url, capability=control.capability, world_id=control.world_id)
        user = lab.user("Sara", username="sara", language_code="fa")
        bot = lab.bot("echo")
        conversation = lab.conversation(user=user, bot=bot)

        assert isinstance(user, User)
        assert (user.id, user.first_name, user.username, user.language_code) == (
            2,
            "Sara",
            "sara",
            "fa",
        )
        assert isinstance(bot, Bot)
        assert (bot.id, bot.name) == (1, "echo")
        assert isinstance(conversation, Conversation)
        assert (conversation.id, conversation.user, conversation.bot) == (1, user, bot)

        incoming = conversation.send("سلام hello")
        assert isinstance(incoming, Message)
        assert (incoming.id, incoming.sender_id, incoming.text) == (1, user.id, "سلام hello")
        changed = incoming.raw
        changed["text"] = "changed copy"
        assert incoming.text == "سلام hello"

        keyboard = {"inline_keyboard": [[{"text": "Choose", "callback_data": "confirm"}]]}
        lab.send_message(
            chat_id=conversation.id,
            sender_id=bot.id,
            text="Choose",
            reply_markup=keyboard,
        )
        history = conversation.wait_for_messages(2, timeout=1)
        assert isinstance(history, tuple)
        assert all(isinstance(message, Message) for message in history)
        assert [message.text for message in history] == ["سلام hello", "Choose"]
        assert history[1].raw["reply_markup"] == keyboard

        button = history[1].inline_button(0, 0)
        assert isinstance(button, InlineButton)
        assert (button.text, button.data, button.row, button.column) == (
            "Choose",
            "confirm",
            0,
            0,
        )
        action = button.tap(timeout=1)
        assert isinstance(action, InlineAction)
        callback = action.callback
        assert isinstance(callback, Callback)
        assert callback.data == "confirm"
        with World.open(directory) as world:
            world.answer_callback(bot_id=bot.id, callback_id=callback.id, text="Confirmed")
        answered = callback.wait_until_answered(timeout=1)
        assert answered.answer == {"text": "Confirmed", "show_alert": False, "cache_time": 0}

        capture = conversation.capture("typed-flow", contains=["سلام", "Choose"], timeout=1)
        assert isinstance(capture, Capture)
        assert (capture.label, capture.rendered) == ("typed-flow", False)
        assert capture.raw["chat_id"] == conversation.id

        typed = conversation.type("typed input", timeout=1)
        started = conversation.start(timeout=1)
        assert typed.raw == {
            "operation": "type_message",
            "chat_id": conversation.id,
            "text": "typed input",
        }
        assert started.raw == {"operation": "start_bot_chat", "chat_id": conversation.id}

        status = bot.wait_for_state("exited", timeout=1)
        assert isinstance(status, BotStatus)
        assert (status.name, status.generation, status.state, status.exit_code) == (
            "echo",
            1,
            "exited",
            0,
        )


def test_flow_waits_are_bounded_and_report_the_last_safe_observation(tmp_path: Path) -> None:
    from gramlab import Scenario, ScenarioWaitTimeout

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        bot_id = world.create_user(first_name="Echo", is_bot=True)["id"]
    with WorldControl(directory, bots={"echo": bot_id}) as control:
        lab = Scenario(control.base_url, capability=control.capability, world_id=control.world_id)
        conversation = lab.conversation(user=lab.user("Sara"), bot="echo")
        only = conversation.send("Only message")
        with pytest.raises(ScenarioWaitTimeout) as failure:
            conversation.wait_for_messages(2, timeout=0.02)
        assert failure.value.operation == "conversation.wait_for_messages"
        assert failure.value.timeout == 0.02
        assert failure.value.last_observation == (only.raw,)
        assert control.capability not in str(failure.value) + repr(failure.value)


def test_flow_handles_cannot_cross_scenario_instances(tmp_path: Path) -> None:
    from gramlab import Scenario

    directories = [tmp_path / "alpha", tmp_path / "beta"]
    for directory in directories:
        with World.create(directory, seed=7, now=100) as world:
            world.create_user(first_name="Echo", is_bot=True)
    with (
        WorldControl(directories[0], bots={"echo": 1}) as alpha_control,
        WorldControl(directories[1], bots={"echo": 1}) as beta_control,
    ):
        alpha = Scenario(
            alpha_control.base_url,
            capability=alpha_control.capability,
            world_id=alpha_control.world_id,
        )
        beta = Scenario(
            beta_control.base_url,
            capability=beta_control.capability,
            world_id=beta_control.world_id,
        )
        alpha_user = alpha.user("Alpha")
        with pytest.raises(ValueError, match="another Scenario"):
            beta.conversation(user=alpha_user, bot="echo")
        assert beta.snapshot()["chats"] == []


@pytest.mark.parametrize(
    ("count", "timeout"),
    [(-1, 1), (True, 1), (1, 0), (1, True), (1, float("inf"))],
)
def test_flow_waits_reject_invalid_limits_before_reading(
    tmp_path: Path, count: object, timeout: object
) -> None:
    from gramlab import Scenario

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Echo", is_bot=True)
    with WorldControl(directory, bots={"echo": 1}) as control:
        lab = Scenario(control.base_url, capability=control.capability, world_id=control.world_id)
        conversation = lab.conversation(user=lab.user("Sara"), bot="echo")
        with pytest.raises(ValueError, match=r"count|timeout"):
            conversation.wait_for_messages(count, timeout=timeout)  # type: ignore[arg-type]


def test_message_rejects_missing_inline_cells_without_sending_input(tmp_path: Path) -> None:
    from gramlab import Scenario

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        world.create_user(first_name="Echo", is_bot=True)
    with WorldControl(directory, bots={"echo": 1}) as control:
        lab = Scenario(control.base_url, capability=control.capability, world_id=control.world_id)
        conversation = lab.conversation(user=lab.user("Sara"), bot="echo")
        message = conversation.send("No keyboard")
        with pytest.raises(ValueError, match="inline button"):
            message.inline_button(0, 0)
