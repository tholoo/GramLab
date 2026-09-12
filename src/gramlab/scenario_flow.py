"""Typed, run-bound handles for authoring GramLab consumer scenarios."""

from __future__ import annotations

import copy
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from threading import Event
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from gramlab.scenario import Scenario

BotState = Literal["running", "stopped", "exited"]
_POLL_INTERVAL = 0.02


class ScenarioFlowError(RuntimeError):
    """A typed-flow result did not satisfy its documented semantic shape."""


class ScenarioWaitTimeout(TimeoutError):
    """A bounded read-only observation did not reach its requested state."""

    def __init__(self, operation: str, timeout: float, last_observation: Any) -> None:
        super().__init__(f"{operation} did not complete within {timeout:g} seconds")
        self.operation = operation
        self.timeout = timeout
        if isinstance(last_observation, tuple):
            self.last_observation = tuple(item.raw for item in last_observation)
        elif hasattr(last_observation, "raw"):
            self.last_observation = last_observation.raw
        else:
            self.last_observation = copy.deepcopy(last_observation)


def _timeout(value: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError("Flow timeout must be finite and positive")
    return float(value)


def _count(value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("Message count must be a nonnegative integer")
    return value


def _integer(body: dict[str, Any], field: str, context: str, *, positive: bool = True) -> int:
    value = body.get(field)
    minimum = 1 if positive else 0
    if type(value) is not int or not minimum <= value < 2**63:
        raise ScenarioFlowError(f"{context} returned an invalid {field}")
    return value


def _text(body: dict[str, Any], field: str, context: str, *, optional: bool = False) -> str | None:
    value = body.get(field)
    if optional and value is None:
        return None
    if not isinstance(value, str):
        raise ScenarioFlowError(f"{context} returned an invalid {field}")
    return value


def _wait[Observation](
    operation: str,
    timeout: float,
    read: Callable[[], Observation],
    ready: Callable[[Observation], bool],
) -> Observation:
    limit = _timeout(timeout)
    deadline = time.monotonic() + limit
    last = read()
    while not ready(last):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ScenarioWaitTimeout(operation, limit, last)
        Event().wait(min(_POLL_INTERVAL, remaining))
        last = read()
    return last


@dataclass(frozen=True, slots=True)
class User:
    """A virtual participant bound to the Scenario instance that created it."""

    _scenario: Scenario = field(repr=False, compare=False)
    id: int
    first_name: str
    is_bot: bool
    username: str | None
    language_code: str | None
    _body: dict[str, Any] = field(repr=False, compare=False)

    @property
    def raw(self) -> dict[str, Any]:
        return copy.deepcopy(self._body)


@dataclass(frozen=True, slots=True)
class Bot:
    """A configured consumer bot bound to one scenario run."""

    _scenario: Scenario = field(repr=False, compare=False)
    name: str
    id: int

    def status(self) -> BotStatus:
        return _bot_status(self, self._scenario.bot_status(self.name))

    def wait_for_state(self, state: BotState, *, timeout: float = 30) -> BotStatus:
        if state not in ("running", "stopped", "exited"):
            raise ValueError("Bot state must be running, stopped or exited")
        return _wait(
            "bot.wait_for_state",
            timeout,
            self.status,
            lambda current: current.state == state,
        )

    def wait_until_exited(self, *, timeout: float = 30) -> BotStatus:
        return self.wait_for_state("exited", timeout=timeout)


@dataclass(frozen=True, slots=True)
class BotStatus:
    """One observed generation of a configured consumer bot."""

    bot: Bot
    name: str
    generation: int
    state: BotState
    exit_code: int | None
    _body: dict[str, Any] = field(repr=False, compare=False)

    @property
    def raw(self) -> dict[str, Any]:
        return copy.deepcopy(self._body)


@dataclass(frozen=True, slots=True)
class Conversation:
    """One private user/bot chat with identity and common operations already bound."""

    _scenario: Scenario = field(repr=False, compare=False)
    user: User
    bot: Bot
    id: int
    _body: dict[str, Any] = field(repr=False, compare=False)

    @property
    def raw(self) -> dict[str, Any]:
        return copy.deepcopy(self._body)

    def send(
        self,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
        entities: list[dict[str, Any]] | None = None,
    ) -> Message:
        body = self._scenario.send_message(
            chat_id=self.id,
            sender_id=self.user.id,
            text=text,
            reply_markup=reply_markup,
            entities=entities,
        )
        return _message(self, body)

    def history(self) -> tuple[Message, ...]:
        return tuple(_message(self, body) for body in self._scenario.history(self.id))

    def wait_for_messages(self, count: int, *, timeout: float = 30) -> tuple[Message, ...]:
        expected = _count(count)
        return _wait(
            "conversation.wait_for_messages",
            timeout,
            self.history,
            lambda messages: len(messages) >= expected,
        )

    def capture(
        self,
        label: str,
        *,
        contains: list[str],
        timeout: float = 180,
    ) -> Capture:
        body = self._scenario.capture_chat(
            chat_id=self.id,
            label=label,
            contains=contains,
            timeout=timeout,
        )
        return _capture(self, body)

    def type(self, text: str, *, timeout: float = 180) -> InteractionReceipt:
        """Enter text through the selected client mode and retain its receipt."""
        body = self._scenario.type_message(chat_id=self.id, text=text, timeout=timeout)
        return InteractionReceipt(self, copy.deepcopy(body))

    def start(self, *, timeout: float = 180) -> InteractionReceipt:
        """Press Start Bot through the selected client mode and retain its receipt."""
        body = self._scenario.start_bot_chat(chat_id=self.id, timeout=timeout)
        return InteractionReceipt(self, copy.deepcopy(body))


@dataclass(frozen=True, slots=True)
class Message:
    """An immutable observation of one message in a conversation."""

    conversation: Conversation
    id: int
    chat_id: int
    sender_id: int
    text: str
    caption: str | None
    _body: dict[str, Any] = field(repr=False, compare=False)

    @property
    def raw(self) -> dict[str, Any]:
        return copy.deepcopy(self._body)

    def inline_button(self, row: int, column: int) -> InlineButton:
        if any(type(value) is not int or value < 0 for value in (row, column)):
            raise ValueError("Inline button row and column must be nonnegative integers")
        markup = self._body.get("reply_markup")
        keyboard = markup.get("inline_keyboard", []) if isinstance(markup, dict) else []
        if (
            not isinstance(keyboard, list)
            or row >= len(keyboard)
            or not isinstance(keyboard[row], list)
            or column >= len(keyboard[row])
            or not isinstance(keyboard[row][column], dict)
        ):
            raise ValueError("Message has no inline button at that row and column")
        button = keyboard[row][column]
        text = _text(button, "text", "Inline keyboard")
        data = _text(button, "callback_data", "Inline keyboard")
        if text is None or data is None:
            raise ScenarioFlowError("Inline keyboard returned invalid text or callback_data")
        return InlineButton(self, row, column, text, data)


@dataclass(frozen=True, slots=True)
class InlineButton:
    """One selected callback button from an immutable message observation."""

    message: Message
    row: int
    column: int
    text: str
    data: str

    def tap(self, *, timeout: float = 180) -> InlineAction:
        conversation = self.message.conversation
        body = conversation._scenario.tap_inline_button(
            chat_id=conversation.id,
            message_id=self.message.id,
            row=self.row,
            column=self.column,
            timeout=timeout,
        )
        return InlineAction(self, copy.deepcopy(body))


@dataclass(frozen=True, slots=True)
class InteractionReceipt:
    """A retained composer or Start Bot interaction result."""

    conversation: Conversation
    _body: dict[str, Any] = field(repr=False, compare=False)

    @property
    def raw(self) -> dict[str, Any]:
        return copy.deepcopy(self._body)


@dataclass(frozen=True, slots=True)
class InlineAction:
    """The retained result of one inline-button input action."""

    button: InlineButton
    _body: dict[str, Any] = field(repr=False, compare=False)

    @property
    def raw(self) -> dict[str, Any]:
        return copy.deepcopy(self._body)

    @property
    def callback(self) -> Callback:
        body = self._body.get("callback")
        if not isinstance(body, dict):
            raise ScenarioFlowError("Inline action returned no callback result")
        return _callback(self.button.message.conversation, body)


@dataclass(frozen=True, slots=True)
class Callback:
    """A durable callback observation bound to its originating conversation."""

    conversation: Conversation
    id: str
    user_id: int
    chat_id: int
    data: str
    answer: Mapping[str, Any] | None
    _body: dict[str, Any] = field(repr=False, compare=False)

    @property
    def raw(self) -> dict[str, Any]:
        return copy.deepcopy(self._body)

    def refresh(self) -> Callback:
        body = self.conversation._scenario.get_callback(
            user_id=self.conversation.user.id,
            callback_id=self.id,
        )
        return _callback(self.conversation, body)

    def wait_until_answered(self, *, timeout: float = 30) -> Callback:
        return _wait(
            "callback.wait_until_answered",
            timeout,
            self.refresh,
            lambda current: current.answer is not None,
        )


@dataclass(frozen=True, slots=True)
class Capture:
    """A retained semantic capture, with rendering evidence when available."""

    conversation: Conversation
    label: str
    rendered: bool
    _body: dict[str, Any] = field(repr=False, compare=False)

    @property
    def raw(self) -> dict[str, Any]:
        return copy.deepcopy(self._body)


def user_from_result(scenario: Scenario, body: dict[str, Any]) -> User:
    identifier = _integer(body, "id", "User")
    first_name = _text(body, "first_name", "User")
    is_bot = body.get("is_bot")
    if first_name is None or is_bot is not False:
        raise ScenarioFlowError("User returned invalid identity fields")
    return User(
        scenario,
        identifier,
        first_name,
        is_bot,
        _text(body, "username", "User", optional=True),
        _text(body, "language_code", "User", optional=True),
        copy.deepcopy(body),
    )


def bot_from_name(scenario: Scenario, name: str, bots: dict[str, int]) -> Bot:
    if not isinstance(name, str) or not name:
        raise ValueError("Bot name must be a nonempty configured alias")
    identifier = bots.get(name)
    if type(identifier) is not int or not 0 < identifier < 2**63:
        raise ValueError("Unknown configured bot alias")
    return Bot(scenario, name, identifier)


def conversation_from_result(
    scenario: Scenario, user: User, bot: Bot, body: dict[str, Any]
) -> Conversation:
    identifier = _integer(body, "id", "Conversation")
    if (
        body.get("type") != "private"
        or body.get("user_id") != user.id
        or body.get("bot_id") != bot.id
    ):
        raise ScenarioFlowError("Conversation returned invalid participant identity")
    return Conversation(scenario, user, bot, identifier, copy.deepcopy(body))


def _message(conversation: Conversation, body: dict[str, Any]) -> Message:
    identifier = _integer(body, "id", "Message")
    chat_id = _integer(body, "chat_id", "Message")
    sender_id = _integer(body, "sender_id", "Message")
    if chat_id != conversation.id or sender_id not in (conversation.user.id, conversation.bot.id):
        raise ScenarioFlowError("Message returned invalid conversation identity")
    text = body.get("text", "")
    caption = body.get("caption")
    if not isinstance(text, str) or (caption is not None and not isinstance(caption, str)):
        raise ScenarioFlowError("Message returned invalid text or caption")
    return Message(
        conversation,
        identifier,
        chat_id,
        sender_id,
        text,
        caption,
        copy.deepcopy(body),
    )


def _callback(conversation: Conversation, body: dict[str, Any]) -> Callback:
    identifier = _text(body, "id", "Callback")
    user_id = _integer(body, "user_id", "Callback")
    chat_id = _integer(body, "chat_id", "Callback")
    data = _text(body, "data", "Callback")
    answer = body.get("answer")
    if (
        identifier is None
        or data is None
        or user_id != conversation.user.id
        or chat_id != conversation.id
        or (answer is not None and not isinstance(answer, dict))
    ):
        raise ScenarioFlowError("Callback returned invalid conversation identity or answer")
    return Callback(
        conversation,
        identifier,
        user_id,
        chat_id,
        data,
        MappingProxyType(copy.deepcopy(answer)) if answer is not None else None,
        copy.deepcopy(body),
    )


def _bot_status(bot: Bot, body: dict[str, Any]) -> BotStatus:
    name = _text(body, "name", "Bot status")
    generation = _integer(body, "generation", "Bot status")
    state = body.get("state")
    exit_code = body.get("exit_code")
    if (
        name != bot.name
        or state not in ("running", "stopped", "exited")
        or (exit_code is not None and type(exit_code) is not int)
    ):
        raise ScenarioFlowError("Bot status returned invalid process state")
    return BotStatus(bot, name, generation, state, exit_code, copy.deepcopy(body))


def _capture(conversation: Conversation, body: dict[str, Any]) -> Capture:
    label = _text(body, "label", "Capture")
    rendered = body.get("rendered")
    if body.get("chat_id") != conversation.id or label is None or type(rendered) is not bool:
        raise ScenarioFlowError("Capture returned invalid conversation identity or rendering state")
    return Capture(conversation, label, rendered, copy.deepcopy(body))


__all__ = [
    "Bot",
    "BotState",
    "BotStatus",
    "Callback",
    "Capture",
    "Conversation",
    "InlineAction",
    "InlineButton",
    "InteractionReceipt",
    "Message",
    "ScenarioFlowError",
    "ScenarioWaitTimeout",
    "User",
]
