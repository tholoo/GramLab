"""The scenario client preserves control results and never retries uncertain writes."""

import http.client
import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from gramlab._control import WorldControl
from gramlab.world import World


@contextmanager
def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_scenario_client_drives_the_existing_world_contract(tmp_path: Path):
    from gramlab.scenario import Scenario

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as server:
        scenario = Scenario(server.base_url, capability=server.capability, world_id=server.world_id)
        alice = {"id": 1, "is_bot": False, "first_name": "Alice", "language_code": "fa"}
        bot = {"id": 2, "is_bot": True, "first_name": "Echo"}
        chat = {"id": 1, "type": "private", "user_id": 1, "bot_id": 2}
        message = {"id": 1, "chat_id": 1, "sender_id": 1, "date": 100, "text": "سلام hello"}
        assert scenario.create_user(first_name="Alice", language_code="fa") == alice
        assert scenario.create_user(first_name="Echo", is_bot=True) == bot
        assert scenario.open_private_chat(user_id=1, bot_id=2) == chat
        assert scenario.send_message(chat_id=1, sender_id=1, text="سلام hello") == message
        assert scenario.advance_time(5) == 105
        assert scenario.history(1) == [message]
        assert scenario.snapshot() == {
            "schema": 1,
            "seed": 7,
            "now": 105,
            "users": [alice, bot],
            "chats": [chat],
        }
        assert scenario.events(after=3) == [
            {"sequence": 4, "type": "message.created", "data": message},
            {"sequence": 5, "type": "clock.advanced", "data": {"now": 105}},
        ]
    with World.open(directory) as world:
        assert world.history(1) == [message]
        assert world.poll_updates(2) == [{"update_id": 1, "message": message}]


def test_lost_mutation_response_is_uncertain_and_is_never_retried(tmp_path: Path):
    from gramlab.scenario import Scenario, ScenarioError

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    forwarded = []
    with WorldControl(directory) as control:
        target = urlsplit(control.base_url)

        class DropAfterCommit(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = self.rfile.read(int(self.headers["Content-Length"]))
                upstream = http.client.HTTPConnection(target.hostname, target.port, timeout=3)
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
                    forwarded.append((response.status, json.loads(response.read())))
                    # The authoritative mutation has completed. Lose only its response.
                finally:
                    upstream.close()

            def log_message(self, *args):
                pass

        with serve(DropAfterCommit) as endpoint:
            scenario = Scenario(endpoint, capability=control.capability, world_id=control.world_id)
            caught = None
            try:
                scenario.create_user(first_name="Once")
            except Exception as error:
                caught = error
        with World.open(directory) as world:
            user = {"id": 1, "is_bot": False, "first_name": "Once"}
            assert world.snapshot()["users"] == [user]
            assert world.events() == [{"sequence": 1, "type": "user.created", "data": user}]
        assert forwarded == [(200, {"schema": 1, "world_id": control.world_id, "result": user})]
        assert isinstance(caught, ScenarioError)
        assert (caught.operation, caught.code, caught.outcome_uncertain, caught.status) == (
            "create_user",
            "transport_error",
            True,
            None,
        )
        assert control.capability not in str(caught) + repr(caught)


def test_known_control_rejections_are_reported_without_uncertain_effects(tmp_path: Path):
    from gramlab.scenario import Scenario, ScenarioError

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100) as world:
        before = world.snapshot()
    with World.create(tmp_path / "other", seed=7, now=100):
        pass
    with WorldControl(directory) as server, WorldControl(tmp_path / "other") as other:
        for capability, world_id, name, code, status in [
            (other.capability, server.world_id, "forged", "unauthorized", 401),
            (server.capability, other.world_id, "forged", "wrong_world", 409),
            (server.capability, server.world_id, "", "invalid_request", 400),
        ]:
            scenario = Scenario(server.base_url, capability=capability, world_id=world_id)
            with pytest.raises(ScenarioError) as failure:
                scenario.create_user(first_name=name)
            assert (failure.value.code, failure.value.status, failure.value.outcome_uncertain) == (
                code,
                status,
                False,
            )
    with World.open(directory) as world:
        assert world.snapshot() == before
        assert world.events() == []


def test_invalid_responses_are_not_success_or_safe_mutation_rejections(tmp_path: Path):
    from gramlab.scenario import Scenario, ScenarioError

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    responses, requests = [], []

    class Peer(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            status, headers, body = responses.pop(0)
            self.send_response(status)
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    with WorldControl(directory) as control, serve(Peer) as endpoint:
        scenario = Scenario(endpoint, capability=control.capability, world_id=control.world_id)
        valid = {"schema": 1, "world_id": control.world_id, "result": {"id": 1}}
        malformed = [
            valid | {"world_id": "another-world"},
            valid | {"schema": True},
            valid | {"schema": 2},
            [],
            {},
            valid | {"extra": 1},
            valid | {"result": "wrong type"},
            valid | {"result": {"value": float("nan")}},
            valid | {"result": {"value": "\ud800"}},
        ]
        bodies = [json.dumps(value).encode() for value in malformed]
        bodies += [
            json.dumps(valid).replace('"schema": 1', '"schema": 1, "schema": 1').encode(),
            json.dumps(valid).encode("utf-16"),
            b"\xff",
            b"{",
            b"[" * 1100 + b"]" * 1100,
        ]
        cases = [
            (200, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))], body)
            for body in bodies
        ]
        cases += [
            (200, [("Content-Type", "text/plain"), ("Content-Length", "2")], b"{}"),
            (
                200,
                [
                    ("Content-Type", "application/json"),
                    ("Content-Length", "2"),
                    ("Content-Length", "2"),
                ],
                b"{}",
            ),
            (
                200,
                [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(16 * 1024 * 1024 + 1)),
                ],
                b"",
            ),
            (302, [("Location", control.base_url + "/v1/world"), ("Content-Length", "0")], b""),
            (400, [("Content-Length", "0")], b""),
        ]
        for index, response in enumerate(cases):
            responses.append(response)
            caught = None
            try:
                scenario.create_user(first_name="Once")
            except Exception as error:
                caught = error
            assert isinstance(caught, ScenarioError), index
            assert (caught.code, caught.outcome_uncertain, caught.status) == (
                "invalid_response",
                True,
                response[0],
            ), index
            assert len(requests) == index + 1
            assert control.capability not in str(caught) + repr(caught)
        # A rejected redirect must not reach the actual control service.
        with World.open(directory) as world:
            assert world.snapshot()["users"] == []
        for action, result, uncertain in (
            (lambda: scenario.advance_time(1), True, True),
            (lambda: scenario.history(1), [1], False),
            (scenario.snapshot, None, False),
        ):
            body = json.dumps(valid | {"result": result}).encode()
            responses.append(
                (
                    200,
                    [("Content-Type", "application/json"), ("Content-Length", str(len(body)))],
                    body,
                )
            )
            with pytest.raises(ScenarioError) as failure:
                action()
            assert (failure.value.code, failure.value.outcome_uncertain) == (
                "invalid_response",
                uncertain,
            )


def test_connect_failures_and_failed_reads_do_not_imply_world_mutations(tmp_path: Path):
    from gramlab.scenario import Scenario, ScenarioError

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as control, socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))  # Reserve the port without listening.
        scenario = Scenario(
            f"http://127.0.0.1:{unavailable.getsockname()[1]}",
            capability=control.capability,
            world_id=control.world_id,
        )
        with pytest.raises(ScenarioError) as failure:
            scenario.create_user(first_name="Never sent")
        assert (failure.value.code, failure.value.outcome_uncertain, failure.value.status) == (
            "transport_error",
            False,
            None,
        )

        class BrokenRead(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))

        with serve(BrokenRead) as endpoint:
            scenario = Scenario(endpoint, capability=control.capability, world_id=control.world_id)
            with pytest.raises(ScenarioError) as failure:
                scenario.snapshot()
            assert failure.value.code == "transport_error"
            assert failure.value.outcome_uncertain is False


def test_invalid_request_values_fail_locally_without_sending_or_leaking(tmp_path: Path):
    from gramlab.scenario import Scenario, ScenarioError

    with World.create(tmp_path / "world", seed=7, now=100):
        pass
    received = []

    class Reject(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.rfile.read(int(self.headers["Content-Length"])))
            body = b'{"error":{"code":"invalid_request","message":"too large"}}'
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    with WorldControl(tmp_path / "world") as control, serve(Reject) as endpoint:
        scenario = Scenario(endpoint, capability=control.capability, world_id=control.world_id)
        for value in ("x" * 65536, b"private-payload", "\ud800", float("nan")):
            caught = None
            try:
                scenario.send_message(chat_id=1, sender_id=1, text=value)
            except Exception as error:
                caught = error
            assert isinstance(caught, ScenarioError)
            assert (caught.code, caught.status, caught.outcome_uncertain) == (
                "invalid_request",
                None,
                False,
            )
            assert "private-payload" not in str(caught)
            assert received == []


def test_configuration_and_environment_use_only_the_explicit_local_service(
    tmp_path: Path, monkeypatch
):
    from gramlab.scenario import Scenario

    with World.create(tmp_path / "world", seed=7, now=100):
        pass
    with WorldControl(tmp_path / "world") as control:
        values = {"capability": control.capability, "world_id": control.world_id}
        for endpoint in (
            "https://127.0.0.1:123",
            "http://localhost:123",
            "http://192.0.2.1:123",
            "http://127.0.0.1:0",
            "http://127.0.0.1:private-configuration-value",
            "http://private-configuration-value@127.0.0.1:123",
            "http://127.0.0.1:123/path",
            "http://127.0.0.1:123?x=1",
            "http://127.0.0.1:123#fragment",
            "\nhttp://127.0.0.1:123",
        ):
            with pytest.raises(ValueError) as failure:
                Scenario(endpoint, **values)
            assert "private-configuration-value" not in str(failure.value)
        for changes in (
            {"timeout": 0},
            {"timeout": True},
            {"timeout": float("inf")},
            {"capability": "private-configuration-value"},
            {"world_id": "private-configuration-value"},
        ):
            with pytest.raises(ValueError) as failure:
                Scenario(control.base_url, **(values | changes))
            assert "private-configuration-value" not in str(failure.value)
        monkeypatch.setenv("GRAMLAB_CONTROL_ENDPOINT", control.base_url)
        monkeypatch.setenv("GRAMLAB_CONTROL_CAPABILITY", control.capability)
        monkeypatch.setenv("GRAMLAB_WORLD_ID", control.world_id)
        # A closed local proxy would make any accidental proxy discovery fail this request.
        with socket.socket() as proxy:
            proxy.bind(("127.0.0.1", 0))
            poison = f"http://127.0.0.1:{proxy.getsockname()[1]}"
            for name in (
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
            ):
                monkeypatch.setenv(name, poison)
            monkeypatch.setenv("NO_PROXY", "")
            monkeypatch.setenv("no_proxy", "")
            scenario = Scenario.from_environment()
            assert scenario.snapshot() == {
                "schema": 1,
                "seed": 7,
                "now": 100,
                "users": [],
                "chats": [],
            }
            assert control.capability not in repr(scenario)
        monkeypatch.delenv("GRAMLAB_CONTROL_CAPABILITY")
        with pytest.raises(ValueError, match="configuration"):
            Scenario.from_environment()


def test_scenario_callback_methods_keep_durable_identity_and_answer_state(tmp_path: Path):
    from gramlab.scenario import Scenario

    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as control:
        scenario = Scenario(
            control.base_url, capability=control.capability, world_id=control.world_id
        )
        scenario.create_user(first_name="Alice")
        scenario.create_user(first_name="Echo", is_bot=True)
        scenario.open_private_chat(user_id=1, bot_id=2)
        keyboard = {"inline_keyboard": [[{"text": "Choose", "callback_data": "سلام"}]]}
        entities = [{"type": "bold", "offset": 0, "length": 6}]
        message = scenario.send_message(
            chat_id=1, sender_id=2, text="Choose", reply_markup=keyboard, entities=entities
        )
        assert message == {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 100,
            "text": "Choose",
            "reply_markup": keyboard,
            "entities": entities,
        }
        command = {
            "user_id": 1,
            "chat_id": 1,
            "message_id": 1,
            "data": "سلام",
            "request_id": "tap-1",
        }
        callback = scenario.create_callback(**command)
        assert callback == {
            "id": callback["id"],
            "user_id": 1,
            "chat_id": 1,
            "message": message,
            "data": "سلام",
            "chat_instance": callback["chat_instance"],
            "answer": None,
        }
        assert scenario.create_callback(**command) == callback
        with World.open(directory) as world:
            world.answer_callback(bot_id=2, callback_id=callback["id"], text="Confirmed")
        assert scenario.get_callback(user_id=1, callback_id=callback["id"]) == callback | {
            "answer": {"text": "Confirmed", "show_alert": False, "cache_time": 0},
        }


def test_response_timeouts_and_server_errors_never_trigger_retries(tmp_path: Path):
    from gramlab.scenario import Scenario, ScenarioError

    with World.create(tmp_path / "world", seed=7, now=100):
        pass
    release = threading.Event()
    requests = []
    behavior = ["stall"]

    class Peer(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            status = 200 if behavior[0] == "stall" else 503
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "100")
            self.end_headers()
            if behavior[0] == "stall":
                release.wait(timeout=5)

        def log_message(self, *args):
            pass

    with WorldControl(tmp_path / "world") as control, serve(Peer) as endpoint:
        scenario = Scenario(
            endpoint, capability=control.capability, world_id=control.world_id, timeout=0.5
        )
        try:
            with pytest.raises(ScenarioError) as failure:
                scenario.create_user(first_name="Unknown")
            assert (failure.value.code, failure.value.outcome_uncertain, failure.value.status) == (
                "transport_error",
                True,
                200,
            )
        finally:
            release.set()
        assert len(requests) == 1
        behavior[0] = "server_error"
        for action, uncertain in (
            (lambda: scenario.create_user(first_name="Unknown"), True),
            (scenario.snapshot, False),
        ):
            with pytest.raises(ScenarioError) as failure:
                action()
            assert (failure.value.code, failure.value.outcome_uncertain, failure.value.status) == (
                "server_error",
                uncertain,
                503,
            )
        assert len(requests) == 3
