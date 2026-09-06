"""Composer semantics are checked against independently observed native fixtures."""

import json
import threading
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gramlab._control import WorldControl
from gramlab._interactions import Interactions
from gramlab.scenario import Scenario, ScenarioError
from gramlab.world import World

CASES = json.loads(Path("tests/fixtures/composer-text.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_composer_model_matches_original_android(case):
    from gramlab._composer import composer_text

    assert composer_text(case["input"]) == case["message"]


@pytest.mark.parametrize(
    "value",
    [None, True, "", " \n ", "\ud800", "a" * 4097, "👩" * 2049],
    ids=["none", "boolean", "empty", "whitespace", "surrogate", "ascii-split", "emoji-split"],
)
def test_composer_rejects_invalid_or_unsplit_input(value):
    from gramlab._composer import composer_text

    with pytest.raises(ValueError):
        composer_text(value)


def test_composer_preserves_single_message_utf16_boundary():
    from gramlab._composer import composer_text

    for text in ("a" * 4096, "👩" * 2048):
        assert composer_text(text) == {"text": text}


@pytest.mark.parametrize(
    "value",
    ["```code```", "**a __b__ c**", "https://example.invalid", "🎲", "**  ** x"],
    ids=["fenced-code", "nested-markup", "link", "dice", "empty-entity"],
)
def test_unestablished_or_empty_composer_entities_are_explicit(value):
    from gramlab._composer import composer_text

    with pytest.raises(ValueError):
        composer_text(value)


@given(st.text(alphabet="abcسلام‌é👩🏽\t\r\n\u00a0 ", min_size=1, max_size=100))  # noqa: RUF001 — intentional mixed scripts
def test_plain_composer_preserves_unicode_and_only_trims_space_lf(text):
    from gramlab._composer import composer_text

    expected = text.strip(" \n")
    if expected:
        assert composer_text(text) == {"text": expected}
    else:
        with pytest.raises(ValueError):
            composer_text(text)


def test_composer_does_not_treat_version_numbers_as_links():
    from gramlab._composer import composer_text

    text = "Version v1.2 uses format 3.1"
    assert composer_text(text) == {"text": text}


def test_composer_does_not_treat_styled_dice_as_an_ordinary_text_send():
    from gramlab._composer import composer_text

    with pytest.raises(ValueError):
        composer_text("**🎲**")


def test_scenario_composer_sends_observed_text_and_distinguishes_equal_actions(tmp_path: Path):
    directory = tmp_path / "world"
    with World.create(directory, seed=19, now=1700000000) as world:
        world.create_user(first_name="Sara", language_code="fa")
        world.create_user(first_name="Composer", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        greeting = world.send_message(chat_id=1, sender_id=2, text="Write a message")
    interactions = Interactions(directory, lock=threading.Lock())
    accepted = []
    with WorldControl(directory, type_message=interactions.type_message) as control:
        lab = Scenario(control.base_url, capability=control.capability, world_id=control.world_id)
        for case in [*CASES, CASES[-1]]:
            record = lab.type_message(chat_id=1, text=case["input"])
            expected = {
                "id": len(accepted) + 2,
                "chat_id": 1,
                "sender_id": 1,
                "date": 1700000000,
                **case["message"],
            }
            assert record == {
                "operation": "type_message",
                "chat_id": 1,
                "text": case["input"],
                "native": False,
                "sends": [
                    {
                        "request_id": record["sends"][0]["request_id"],
                        "position": len(accepted) + 2,
                        "message": expected,
                    }
                ],
            }
            accepted.append(record["sends"][0])
        before = lab.events()
        for parameters in (
            {"chat_id": 999, "text": "hello"},
            {"chat_id": True, "text": "hello"},
            {"chat_id": 1, "text": " \n "},
            {"chat_id": 1, "text": "\ud800"},
        ):
            with pytest.raises(ScenarioError) as failure:
                lab.type_message(**parameters)
            assert failure.value.code == "invalid_request"
            assert not failure.value.outcome_uncertain
        assert lab.events() == before
    assert len({send["request_id"] for send in accepted}) == 8
    assert len(interactions.records) == 8 and not interactions.failed
    with World.open(directory) as world:
        assert world.client_snapshot(1, version=2)["sends"] == accepted
        assert world.history(1) == [greeting, *[send["message"] for send in accepted]]
        assert world.poll_updates(2) == [
            {"update_id": index + 1, "message": send["message"]}
            for index, send in enumerate(accepted)
        ]


def test_lost_composer_control_response_keeps_one_send_and_no_automatic_retry(tmp_path: Path):
    import http.client
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import urlsplit

    from test_scenario_client import serve

    directory = tmp_path / "world"
    with World.create(directory, seed=19, now=1700000000) as world:
        world.create_user(first_name="Sara")
        world.create_user(first_name="Composer", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        greeting = world.send_message(chat_id=1, sender_id=2, text="Write a message")
    interactions = Interactions(directory, lock=threading.Lock())
    responses = []
    with WorldControl(directory, type_message=interactions.type_message) as control:
        target = urlsplit(control.base_url)

        class LoseResponse(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = self.rfile.read(int(self.headers["Content-Length"]))
                connection = http.client.HTTPConnection(target.hostname, target.port, timeout=5)
                try:
                    connection.request(
                        "POST",
                        "/v1/world",
                        payload,
                        {
                            "Content-Type": "application/json",
                            "Authorization": self.headers["Authorization"],
                        },
                    )
                    response = connection.getresponse()
                    responses.append((response.status, json.loads(response.read())))
                finally:
                    connection.close()
                # Drop only the reply; the actual control handler has already committed.

            def log_message(self, *args):
                pass

        with serve(LoseResponse) as endpoint:
            lab = Scenario(endpoint, capability=control.capability, world_id=control.world_id)
            with pytest.raises(ScenarioError) as failure:
                lab.type_message(chat_id=1, text="**سلام**")
        assert (failure.value.operation, failure.value.code, failure.value.outcome_uncertain) == (
            "type_message",
            "transport_error",
            True,
        )
    assert len(responses) == len(interactions.records) == 1
    assert responses[0][0] == 200
    send = responses[0][1]["result"]["sends"][0]
    assert send["message"] == {
        "id": 2,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "سلام",
        "entities": [{"type": "bold", "offset": 0, "length": 4}],
    }
    with World.open(directory) as world:
        assert world.client_snapshot(1, version=2)["sends"] == [send]
        assert world.history(1) == [greeting, send["message"]]
        assert world.poll_updates(2) == [{"update_id": 1, "message": send["message"]}]


def test_concurrent_composer_and_inline_actions_share_the_run_limit(tmp_path: Path):
    from concurrent.futures import ThreadPoolExecutor

    directory = tmp_path / "world"
    with World.create(directory, seed=19, now=1700000000) as world:
        world.create_user(first_name="Sara")
        world.create_user(first_name="Composer", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_message(
            chat_id=1,
            sender_id=2,
            text="Choose",
            reply_markup={"inline_keyboard": [[{"text": "Choose", "callback_data": "yes"}]]},
        )
    interactions = Interactions(directory, lock=threading.Lock())
    with WorldControl(
        directory,
        type_message=interactions.type_message,
        tap_inline_button=interactions.tap_inline_button,
    ) as control:
        lab = Scenario(control.base_url, capability=control.capability, world_id=control.world_id)
        barrier = threading.Barrier(4)

        def actor():
            barrier.wait(timeout=5)
            for _ in range(8):
                lab.type_message(chat_id=1, text="same سلام")
                lab.tap_inline_button(chat_id=1, message_id=1, row=0, column=0)

        with ThreadPoolExecutor(max_workers=4) as workers:
            futures = [workers.submit(actor) for _ in range(4)]
            for future in futures:
                future.result(timeout=30)
        for operation in (
            lambda: lab.type_message(chat_id=1, text="too many"),
            lambda: lab.tap_inline_button(chat_id=1, message_id=1, row=0, column=0),
        ):
            with pytest.raises(ScenarioError) as failure:
                operation()
            assert failure.value.code == "invalid_request" and not failure.value.outcome_uncertain
    assert len(interactions.records) == 64 and not interactions.failed
    with World.open(directory) as world:
        sends = world.client_snapshot(1, version=2)["sends"]
        assert len(sends) == len({send["request_id"] for send in sends}) == 32
        assert [send["position"] for send in sends] == list(range(2, 34))
        assert world.history(1)[1:] == [
            {"id": index, "chat_id": 1, "sender_id": 1, "date": 1700000000, "text": "same سلام"}
            for index in range(2, 34)
        ]
        updates = world.poll_updates(2)
        assert len(updates) == 64
        assert [row["message"] for row in updates if "message" in row] == world.history(1)[1:]
        assert (
            len({row["callback_query"]["id"] for row in updates if "callback_query" in row}) == 32
        )


def test_new_bot_chat_requires_explicit_start_before_typing(tmp_path: Path):
    directory = tmp_path / "world"
    with World.create(directory, seed=19, now=1700000000) as world:
        world.create_user(first_name="Sara")
        world.create_user(first_name="Composer", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
    interactions = Interactions(directory, lock=threading.Lock())
    with WorldControl(
        directory,
        type_message=interactions.type_message,
        start_bot_chat=interactions.start_bot_chat,
    ) as control:
        lab = Scenario(control.base_url, capability=control.capability, world_id=control.world_id)
        with pytest.raises(ScenarioError) as failure:
            lab.type_message(chat_id=1, text="hello")
        assert failure.value.code == "invalid_request" and not failure.value.outcome_uncertain
        assert lab.history(1) == [] and interactions.records == []
        started = lab.start_bot_chat(chat_id=1)
        assert started["operation"] == "start_bot_chat"
        assert started["sends"][0]["message"] == {
            "id": 1,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "/start",
        }
        typed = lab.type_message(chat_id=1, text="hello")
        assert typed["sends"][0]["message"] == {
            "id": 2,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "hello",
        }
        with pytest.raises(ScenarioError) as failure:
            lab.start_bot_chat(chat_id=1)
        assert failure.value.code == "invalid_request" and not failure.value.outcome_uncertain
        assert lab.history(1) == [started["sends"][0]["message"], typed["sends"][0]["message"]]


def test_committed_backend_failure_is_uncertain_and_retained_by_control(tmp_path: Path):
    directory = tmp_path / "world"
    with World.create(directory, seed=19, now=1700000000) as world:
        world.create_user(first_name="Sara")
        world.create_user(first_name="Composer", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        greeting = world.send_message(chat_id=1, sender_id=2, text="Write a message")

    def interrupted_backend(chat, text, message):
        # Substitute the external renderer boundary only. Commit through real world storage,
        # then lose its completion, as the separate actual Android interruption probe exercises.
        with World.open(directory) as world:
            world.send_client_message(
                user_id=chat["user_id"], chat_id=chat["id"], request_id="interrupted", **message
            )
        raise ConnectionError("Controlled renderer completion loss")

    def unused_start(chat):
        raise AssertionError("This fixture already has conversation history")

    interactions = Interactions(
        directory, lock=threading.Lock(), compose=interrupted_backend, start_chat=unused_start
    )
    with WorldControl(directory, type_message=interactions.type_message) as control:
        lab = Scenario(control.base_url, capability=control.capability, world_id=control.world_id)
        with pytest.raises(ScenarioError) as failure:
            lab.type_message(chat_id=1, text="**hello**")
        assert (failure.value.code, failure.value.outcome_uncertain) == ("server_error", True)
    assert interactions.failed
    assert interactions.records == [
        {
            "operation": "type_message",
            "chat_id": 1,
            "text": "**hello**",
            "native": True,
            "failure": "ConnectionError",
        }
    ]
    expected = {
        "id": 2,
        "chat_id": 1,
        "sender_id": 1,
        "date": 1700000000,
        "text": "hello",
        "entities": [{"type": "bold", "offset": 0, "length": 5}],
    }
    with World.open(directory) as world:
        assert world.history(1) == [greeting, expected]
        assert world.client_snapshot(1, version=2)["sends"] == [
            {"request_id": "interrupted", "position": 2, "message": expected}
        ]
        assert world.poll_updates(2) == [{"update_id": 1, "message": expected}]
