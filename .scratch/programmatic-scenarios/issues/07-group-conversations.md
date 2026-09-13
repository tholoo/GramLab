# Add synthetic group conversations

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: none

Add a generic group-chat and membership model to the simulated World so installed consumers can
exercise causal behavior across private administration and group participation. Keep the model
consumer-neutral, offline, durable, and owned by the same World used by Bot API and scenario
control. Do not add consumer names, policies, fixtures, paths, or assumptions to GramLab.

The first vertical slice is simulation behavior. Native Android evidence follows only after the
shared client bridge can represent the same group without a private-chat approximation.

## Acceptance

- Public World operations create one titled synthetic group with explicit virtual-user and bot
  memberships and reject unknown, duplicate, botless, or unauthorized membership combinations.
- A virtual group member can send a message which reaches each member bot through the existing
  polling update queue with a complete Telegram-compatible group chat envelope.
- A member bot can send and edit messages in the group and `getChatMember` returns the modeled
  status for the requested participant; nonmembers and unrelated bots are rejected.
- Group identity, memberships, messages, pending updates, callbacks, and member visibility survive
  World restart and remain isolated between worlds.
- The authenticated schema-1 control service and experimental typed scenario SDK expose group
  creation and conversation handles without retrying uncertain writes or breaking existing raw
  private-chat operations.
- A contained generic bot/scenario proves two virtual users, one bot, group delivery, membership
  lookup, callback behavior, and bot restart through public interfaces.
- The compatibility and scenario documentation state what simulation proves and whether the
  current Android bridge can render the group honestly.
- Focused red/green evidence, strict typing, Ruff, packaging checks, and the applicable non-Android
  gate pass. Android evidence is required before claiming native group support.

## Comments

Approved on 2026-09-13 to enable high-value cross-role consumer scenarios. The public seams are the
World, local Bot API, authenticated scenario control, typed scenario SDK, and contained runner.
