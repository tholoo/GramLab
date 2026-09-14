# Operate a persistent playground from a browser

Type: task
Status: ready-for-agent
Work state: claimed
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
