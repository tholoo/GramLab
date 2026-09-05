# Product requirements

Status: approved direction; all runtime capabilities below remain unimplemented.

GramLab is a reusable offline Telegram bot testing library and laboratory, not a consumer application game
harness. consumer application is a prospective demanding consumer. Support real bot processes through a
local Bot API boundary without requiring their implementation language to match GramLab.

## Execution and fidelity

Use one simulated world model for simulation-only, headless Android and interactive Android modes.
Independent runs may execute concurrently; participants within a run may act concurrently too.
Virtual users require no phone, SIM, login code or real Telegram session. Rendered client instances
are bounded resources; avoid altering Telegram's account-slot behavior to manufacture load.

Match the actual pinned Android client's supported surfaces. Pin Android OS image, fonts,
language, theme, display size/density and relevant assets. Expose differences and missing support.
Do not equate source presence, a plausible screenshot, or a successful mock response with verified
Telegram behavior. Official client updates require server-model and compatibility review as well
as rendering updates.

## Interaction inventory

Build a version-specific catalog from official Bot API/schema/client evidence, not a game list.
Cover commands, deep links, replies, inline queries/results, callbacks, message editing/deletion,
keyboards, polls/quizzes, media/albums/files, reactions, custom emoji, rich messages and Mini Apps.
Inventory additional current features such as business, payments/Stars, gifts and administrative
operations: model locally where meaningful, or report unsupported and explain the boundary.
Never simulate a real payment settlement or undocumented platform decision as verified reality.

Contexts include private chats, groups, supergroups, channels and supported topics. Model privacy,
membership/admin permissions, anonymous/sender-chat identities, bot blocking/removal, user departure
and migration where applicable. Reject meaningless combinations explicitly rather than inventing
Telegram support. Bot API transports include local long polling and webhook behavior.

## Edge cases and recovery

Cover duplicate/stale callbacks, missing/deleted/edited messages, invalid actions, wrong actor,
permission loss, concurrency, retries, out-of-order actions, abandoned interactions and recovery.
Inject 400/403/429/5xx responses, delays, disconnects, retries and response loss after an operation
has already committed. Keep normal protocol-valid operation separate from adversarial injection.
Persist run IDs, seeds, event ordering and relevant state for replay and failure minimization.

The library must support consumer-defined assertions; it cannot infer every bot's correct domain
behavior. Provide reset/seed/log hooks without assuming one consumer's database schema.

## Language and presentation

Treat participant language, client language, bot language and chat-level bot preferences as
independent inputs. English and Persian combinations are mandatory early cases, not the entire
language catalog. Cover RTL/LTR, punctuation, نیم‌فاصله, emoji, text expansion and special filenames.

Exercise actual rich-message blocks supported by the pinned client, not only ordinary formatted
text. Validate API exposure independently. Use deterministic local media and custom-emoji fixtures,
including inaccessible documents and entitlement/fallback cases. No production document ID is an
offline fixture merely because it looks valid.

Run actual local Mini Apps with a modeled host bridge, local authentication fixtures, themes,
launch contexts and failure cases. Audit WebView network paths separately. Local fixture signatures
are not Telegram-issued authorization.

## Preview and documentation

Preview messages without sending to Telegram. Export labeled conversation examples, screenshots,
and eventually recorded walkthroughs for bot help. Generate examples from passing scenarios where
possible; protect against leaking real identities or credentials into exported artifacts.

## Reports, UX and performance

Produce self-contained HTML run reports with run IDs, relevant requests/updates, user/chat/message
and consumer session IDs, event timelines, logs, state snapshots and screenshots when applicable.
Distinguish observed bugs, proposed fixes, applied fixes and verified fixes. Capture decisions and
before/after evidence, including UI/UX improvements when the consumer task authorizes changes.
Testing/reporting alone does not authorize modifying arbitrary consumer applications.

Measure throughput, p50/p95/p99 latency, queue growth and failures under documented workloads.
Separate bot work, simulator overhead, rendering cost and injected delay. Support optional handler
and database instrumentation to explain slow operations. Local results do not predict Telegram's
anti-abuse limits or production network performance. Use resource budgets, not unlimited spawning.

All suites are explicitly invoked initially. Real-Telegram conformance is a separate possible
workflow requiring new authorization, never fallback behavior in an offline run.
