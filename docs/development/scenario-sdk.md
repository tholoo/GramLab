# Experimental Python scenario client

`gramlab.Scenario` provides typed scenario flows and raw Python methods for the existing
[world control service](scenario-control.md). It runs inside a private scenario component and
does not import world storage, launch a bot or acquire credentials. The [consumer runner](consumer-runner.md)
now prepares selected files and launches simulation-only scenarios or headless Android captures.
This is an experimental
interface, not a stable SDK compatibility commitment.

## Using typed scenario flows

Trusted orchestration supplies `GRAMLAB_CONTROL_ENDPOINT`, `GRAMLAB_CONTROL_CAPABILITY` and
`GRAMLAB_WORLD_ID` to the private process. Within that process:

```python
from gramlab import Scenario

scenario = Scenario.from_environment()
chat = scenario.conversation(
    user=scenario.user("Sara", language_code="fa"),
    bot="echo",
)
chat.send("سلام hello")
history = chat.wait_for_messages(2, timeout=10)
if history[1].text != "Echo: سلام hello":
    raise AssertionError("Unexpected bot reply")
chat.capture("echo", contains=["سلام hello", "Echo: سلام hello"])
```

`Scenario.user()` creates a virtual non-bot participant. `Scenario.bot()` resolves a configured
manifest bot, and `Scenario.conversation()` opens their private chat. Each returned handle belongs
to that exact `Scenario` instance; passing it to another instance fails before a control request.
`Conversation.send()`, `history()`, `capture()`, `type()` and `start()` bind the
chat and participant identities. History is an immutable tuple of `Message` observations. A
message owns `inline_button(row, column)`, whose `tap()` result exposes a `Callback` handle.

`Conversation.wait_for_messages()`, `Callback.wait_until_answered()` and
`Bot.wait_for_state()` repeatedly perform only the corresponding read operation. They never retry
an input or another uncertain write. Each requires a positive finite timeout and raises
`ScenarioWaitTimeout` with `operation`, `timeout` and the last safe JSON-shaped observation when
the state is not reached. Transport and protocol failures continue to raise `ScenarioError`
immediately. The fixed short polling interval is an implementation detail; synthetic World time is
not advanced.

Every handle provides a copied `raw` dictionary for complete contract assertions and interoperation
with code that still consumes JSON-shaped values. Mutating that copy does not change the handle.
The typed fields are immutable observations; call `history()`, `Callback.refresh()` or a wait method
to observe later state.

Creating a virtual bot identity through the raw interface does not start a consumer bot process.
The current trusted integration harness or consumer runner starts that separate process. With the
runner, `scenario.bot("echo")` identifies the bot declared in the manifest. Do not
execute this snippet as host-side orchestration or grant it the world database directory.

The public package exports `Scenario`, `ScenarioError`, `ScenarioWaitTimeout`,
`ScenarioFlowError`, `User`, `Bot`, `BotStatus`, `Conversation`, `Message`, `InlineButton`,
`InlineAction`, `Callback`, `Capture` and `InteractionReceipt`. The lower-level imports from
`gramlab.scenario` remain supported.

## Raw operations

`Scenario` still exposes the original twenty JSON-shaped operations:

| Method | Effect or result |
| --- | --- |
| `create_user` | Create a virtual participant or bot identity |
| `open_private_chat` | Open the existing private user/bot conversation model |
| `send_message` | Create a synthetic message, including supported entities/keyboard fields |
| `register_custom_emoji` | Register immutable local WebP/WebM bytes with a durable request ID |
| `advance_time` | Advance the explicit world clock by integer seconds |
| `history` | Read one chat's complete message history |
| `snapshot` | Read world metadata, participants and chats |
| `bots` | Read manifest bot aliases and their world IDs; empty without configured names |
| `events` | Read ordered events after an optional cursor |
| `create_callback` | Create a synthetic callback with an explicit durable request ID |
| `get_callback` | Observe that callback and its answer |
| `capture_chat` | Retain semantic evidence and original screenshots in headless Android mode |
| `rich_buttons` | Allocate canonical single-use rich-message targets for the current client lifetime |
| `tap_rich_button` | Consume one rich target and retain its callback, copy or disabled receipt |
| `tap_inline_button` | Select a callback keyboard cell, using actual input in Android mode |
| `start_bot_chat` | Press Start Bot in a new conversation and retain its `/start` send receipt |
| `type_message` | Compose supported text through the native editor or its semantic simulation |
| `bot_status` | Observe a configured bot's process generation and state |
| `stop_bot` | Hard-stop the expected bot generation and its descendants |
| `start_bot` | Replace a stopped generation while preserving private bot files |

Arguments and JSON-shaped results retain the existing world contract. The typed flows are an
additive authoring interface over those operations, not a second Bot
API client or a recreated Android interaction layer. A new HTTP connection is used for each call;
shared instances can make concurrent calls without sharing a socket or response buffer. Tests
exercise two shared clients with concurrent writers in two independent worlds.

`capture_chat` requires the consumer runner's capture service. Its expected-text checks,
artifacts, separate socket timeout and current rendering limits are documented in
[scenario captures](scenario-captures.md). Capture failures can have uncertain artifact/client
effects even though the operation does not create a simulated message.

`tap_inline_button` also requires the consumer runner. Its row/column selection, native targeting,
uncertain outcomes and runnable example are described in [scenario input](scenario-input.md).

`rich_buttons` and `tap_rich_button` use the runner’s [rich-button service](scenario-rich-buttons.md).
Observing can change the client lifetime and allocate targets, so it has write uncertainty despite
its observational name. Repeating a known target never dispatches a second input.

`start_bot_chat` and `type_message` use the runner's [composer service](scenario-composer.md).
That document specifies raw input versus accepted messages, formatting limits, new-chat state,
durable receipts and the actual Start Bot/composer example.

The bot lifecycle methods also require the consumer runner. See [scenario lifecycle](scenario-lifecycle.md)
for generation checks, persistent state, stop/restart uncertainty and a callback recovery example.

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

Ordinary requests are UTF-8 JSON, limited to 65,536 bytes before transmission. Custom-emoji
registration uses a dedicated authenticated route capped at 1 MiB including base64 media, with
separate decoded media bounds and a default 30-second socket timeout. See [local custom emoji](custom-emoji.md)
for formats, logical IDs, retry semantics and current verification limits. Responses require a single
bounded length, JSON content type, exact envelope/version/world identity and the expected top-level
result shape. Duplicate members, invalid UTF-8, non-finite numbers, excessive nesting and malformed
or oversized bodies are rejected. The response limit is 16 MiB. This is protocol validation, not
independent verification of every semantic field returned by the world.

`timeout` defaults to five seconds and bounds socket operations. It is not a whole-scenario or
absolute command deadline against continuously trickling input; the trusted runtime must still
bound the complete scenario lifetime. There is no connection pool or automatic pagination yet.

## Verification

The [flow tests](../../tests/test_scenario_flows.py) exercise the typed interface through real local
HTTP, including handle ownership, immutable message history, inline callbacks, captures, bot status,
bounded waits and timeout evidence. The contained [echo](../../examples/echo) and
[inline-button](../../examples/inline) scenarios import from `gramlab` and use typed flows, proving
the runner-supplied SDK includes the complete module.

The lower-level [client tests](../../tests/test_scenario_client.py) use real local HTTP. A relay lets the
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
