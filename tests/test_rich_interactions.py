"""Real World effects, shared budgets and durable single-use rich operations."""

import http.client
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from gramlab._control import WorldControl
from gramlab._interactions import Interactions
from gramlab._rich_button_journal import recover_journal
from gramlab._rich_interactions import NativeRichInput, RichInteractions
from gramlab.scenario import Scenario, ScenarioError
from gramlab.world import World


def setup(
    directory: Path, *, native: NativeRichInput | None = None
) -> tuple[Interactions, RichInteractions]:
    with World.create(directory / "world", seed=7, now=100) as world:
        world.create_user(first_name="Sara")
        world.create_user(first_name="Bot", is_bot=True)
        world.open_private_chat(user_id=1, bot_id=2)
        world.send_rich_message(
            chat_id=1,
            sender_id=2,
            rich_message={
                "skip_entity_detection": True,
                "blocks": [
                    {
                        "type": "buttons",
                        "buttons": [
                            {"text": "Same", "callback_data": "same"},
                            {"text": "کپی", "copy_text": {"text": "copied / کپی"}},
                            {"text": "Disabled", "disabled": {}},
                        ],
                    }
                ],
            },
        )
    lock = threading.Lock()
    ordinary = Interactions(directory / "world", lock=lock)
    return ordinary, RichInteractions(
        directory / "world", lock=lock, interactions=ordinary, native=native
    )


def test_concurrent_claims_retain_one_complete_callback_and_recover_exactly(tmp_path: Path) -> None:
    ordinary, rich = setup(tmp_path)
    observed = rich.rich_buttons(chat_id=1, message_id=1)
    selected = observed["targets"][0]
    rendezvous = threading.Barrier(8)

    def tap() -> dict[str, Any]:
        rendezvous.wait(timeout=5)
        return rich.tap_rich_button(target_id=selected["target_id"])

    with ThreadPoolExecutor(max_workers=8) as threads:
        receipts = list(threads.map(lambda _: tap(), range(8)))
    final = rich.tap_rich_button(target_id=selected["target_id"])
    assert {receipt["operation_id"] for receipt in receipts} == {final["operation_id"]}
    assert {receipt["status"] for receipt in receipts} <= {"in_progress", "succeeded"}
    assert final["status"] == "succeeded"
    assert final["dispatch"] == "dispatched"
    assert final["target"] == selected | {"chat_id": 1, "message_id": 1, "message_revision": 4}
    assert final["reason"] is None
    assert ordinary.records == [final]
    with World.open(tmp_path / "world") as world:
        callbacks = [event for event in world.events() if event["type"] == "callback.created"]
        assert len(callbacks) == 1
        assert final["effect"] == {
            "kind": "callback",
            "callback": callbacks[0]["data"] | {"answer": None},
            "event_sequence": 5,
        }
        assert final["evidence"] == {
            "mode": "simulation",
            "world_event_sequences": [5],
            "clipboard_observation": None,
        }
        assert world.poll_updates(2) == [{"update_id": 1, "callback_query": callbacks[0]["data"]}]
    rich.close()
    recovered = recover_journal(tmp_path / "rich-button-journal.jsonl")
    assert recovered["receipts"] == [final]
    assert recovered["unclaimed_target_ids"] == [
        target["target_id"] for target in observed["targets"][1:]
    ]
    assert recovered["incomplete_tail"] is False


@pytest.mark.parametrize(
    "phase", ["observe", "invalid_nonce", "prepare", "invalid_preparation", "dispatch"]
)
def test_external_backend_failure_is_not_a_successful_run_or_repeated_input(
    tmp_path: Path, phase: str
) -> None:
    """Substitute a failing external backend only; this establishes no native evidence."""

    class FailingInput:
        dispatched = 0
        aborted = 0

        def observe(self, record: dict[str, Any]) -> str:
            if phase == "observe":
                raise OSError("external client stopped")
            return "" if phase == "invalid_nonce" else "external-client"

        def prepare(self, receipt: dict[str, Any], *, client_nonce: str) -> dict[str, Any]:
            if phase == "prepare":
                raise RuntimeError("external preparation stopped")
            candidate = receipt | {
                "status": "succeeded",
                "dispatch": "dispatched",
                "effect": {"kind": "copy", "text": "copied / کپی"},
                "reason": None,
            }
            if phase == "invalid_preparation":
                candidate["operation_id"] = "another-operation"
            return {"context": {}, "receipt_for_size_check": candidate}

        def dispatch(self, receipt: dict[str, Any], prepared: dict[str, Any]) -> dict[str, Any]:
            self.dispatched += 1
            raise OSError("external transport stopped after durable intent")

        def abort_prepared(self, receipt: dict[str, Any], prepared: dict[str, Any]) -> None:
            self.aborted += 1

        def reconcile(self, receipt: dict[str, Any]) -> dict[str, Any] | None:
            return None

    backend = FailingInput()
    _, rich = setup(tmp_path, native=backend)
    with World.open(tmp_path / "world") as world:
        before = world.snapshot(), world.events(), world.poll_updates(2)
    if phase in {"observe", "invalid_nonce"}:
        with pytest.raises((OSError, ValueError, RuntimeError)):
            rich.rich_buttons(chat_id=1, message_id=1)
    else:
        selected = rich.rich_buttons(chat_id=1, message_id=1)["targets"][1]["target_id"]
        result = rich.tap_rich_button(target_id=selected)
        assert result["effect"] is None
        if phase == "dispatch":
            assert (result["status"], result["dispatch"], result["reason"]) == (
                "uncertain",
                "intent_recorded",
                {"code": "dispatch_unconfirmed"},
            )
        else:
            assert (result["status"], result["dispatch"], result["reason"]) == (
                "rejected_before_dispatch",
                "not_dispatched",
                {"code": "component_stopped"},
            )
        assert rich.tap_rich_button(target_id=selected) == result
    assert rich.failed and rich.failure == "rich_button_component_failed"
    assert backend.dispatched == (1 if phase == "dispatch" else 0)
    assert backend.aborted == (1 if phase == "invalid_preparation" else 0)
    with World.open(tmp_path / "world") as world:
        assert (world.snapshot(), world.events(), world.poll_updates(2)) == before
    rich.close()
    recovered = recover_journal(tmp_path / "rich-button-journal.jsonl")
    if phase in {"observe", "invalid_nonce"}:
        assert recovered["receipts"] == recovered["unclaimed_target_ids"] == []
    else:
        assert recovered["receipts"] == [result]


def test_copy_disabled_are_client_local_and_repeat_is_read_only(tmp_path: Path) -> None:
    ordinary, rich = setup(tmp_path)
    targets = rich.rich_buttons(chat_id=1, message_id=1)["targets"]
    with World.open(tmp_path / "world") as world:
        before = world.snapshot(), world.events(), world.poll_updates(2)
    copied = rich.tap_rich_button(target_id=targets[1]["target_id"])
    disabled = rich.tap_rich_button(target_id=targets[2]["target_id"])
    assert copied["effect"] == {"kind": "copy", "text": "copied / کپی"}
    assert copied["evidence"] == {
        "mode": "simulation",
        "world_event_sequences": [],
        "clipboard_observation": {"before": None, "after": "copied / کپی"},
    }
    assert disabled["effect"] == {"kind": "none", "reason": "disabled"}
    assert disabled["evidence"] == {
        "mode": "simulation",
        "world_event_sequences": [],
        "clipboard_observation": {"before": "copied / کپی", "after": "copied / کپی"},
    }
    retained = (tmp_path / "rich-button-journal.jsonl").read_bytes()
    for target, expected in ((targets[1], copied), (targets[2], disabled)):
        assert rich.tap_rich_button(target_id=target["target_id"]) == expected
    assert (tmp_path / "rich-button-journal.jsonl").read_bytes() == retained
    assert ordinary.records == [copied, disabled]
    with World.open(tmp_path / "world") as world:
        assert (world.snapshot(), world.events(), world.poll_updates(2)) == before
    rich.close()


def test_issued_targets_reserve_shared_capacity_before_ordinary_input(tmp_path: Path) -> None:
    ordinary, rich = setup(tmp_path)
    observations = [rich.rich_buttons(chat_id=1, message_id=1) for _ in range(21)]
    ordinary.type_message(chat_id=1, text="Last ordinary slot")
    retained = (tmp_path / "rich-button-journal.jsonl").read_bytes()
    with pytest.raises(ValueError, match="64 interactions"):
        rich.rich_buttons(chat_id=1, message_id=1)
    with pytest.raises(ValueError, match="64 interactions"):
        ordinary.type_message(chat_id=1, text="Must not send")
    assert (tmp_path / "rich-button-journal.jsonl").read_bytes() == retained
    for observed in observations:
        for target in observed["targets"]:
            assert rich.tap_rich_button(target_id=target["target_id"])["status"] == "succeeded"
    assert len(ordinary.records) == 64
    with World.open(tmp_path / "world") as world:
        assert [message["text"] for message in world.history(1)] == ["", "Last ordinary slot"]
        assert len([event for event in world.events() if event["type"] == "callback.created"]) == 21
    rich.close()


@pytest.mark.parametrize("switch", ["observation", "ordinary_input"])
def test_selecting_another_persona_invalidates_old_virtual_targets(
    tmp_path: Path, switch: str
) -> None:
    ordinary, rich = setup(tmp_path)
    original = rich.rich_buttons(chat_id=1, message_id=1)
    with World.open(tmp_path / "world") as world:
        world.create_user(first_name="Other")
        world.open_private_chat(user_id=3, bot_id=2)
        world.send_rich_message(
            chat_id=2,
            sender_id=2,
            rich_message={"skip_entity_detection": True, **world.get_message(1, 1)["rich_message"]},
        )
    if switch == "observation":
        rich.rich_buttons(chat_id=2, message_id=1)
    else:
        ordinary.type_message(chat_id=2, text="Another client persona")
    rejected = rich.tap_rich_button(target_id=original["targets"][0]["target_id"])
    assert rejected["status"] == "rejected_before_dispatch"
    assert rejected["dispatch"] == "not_dispatched"
    assert rejected["effect"] is None
    assert rejected["reason"] == {"code": "client_restarted"}
    with World.open(tmp_path / "world") as world:
        assert not any(event["type"] == "callback.created" for event in world.events())
    rich.close()


@pytest.mark.parametrize("operation", ["rich_buttons", "tap_rich_button"])
def test_lost_control_reply_does_not_repeat_allocation_or_callback(
    tmp_path: Path, operation: str
) -> None:
    _, rich = setup(tmp_path)
    forwarded: list[dict[str, Any]] = []
    with WorldControl(
        tmp_path / "world", rich_buttons=rich.rich_buttons, tap_rich_button=rich.tap_rich_button
    ) as control:
        direct = Scenario(
            control.base_url, capability=control.capability, world_id=control.world_id
        )
        observed = direct.rich_buttons(chat_id=1, message_id=1)
        selected = observed["targets"][0]["target_id"]

        class DropReply(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                payload = self.rfile.read(int(self.headers["Content-Length"]))
                upstream = http.client.HTTPConnection(
                    control.base_url.removeprefix("http://"), timeout=5
                )
                try:
                    upstream.request(
                        "POST",
                        "/v1/world",
                        payload,
                        {
                            "Content-Type": "application/json",
                            "Authorization": self.headers["Authorization"],
                        },
                    )
                    response = upstream.getresponse()
                    assert response.status == 200
                    forwarded.append(json.loads(response.read()))
                    # Drop only the real control response after its authoritative operation.
                finally:
                    upstream.close()

            def log_message(self, format: str, *args: Any) -> None:
                pass

        proxy = ThreadingHTTPServer(("127.0.0.1", 0), DropReply)
        thread = threading.Thread(target=proxy.serve_forever)
        thread.start()
        try:
            client = Scenario(
                f"http://127.0.0.1:{proxy.server_port}",
                capability=control.capability,
                world_id=control.world_id,
            )
            with pytest.raises(ScenarioError) as caught:
                if operation == "rich_buttons":
                    client.rich_buttons(chat_id=1, message_id=1)
                else:
                    client.tap_rich_button(target_id=selected)
            assert (caught.value.operation, caught.value.code, caught.value.outcome_uncertain) == (
                operation,
                "transport_error",
                True,
            )
        finally:
            proxy.shutdown()
            proxy.server_close()
            thread.join(timeout=5)
        assert len(forwarded) == 1
        if operation == "tap_rich_button":
            assert direct.tap_rich_button(target_id=selected) == forwarded[0]["result"]
        with pytest.raises(ScenarioError) as rejected:
            direct.tap_rich_button(target_id="another-run-or-unknown")
        assert (rejected.value.code, rejected.value.outcome_uncertain) == ("invalid_request", False)
    rich.close()
    recovered = recover_journal(tmp_path / "rich-button-journal.jsonl")
    with World.open(tmp_path / "world") as world:
        callback_events = [event for event in world.events() if event["type"] == "callback.created"]
    if operation == "rich_buttons":
        assert callback_events == []
        assert len(recovered["unclaimed_target_ids"]) == 6
        assert recovered["receipts"] == []
    else:
        assert len(callback_events) == 1
        assert recovered["receipts"] == [forwarded[0]["result"]]
        assert len(recovered["unclaimed_target_ids"]) == 2


@pytest.mark.parametrize(
    "completion", ["success", "uncertain", "mismatch", "exception", "malformed"]
)
def test_readonly_reconciliation_preserves_effect_and_failure_contract(
    tmp_path: Path, completion: str
) -> None:
    """The external input boundary is controlled; World and journal remain real."""

    class DelayedInput:
        dispatched = 0
        polls = 0

        def observe(self, record: dict[str, Any]) -> str:
            return "delayed-client"

        def outcome(self, receipt: dict[str, Any], *, confirmed: bool) -> dict[str, Any]:
            return {
                "status": "succeeded" if confirmed else "uncertain",
                "dispatch": "dispatched",
                "effect": {"kind": "none", "reason": "disabled"} if confirmed else None,
                "reason": None if confirmed else {"code": "effect_timeout"},
                "evidence": receipt["evidence"]
                | {
                    "clipboard_observation": {"before": None, "after": None},
                },
            }

        def prepare(self, receipt: dict[str, Any], *, client_nonce: str) -> dict[str, Any]:
            return {
                "context": {},
                "receipt_for_size_check": receipt | self.outcome(receipt, confirmed=True),
            }

        def dispatch(self, receipt: dict[str, Any], prepared: dict[str, Any]) -> dict[str, Any]:
            self.dispatched += 1
            return self.outcome(receipt, confirmed=False)

        def abort_prepared(self, receipt: dict[str, Any], prepared: dict[str, Any]) -> None:
            raise AssertionError("No prepared input failed")

        def reconcile(self, receipt: dict[str, Any]) -> dict[str, Any] | None:
            self.polls += 1
            if completion == "exception":
                raise OSError("external observation failed")
            if completion == "malformed":
                return {"status": "succeeded"}
            outcome = self.outcome(receipt, confirmed=completion == "success")
            outcome["evidence"]["native"] = receipt["evidence"]["native"] | {
                "effect": "rich-buttons/retained-late-effect.json",
            }
            if completion == "mismatch":
                outcome["reason"] = {"code": "effect_mismatch"}
            return outcome

    backend = DelayedInput()
    ordinary, rich = setup(tmp_path, native=backend)
    target_id = rich.rich_buttons(chat_id=1, message_id=1)["targets"][2]["target_id"]
    first = rich.tap_rich_button(target_id=target_id)
    assert first["status"] == "uncertain" and first["dispatch"] == "dispatched"
    journal = tmp_path / "rich-button-journal.jsonl"
    before = journal.read_bytes()
    if completion in {"exception", "malformed"}:
        with pytest.raises((OSError, RuntimeError, ValueError)):
            rich.tap_rich_button(target_id=target_id)
        assert rich.failed and rich.failure == "rich_button_component_failed"
        final = first
        assert journal.read_bytes() == before
    else:
        final = rich.tap_rich_button(target_id=target_id)
        expected = first | {
            "evidence": first["evidence"]
            | {
                "native": first["evidence"]["native"]
                | {"effect": "rich-buttons/retained-late-effect.json"},
            }
        }
        if completion == "success":
            expected.update(
                status="succeeded", effect={"kind": "none", "reason": "disabled"}, reason=None
            )
        assert final == expected
        retained = journal.read_bytes()
        assert rich.tap_rich_button(target_id=target_id) == final
        assert journal.read_bytes() == retained
        assert not rich.failed
    assert backend.dispatched == 1
    assert backend.polls == (2 if completion == "uncertain" else 1)
    assert ordinary.records == [final]
    with World.open(tmp_path / "world") as world:
        assert world.poll_updates(2) == []
        assert len(world.events()) == 4
    rich.close()
    assert recover_journal(journal)["receipts"] == [final]
