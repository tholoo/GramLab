# Reusing Bot API testing projects

Reviewed on 2026-09-06. This is a source-based assessment, not a runtime compatibility result.
No candidate was installed, executed, imported, or adopted. Source snapshots below make the
observations reproducible; they are not new GramLab dependency pins.

Existing projects can reduce work on schema inventories, request fixtures, fault controls and
load scenarios. Acceptance of an API method does not establish that it changes a coherent chat
world, delivers the corresponding updates, or renders in the original Android client. GramLab's
[single authoritative world](../adr/0004-semantic-bridge-and-world-persistence.md) and
[licensing boundaries](licensing.md) remain the evaluation criteria.

## Emulate's proposed Telegram emulator

This is the strongest candidate for a bounded stateful-backend comparison. At review time,
[Vercel Labs Emulate PR 75](https://github.com/vercel-labs/emulate/pull/75) is open and unmerged;
the inspected proposal lives at
[revision `886d2fe`](https://github.com/serejke/emulate/tree/886d2fe944297435a83ea83eeaf80c0c1ebf7f1e)
with an [Apache-2.0 license](https://github.com/serejke/emulate/blob/886d2fe944297435a83ea83eeaf80c0c1ebf7f1e/LICENSE).
Treat it as proposed work, not an established Telegram feature of the released parent project.

The [Bot API routes](https://github.com/serejke/emulate/blob/886d2fe944297435a83ea83eeaf80c0c1ebf7f1e/packages/%40emulators/telegram/src/routes/bot-api.ts)
implement stateful sends with chat/membership checks, edits with existence/ownership checks,
media bytes and file identifiers, and explicit unknown-method errors. The
[store](https://github.com/serejke/emulate/blob/886d2fe944297435a83ea83eeaf80c0c1ebf7f1e/packages/%40emulators/telegram/src/store.ts)
models bots, users, chats, messages, files, callbacks, updates, drafts, reactions, faults and
forum topics. The proposal describes in-memory state, webhook retries, polling confirmation,
fault scenarios and bot-framework integration tests. These are useful candidates for reuse or
comparison against original GramLab tests.

There is no `sendRichMessage` route in the inspected implementation. The proposal also lists
gaps including forwarding/copying, albums, inline queries, polls, payments and Web Apps.
It does not establish an offline original-Android renderer. Adopting its backend would require
reconciling its store with GramLab's Python/SQLite authority and client projection, so evaluate
media/webhook behavior and fixtures first. No integration or runtime compatibility is proven.

## telegym

Inspected [v0.2.0, revision `9064c17`](https://github.com/kolomiichenko/telegym/tree/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5),
whose [root license is MIT](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/LICENSE).
Its [README](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/README.md)
describes a Go mock, an xk6 virtual-user extension, a browser debug chat and a separate relay
through real Telegram. Only the offline mock/load components fit the present runtime boundary;
the relay is not an offline rendering solution.

The README's 176-method count is stale against the inspected
[embedded schema](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/pkg/mock/spec/api.json):
it identifies Bot API 10.2 and contains 185 methods, including `sendRichMessage` and
`sendRichMessageDraft`. That establishes schema awareness, not rich-message implementation.
The [explicit routes](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/pkg/mock/server.go)
do not handle those rich methods. The
[generic dispatcher](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/pkg/mock/dispatcher.go)
constructs a return-type-shaped zero value without storing a message; unknown methods can also
return success. There is no explicit `getUpdates` route, so its generic empty array is not a
polling queue.

The [handwritten handlers](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/pkg/mock/handlers.go)
retain text, entities, keyboards and selected photo/video/animation/sticker uploads. Their
semantics are intentionally small: `deleteMessage` returns success without deleting;
`editMessageText` appends an outbound record without checking that the original exists;
`getChatMember` supplies a fixed member result. Media dimensions are placeholders. This can
exercise bot branches but cannot serve as a conformance oracle for those behaviors.
The [store](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/pkg/mock/store.go)
is an in-memory, bounded outbound log, with per-bot webhook and callback state. It is not a
durable shared chat database. The
[message types](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/pkg/mock/types.go)
contain no rich-message field.

The strongest reuse candidate is its virtual-user/load tooling: text injection, callback clicks,
reply matching and user pools already have a
[scenario interface](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/pkg/xk6/user.go).
An adapter would still be needed for GramLab's world and scenario endpoints. Evaluate that
adapter before building a new load driver. Also evaluate the multipart fixtures and metrics
conventions separately from the permissive API implementation. The xk6 extension's
[module dependencies](https://github.com/kolomiichenko/telegym/blob/9064c17f89d6fbb7a6b363d701e3b4b5da7059f5/pkg/xk6/go.mod)
need their own license and packaging audit; the root MIT notice does not cover every dependency.

## tg-mock

Inspected [revision `c480d16`](https://github.com/watzon/tg-mock/tree/c480d163126f58fc7132d6d8308df66173238009),
after its latest listed v0.2.2 tag. The
[README](https://github.com/watzon/tg-mock/blob/c480d163126f58fc7132d6d8308df66173238009/README.md)
declares MIT, but the inspected recursive tree has no standalone license text. Preserve that
distinction and resolve the notice before importing source. Its
[schema](https://github.com/watzon/tg-mock/blob/c480d163126f58fc7132d6d8308df66173238009/spec/api.json)
identifies Bot API 9.2, contains 158 methods and has no rich-message methods.

The [request handler](https://github.com/watzon/tg-mock/blob/c480d163126f58fc7132d6d8308df66173238009/internal/server/bot_handler.go)
special-cases polling and webhook configuration, then delegates ordinary methods to generated
responses. Its polling path reads offset/limit and acknowledges earlier updates, but does not
implement a timeout wait or `allowed_updates` filtering. The
[responder](https://github.com/watzon/tg-mock/blob/c480d163126f58fc7132d6d8308df66173238009/internal/server/responder.go)
calls a faker for the first declared return type; successful sends and edits do not update a
chat world. The
[validator](https://github.com/watzon/tg-mock/blob/c480d163126f58fc7132d6d8308df66173238009/internal/server/validator.go)
checks required-field presence and explicitly leaves type validation as a TODO. README claims
of spec validation should therefore not be read as complete contract validation.

Its useful pieces are the generated method/type inventory, request inspection, configurable
error scenarios, success overrides and webhook test controls. These can accelerate transport
and failure-path testing after comparison with official contracts. File handling needs particular
care: although the README advertises uploads and configurable storage, the inspected request
parser handles JSON/form fields without a multipart upload path, and the
[server](https://github.com/watzon/tg-mock/blob/c480d163126f58fc7132d6d8308df66173238009/internal/server/server.go)
selects memory storage even when a storage directory is configured. Do not count it as a proven
media backend or durable store.

## telegram-test-api

Inspected [revision `f1e75d2`](https://github.com/jehy/telegram-test-api/tree/f1e75d2d98c895f9db839042dba2238950df6cda),
package version 4.2.1, with an actual
[MIT license text](https://github.com/jehy/telegram-test-api/blob/f1e75d2d98c895f9db839042dba2238950df6cda/LICENSE.md).
Its [route registry](https://github.com/jehy/telegram-test-api/blob/f1e75d2d98c895f9db839042dba2238950df6cda/src/routes/bot/index.ts)
implements nine methods: identity, polling, text send/edit, keyboard edit, deletion, webhook
set/delete and callback answer. Unknown methods return errors; there are no rich/media routes.
The [server state](https://github.com/jehy/telegram-test-api/blob/f1e75d2d98c895f9db839042dba2238950df6cda/src/telegramServer.ts)
retains messages in memory, but fetching updates immediately marks the returned items read.
The [polling route](https://github.com/jehy/telegram-test-api/blob/f1e75d2d98c895f9db839042dba2238950df6cda/src/routes/bot/getUpdates.ts)
does not forward offset, limit, timeout or allowed-update settings. It is a useful simple bot
test harness; its polling behavior and narrow API do not provide GramLab's recovery or rich
message contracts.

## Official Bot API server

The [official server](https://github.com/tdlib/telegram-bot-api) is a contract reference, not a
drop-in offline Telegram simulator. Its local mode changes the bot-facing server/file limits;
it still uses Telegram credentials and infrastructure. GramLab already records pinned Bot API
10.3 server and TDLib sources in the
[update-delivery review](update-delivery-references.md). Reuse those contracts and review source
licenses before adapting implementation; do not enable a real Telegram connection to fill a
simulator gap.

## Evaluation before adoption

Prefer a bounded comparison before another large batch of handwritten endpoint work:

1. Compare Emulate's proposed stateful Telegram implementation first, especially its media,
   webhook and contract-test components. Keep the comparison isolated from the current backend.
2. Pin and audit a current schema source, then compare the generated method/field inventory with
   GramLab's target. Keep generated structural coverage separate from semantic compatibility.
3. Exercise representative send, edit, delete, callback, media and rich-message contracts against
   each serious candidate in an isolated offline harness. Assert final state and update delivery,
   including unsupported-input errors, rather than only successful response parsing.
4. Evaluate adapting an existing virtual-user runner to GramLab's authoritative world, and using
   existing fault fixtures as references for original tests.
5. Measure adapter work and remaining semantic gaps before deciding whether to import a component
   or change the backend. A second mutable simulator beside GramLab would require an explicit
   synchronization design; no such architecture change is made by this review.

The reviewed implementations do not demonstrate offline original-Android rendering or the
durable client recovery contract. Schema and harness reuse can still accelerate those broader
features without discarding the existing renderer bridge. No runtime pass rate or schedule
reduction is claimed from source inspection alone.
