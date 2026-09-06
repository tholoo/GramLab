# Long polling and bot delivery lifecycle

The local Bot API now accepts `getUpdates` with an integer `timeout`. A waiting request sees
committed updates from independent world writers, returns the existing Bot API message shape,
and leaves returned updates pending until a later offset confirms them. This extends the
[world/bot foundation](world-bot-prototype.md); it is not a completed polling/webhook profile.

## Contract and sources

The selected baseline remains Bot API 10.3. The official
[`getUpdates` specification](https://core.telegram.org/bots/api#getupdates) defines timeout,
positive-offset confirmation, batch limits and filter behavior. The official server's
[request/conflict handling](https://github.com/tdlib/telegram-bot-api/blob/master/telegram-bot-api/Client.cpp)
and [timeout constant](https://github.com/tdlib/telegram-bot-api/blob/master/telegram-bot-api/Client.h)
were inspected on 2026-09-06 as additional behavioral references. Those moving source links are
not a pinned server executable or external conformance run. No upstream implementation code was
copied into the MIT core.

- Timeout defaults to zero; integer values are bounded to 0–50 seconds. Existing pending updates
  return immediately. An empty queue waits until an update arrives or the deadline expires.
- The deadline uses monotonic runtime time. It neither advances nor waits for the synthetic
  world's explicit clock. GET integer strings and POST JSON integers are accepted.
- A newer valid poll for the same bot interrupts an outstanding poll with HTTP 409. Ownership
  follows authenticated bot identity within one server instance, not a token string or chat ID.
- Invalid parameters and invalid credentials do not acknowledge updates or displace a valid poll.
  Another bot or another world's server has independent polling ownership.
- Sending a response does not acknowledge its contents. A disconnected bot can retry and a
  restarted server can deliver the same still-pending update.

Negative offsets, `allowed_updates`, webhook configuration and 24-hour update expiry remain
unsupported. The official server's flood/backoff behavior and exact millisecond response timing
are not modeled. The prototype retains stricter validation for malformed integers and limits.

## Execution and shutdown

The server serializes poll ownership and each short acknowledgment/read operation. It releases
both that lock and the SQLite transaction while waiting. A bounded 50 ms reread interval sees
changes from other world connections/processes without adding a second authority or requiring
in-process writer notifications. This polling strategy has not been load-qualified for large bot
counts; it is not a promise of deterministic delivery latency or an efficient fleet scheduler.

Leaving `BotAPIServer` wakes pending polls with a labeled local HTTP 503 shutdown response, closes
connections still reading incomplete HTTP input, and joins request threads. Normal disconnects
do not generate access/error traces. World history and unacknowledged updates persist. The outer
runtime timeout still bounds the complete scenario; aggregate connection/resource quotas remain
open. A disconnected poll may remain registered until another poll, an update, its timeout or
server shutdown releases it.

This prototype expects one Bot API server per world. Separate server instances pointing at the
same database do not coordinate live polling ownership. Distributed consumers and webhook/polling
conflicts require further contracts. No network boundary, Android patch or persistence schema was
changed for this milestone.

## Behavioral evidence

[`test_polling.py`](../../tests/test_polling.py) uses real HTTP requests and public world operations.
A committed acknowledgment of a sentinel establishes that a request reached the world before a
writer, competing poll or shutdown acts. Tests do not substitute a guessed sleep for that ordering.
The suite covers timeout without world-clock movement, later delivery/repetition/confirmation,
same-bot conflicts, independent bots/worlds, invalid options, disconnected retries, server restart,
pending-poll shutdown and incomplete-body shutdown. An initial cross-bot expectation was corrected
to respect the world's existing per-chat message identifiers.

The [real bot probe](../../tests/probes/long_poll_bot.py) starts the independently running echo
fixture inside its private component before the virtual user supplies the message. Its offset
confirms a readiness sentinel, then a later mixed Persian/English message reaches the waiting bot.
The bot replies and acknowledges through HTTP. The test checks the full transcript and exact
world history. The same echo fixture now requests long polling in the existing Android cases.

Regression evidence first showed rejected timeout parameters, missing competing-poll cancellation,
orphaned waits on shutdown, disconnect tracebacks and a shutdown delayed by an incomplete body.
Each behavior was reproduced before its correction. Run the core and Android gates through the
outer network guard described in [CONTRIBUTING.md](../../CONTRIBUTING.md) and
[the runtime boundary](runtime-boundary.md). Transcripts, timing observations and process handles
belong in ignored artifacts/local notes, never in public machine inventory.

Verification on 2026-09-06 passes all 51 core tests at 91.04% statement coverage and all ten Android
tests, including the real tap/edit/bot-and-client restart with component separation. The final
client restart screenshot retains the expected edited reply. Ruff, strict typing, Nix platform
evaluation, workflow/configuration and local-link/privacy checks pass. The Android source and APK
are unchanged. The wider runtime safety, compatibility, scenario and reporting goal remains active.
