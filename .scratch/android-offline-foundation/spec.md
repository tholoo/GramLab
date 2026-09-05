# Android offline foundation

Status: ready-for-agent
Work state: claimed

## Objective

Prove that a real local bot and a minimally patched Telegram Android client can interact through
one isolated simulated world, without real Telegram accounts or external network traffic.

## Acceptance

1. Pin source/runtime/schema/asset provenance and make the dedicated offline build reproducible.
2. Create a synthetic identity and chat without any login request or real session.
3. Run a minimal real bot against the local Bot API boundary and display its message in Android.
4. Tap an actual client button, deliver its callback to the bot and render the bot's edit.
5. Restart the bot/client as specified and recover the same isolated world without cross-run state.
6. Capture semantic assertions, screenshots, relevant logs, state and independently enforced
   zero-egress evidence. Test attempts to violate the boundary.
7. Exercise English/Persian input and one rich-message/media/custom-emoji exploration case,
   explicitly marking any unsupported contract rather than fabricating success.

This milestone proves the risky architecture. It does not shrink the broader
[product requirements](../../docs/product/requirements.md) or claim complete compatibility.

## Tickets

- [01: Validate Android integration and runtime](issues/01-validate-android-seam.md)
- [02: Enforce isolation and establish synthetic state](issues/02-offline-world-and-safety.md)
- [03: Complete the real bot/Android interaction loop](issues/03-bot-android-round-trip.md)
- [04: Recovery, concurrency and diagnostic report](issues/04-recovery-concurrency-report.md)
- [05: Expand the authoritative compatibility backlog](issues/05-compatibility-expansion.md)

## Open design work

Ticket 01 should recommend the exact pin/runtime, bridge, schema provenance and proof strategy.
Storage/replay and runtime enforcement need evidence-backed decisions, with user consultation
before consequential commitments. Public SDK APIs follow those findings, not speculative stubs.

## Comments

The user approved scaffolding only in the preparation session; implementation belongs to the next
agent initialized in GramLab. No simulator or Android functionality was implemented in that session.

2026-09-05: The active goal authorizes building the full product and local commits, while retaining
consultation for consequential choices. Ticket 01 is resolved; ticket 02 is claimed. Source and
host investigation support
a [concrete prototype proposal](../../docs/development/android-foundation-proposal.md); its design
choices were approved by the user. No foundation acceptance criterion is claimed complete.
