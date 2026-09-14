# Operate a persistent playground from a browser

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: 10-interactive-playground.md

Add a consumer-neutral loopback web client for an existing persistent playground. The browser
must list every seeded conversation, render its current history and rich-button labels, allow a
seeded human actor to type and send a message, and press a visible rich button. It must also expose
authorized bot addition, exact reset and stop without requiring command-line control.

The web client binds only to loopback, keeps the Unix-socket capability on the host, rejects
cross-origin state changes and treats every message and label as text. Starting it yields one URL
that a consumer launcher can open. Polling refreshes the authoritative World after bot replies and
reset. This browser surface is a semantic playground client, not Telegram rendering-fidelity
evidence; headless Android remains the fidelity boundary.

## Public seams

- A browser-level HTTP acceptance drives status, send, rich-button input, add-bot, reset and stop
  through the same authenticated playground control used by the CLI.
- Rejected origins, malformed payloads, unknown actors/chats and stale playground ownership do not
  mutate state or disclose the control capability.
- Generic UI code contains no consumer application terminology, identities or chat assumptions.

Approved by the user on 2026-09-14 after the command-driven playground produced no interactive
window. They explicitly requested a clickable input bar and normal typing/sending instead of
terminal commands.

Resolved on 2026-09-14. The public `--web --no-open` acceptance loads the page, sends exact composer
text through the browser boundary, observes the real contained bot's rich reply, presses its
visible button and observes the edit, adds the configured bot to a different seeded group, then
proves Reset restores both complete histories and membership before Stop. Cross-origin and unknown-
actor sends are rejected with exact World equality. A separate lifecycle check proves the browser
opener receives the random loopback URL. The interrupted-owner regression proves SIGINT removes
both stale controls and retains a failed `supervisor_interrupted` report.

The focused non-Android playground collection passes 5 tests. Repository Ruff lint and format
checks, strict package typing and the full contained non-Android gate pass. The gate reports 1,628
tests at 85.12% coverage. A real consumer integration additionally opened the page in Zen and a
headless Chromium DOM render showed its four loaded chats, ready state and composer. Android was not
rerun because the browser is a separate semantic host surface and the original-client path did not
change. Publication remains subject to explicit remote approval.
