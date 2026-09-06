# Experimental Python scenario client

`gramlab.scenario.Scenario` now provides Python methods for the existing
[world control service](scenario-control.md). It runs inside a private scenario component and
does not import world storage, launch a bot or acquire credentials. The [consumer runner](consumer-runner.md)
now prepares selected files and launches simulation-only scenarios or headless Android captures.
This is an experimental
interface, not a stable SDK compatibility commitment.

## Using the interface

Trusted orchestration supplies `GRAMLAB_CONTROL_ENDPOINT`, `GRAMLAB_CONTROL_CAPABILITY` and
`GRAMLAB_WORLD_ID` to the private process. Within that process:

```python
from gramlab.scenario import Scenario

scenario = Scenario.from_environment()
user = scenario.create_user(first_name="Sara", language_code="fa")
bot = scenario.create_user(first_name="Echo", is_bot=True)
chat = scenario.open_private_chat(user_id=user["id"], bot_id=bot["id"])
scenario.send_message(chat_id=chat["id"], sender_id=user["id"], text="سلام hello")
history = scenario.history(chat["id"])
```

Creating a virtual bot identity does not start a consumer bot process. The current trusted
integration harness or consumer runner starts that separate process. With the runner, use
`scenario.bots()["echo"]` to identify the bot declared in the manifest. Do not
execute this snippet as host-side orchestration or grant it the world database directory.

The interface exposes twelve operations:

| Method | Effect or result |
| --- | --- |
| `create_user` | Create a virtual participant or bot identity |
| `open_private_chat` | Open the existing private user/bot conversation model |
| `send_message` | Create a synthetic message, including supported entities/keyboard fields |
| `advance_time` | Advance the explicit world clock by integer seconds |
| `history` | Read one chat's complete message history |
| `snapshot` | Read world metadata, participants and chats |
| `bots` | Read manifest bot aliases and their world IDs; empty without configured names |
| `events` | Read ordered events after an optional cursor |
| `create_callback` | Create a synthetic callback with an explicit durable request ID |
| `get_callback` | Observe that callback and its answer |
| `capture_chat` | Retain semantic evidence and original screenshots in headless Android mode |
| `tap_inline_button` | Select a callback keyboard cell, using actual input in Android mode |

Arguments and JSON-shaped results retain the existing world contract. This is not a second Bot
API client or a recreated Android interaction layer. A new HTTP connection is used for each call;
shared instances can make concurrent calls without sharing a socket or response buffer. Tests
exercise two shared clients with concurrent writers in two independent worlds.

`capture_chat` requires the consumer runner's capture service. Its expected-text checks,
artifacts, separate socket timeout and current rendering limits are documented in
[scenario captures](scenario-captures.md). Capture failures can have uncertain artifact/client
effects even though the operation does not create a simulated message.

`tap_inline_button` also requires the consumer runner. Its row/column selection, native targeting,
uncertain outcomes and runnable example are described in [scenario input](scenario-input.md).

## Failure contract

`ScenarioError` provides `operation`, `code`, `status` and `outcome_uncertain`. The client never
automatically retries a request, including callbacks whose server operation supports deduplication.

| Failure | Code | Possible committed effects from this command |
| --- | --- | --- |
| Invalid/oversized local JSON input | `invalid_request`, no HTTP status | No request was sent |
| Connection establishment fails | `transport_error`, no HTTP status | No request was sent |
| Validated server rejection | `invalid_request`, `unauthorized`, `unsupported` or `wrong_world` | Rejected without a new mutation |
| Connection/response fails after transmission may have begun | `transport_error` or `invalid_response` | Mutating calls are uncertain |
| Server returns HTTP 5xx | `server_error` | Mutating calls are uncertain |

Read-only failures have `outcome_uncertain=False` because those operations cannot mutate the
world. This says nothing about concurrent actions by other participants. For an uncertain write,
inspect relevant history/events/state before deciding what to do; do not treat a missing reply as
a failed transaction. General command deduplication and automatic replay remain unimplemented.

Failure messages do not echo credentials, request payloads or remote response text. Configuration
errors use static `ValueError` messages. The status and code distinguish known control rejection
from transport or protocol failure; detailed consumer diagnosis/reporting remains separate work.

## Transport limits

The client accepts only an explicit `http://127.0.0.1:<port>` origin and the proper run-control
capability/world identity. It defensively requires loopback-only interfaces, ignores ambient
proxy variables, follows no redirects and has no external fallback. The enclosing private
runtime remains the actual isolation mechanism.

Requests are UTF-8 JSON, limited to 65,536 bytes before transmission. Responses require a single
bounded length, JSON content type, exact envelope/version/world identity and the expected top-level
result shape. Duplicate members, invalid UTF-8, non-finite numbers, excessive nesting and malformed
or oversized bodies are rejected. The response limit is 16 MiB. This is protocol validation, not
independent verification of every semantic field returned by the world.

`timeout` defaults to five seconds and bounds socket operations. It is not a whole-scenario or
absolute command deadline against continuously trickling input; the trusted runtime must still
bound the complete scenario lifetime. There is no connection pool or automatic pagination yet.

## Verification

The nine [client tests](../../tests/test_scenario_client.py) use real local HTTP. A relay lets the
actual world commit a command, then drops its response: exactly one participant/event exists,
and the client reports uncertainty without a retry. Other tests cover definite rejections,
invalid responses, redirects, connection/read failures, timeouts, HTTP 5xx, local input limits,
explicit configuration, poisoned proxy variables and callback identity/answers.

The [private scenario fixture](../../tests/fixtures/scenario_actor.py) now uses this SDK instead of
its hand-written HTTP code. Trusted preparation copies only the SDK module and package initializer
into the private component. The same full transcript, world state, event order and isolation
assertions continue to pass with a separately running real bot.

Run `tests/test_scenario_client.py` and `tests/test_world_control.py` in the
[documented outer guard](runtime-boundary.md) for focused checks. The full core gate passes
100 tests at 92.46% statement coverage; full lint/format and strict typing pass. Offline wheel and
source builds include the SDK and `py.typed`, with no generated runtime or client-derived files. No Android
source/runtime changes or new rendering evidence are part of this SDK transport milestone.
