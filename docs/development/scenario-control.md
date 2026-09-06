# World control from private scenario code

An internal `WorldControl` service now lets an isolated scenario process drive the existing
authoritative world through local JSON. Trusted orchestration retains the SQLite directory and
bot/client lifecycle. This implements the per-run control capability anticipated by the
[approved proposal](android-foundation-proposal.md), using the existing
[private component runtime](component-boundary.md).

The [programmable scenario workstream](../../.scratch/programmatic-scenarios/spec.md) remains
active. This service is internal (`gramlab._control`); the consumer SDK, source packaging,
launcher and automatic failure artifacts are not implemented yet. Do not run consumer Python
in the trusted supervisor to bypass those remaining steps.

## Control contract

The trusted owner opens an existing world and creates one `WorldControl` instance for its run.
It receives a fresh `gramlab-control_` capability, independent of the world seed and bot/persona
credentials. The capability is held in memory and changes when the service is recreated. It
authorizes scenario control of that whole world, not a single persona.

The service binds an ephemeral IPv4 loopback port and requires a loopback-only interface list.
The actual egress boundary is the enclosing runtime namespace, not this defensive interface check.
Scenario code receives only the explicit endpoint, control capability and world ID, inside its
own private component. It receives no world database, bot token or client capability.

Requests use `POST /v1/world`, one `Authorization: Bearer <capability>` header,
`Content-Type: application/json` and one bounded `Content-Length`. The UTF-8 JSON envelope has
exactly these fields:

```json
{
  "schema": 1,
  "world_id": "the-world-identity-issued-by-the-run-owner",
  "operation": "send_message",
  "parameters": {"chat_id": 1, "sender_id": 1, "text": "سلام hello"}
}
```

Successful responses contain `schema`, `world_id` and `result`. Result values use the existing
world shapes, including internal chat/message IDs; they are not Bot API response objects.
An explicit operation table exposes only:

- `create_user`, `open_private_chat` and `send_message`;
- `create_callback` and `get_callback`;
- `advance_time`, `history`, `snapshot` and `events`.

Parameter names follow those existing world methods. There is no method reflection, arbitrary
code execution, file-path selection, credential issuance or Bot API acknowledgment operation.
Control can create synthetic fixture state; a control action alone does not prove an Android
gesture or a real bot's behavior. The real-process evidence below requires an actual bot reply.

Wrong credentials return HTTP 401, unknown operations/endpoints return 404, wrong-world requests
return 409 and malformed input returns 400. Errors contain an `error` object with `code` and
`message`. The service rechecks the opened database's world ID before each operation, so a
capability cannot silently follow a directory replaced with another world.

Duplicate JSON members, unsupported envelope fields, invalid scalar types, malformed UTF-8,
non-finite JSON values, excessive nesting, transfer encoding and duplicate length/authorization
headers are rejected before mutations. The request body limit is 65,536 bytes; incomplete bodies
cannot commit even if the received prefix is valid JSON. Connection input uses a one-second
socket timeout. Disconnects produce no access tracebacks, and service exit joins request threads.

## Ordering and recovery limits

Each operation uses the existing public world transaction; multiple HTTP writers share SQLite's
committed event order. This does not introduce a new state authority or change the storage schema.
`snapshot` retains its existing metadata/users/chats shape; history and events are separate reads,
not an atomic bundle. Android continues using its persona snapshot/event interface.

`create_callback` retains its existing durable `request_id` deduplication. Other mutating control
operations are not deduplicated. If a connection fails after sending a mutation, the caller must
treat the outcome as uncertain and inspect state rather than automatically retrying. A durable
general command journal and an SDK exception carrying this uncertainty remain open work.

## Evidence and reproduction

The [HTTP tests](../../tests/test_world_control.py) verify complete transitions and reopened state,
credential/world scope, malformed inputs, replacement-world rejection, callback retries/answers,
incomplete-body behavior and concurrent writers in two worlds. Report redaction recognizes the
new control capability, including occurrences embedded in otherwise ordinary text.

The [independent scenario actor](../../tests/fixtures/scenario_actor.py) creates virtual participants
and sends a mixed-language message from its private component. A separately running real echo bot
receives the update and replies through the Bot API. The test compares complete bot responses,
scenario/world state, history and ordered events. The actor cannot see world/bot paths, has only
loopback and observes an external connection rejected with `ENETUNREACH`. Its writable state stays
in its own directory. No scenario code runs directly in the supervisor.

After provisioning, select `tests/test_world_control.py` in the
[documented outer network guard](runtime-boundary.md). Use a fresh ignored artifact directory to
retain the real-process `scenario-result.json`, private state and world database. The full core
gate passes 91 tests at 92.07% statement coverage. Strict typing, lint/format, Nix/direnv/workflow,
local links and public-tree privacy checks pass. There are no Android/client/APK changes or new
Android runs in this milestone; it is control/process evidence, not new rendering evidence.

Resource quotas, per-component port restrictions, full consumer packaging, Android connection
through the future scenario SDK, fault replay and automatic failure reports remain open.
