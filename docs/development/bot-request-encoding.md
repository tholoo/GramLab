# Bot API request encodings

The local Bot API accepts UTF-8 URL query parameters, POST JSON objects and POST
`application/x-www-form-urlencoded` bodies for its implemented methods. This lets a real bot use
form requests for polling, replies and formatting edits while Android observes the same world.
The change stays within the approved HTTP/world boundary; it adds no network access, schema
migration or Android patch.

## Contract and sources

The selected baseline remains Bot API 10.3. The official
[request contract](https://core.telegram.org/bots/api#making-requests) specifies GET/POST,
query/form/JSON parameter transport and UTF-8. The
[message contract](https://core.telegram.org/bots/api#sendmessage) describes serialized entities
and reply markup. The official server's
[argument handling](https://github.com/tdlib/telegram-bot-api/blob/master/telegram-bot-api/Client.cpp)
was inspected on 2026-09-06 for textual Boolean interpretation. That moving source is a behavioral
reference, not a pinned executable or an external conformance run. No implementation was copied.

- Query parameters work with GET or an otherwise empty POST without a content type.
- POST forms preserve blank values, UTF-8 percent encoding and the distinction between spaces
  and literal plus signs. A `charset=UTF-8` content-type parameter is accepted.
- `reply_markup` and `entities` accept native JSON structures or a JSON-serialized string,
  including when that string is supplied through query parameters or a form.
- `answerCallbackQuery.show_alert` accepts native JSON Booleans and text. After trimming and
  case normalization, `true`, `yes` and `1` mean true; other strings mean false, following the
  inspected server behavior. A non-Boolean JSON value such as an array is rejected.
- Ordinary text is never JSON-decoded or Boolean-coerced. Method and world validation still
  apply after decoding; an encoding cannot enable an unsupported method or parameter.

JSON responses and the underlying message/entity/keyboard structures are identical across these
encodings. Query/body fields may be combined only when names do not overlap. Repeated form/query
fields, overlapping query/body names and repeated JSON members are rejected, including members
inside a serialized complex parameter. These ambiguity rules are intentionally stricter local
validation, not a claim about Telegram's handling of malformed requests.

## Rejection and limits

Invalid UTF-8 is rejected before any mutation or update acknowledgment. JSON bodies are explicitly
decoded as UTF-8; Python's automatic UTF-16/UTF-32 JSON detection is not used. Malformed or deeply
nested JSON returns a structured HTTP 400 instead of dropping the connection. Nesting rejection
currently follows the Python JSON decoder's recursion limit, not a versioned nesting quota.

The existing prototype limits remain: 64 fields per query/form section, a 65,536-byte POST body,
no repeated parameters and no transfer encoding. Multipart uploads, file resolution, media APIs,
parse modes, polling filters and unimplemented methods remain explicitly unsupported. This
milestone does not establish compatibility with a particular third-party bot framework.

## Evidence and reproduction

[`test_bot_transport.py`](../../tests/test_bot_transport.py) sends actual HTTP requests and checks
complete responses, reopened world state, client snapshots and pending delivery. Nine cases cover
Unicode/escaping, five equivalent message encodings, callback Boolean forms and malformed inputs.
The invalid-input scenario checks unchanged state and pending updates after each rejection.
The initial regression proved that a UTF-16 JSON poll was incorrectly accepted and acknowledged
an update; strict UTF-8 decoding fixes it.

The independent [formatting bot](../../tests/fixtures/formatted_bot.py) now uses form requests,
including JSON-serialized entities. Its shared simulation-only and Android scenario retains the
same full semantic expectations. A fresh actual Android run shows the formatted reply and its
cold-restart persistence through the unchanged upstream renderer. Other real bot fixtures retain
JSON requests, so the core gate exercises both transports.

After provisioning, run the core/coverage gate in the
[outer network guard](runtime-boundary.md). For a focused encoding check, select
`tests/test_bot_transport.py`. Follow [formatting reproduction](formatted-text.md#reproduction)
for the Android scenario; the focused selection is
`tests/test_android_entities.py -k real_bot`. Use fresh ignored artifact directories.

Verification: 82 core tests pass at 91.99% statement coverage; the focused actual Android test
passes with original captures before/after formatting and after restart. Ruff and strict typing
pass. No client/APK changes were needed; the prior full thirteen-test Android gate is separate
evidence, not a suite rerun for this transport milestone. Broader compatibility and the full
GramLab goal remain open.
