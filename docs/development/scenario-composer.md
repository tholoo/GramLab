# Scenario composer and Start Bot input

The experimental scenario SDK can press the original **Start Bot** button and type into the
original Android composer. Simulation uses the same durable semantic send boundary and an
independently written text model checked against [native fixtures](composer-text-references.md).
The same consumer example passes in both modes, including formatted Persian/emoji text, equal
text sent twice, inline code, italic text and four real bot replies. The APK and renderer are
unchanged from the [native composer milestone](android-composer.md).

## Consumer contract

```python
chat = lab.open_private_chat(user_id=user["id"], bot_id=lab.bots()["echo"])
lab.capture_chat(chat_id=chat["id"], label="before-start", contains=[])
started = lab.start_bot_chat(chat_id=chat["id"])
typed = lab.type_message(chat_id=chat["id"], text="**سلام 👩🏽‍💻**\nhello")
accepted = typed["sends"][0]["message"]
```

`start_bot_chat` operates on a new empty conversation and sends the ordinary `/start` text.
Android taps the unique enabled **Start Bot** control; it uses the captured first-use screen
when already open. The pinned client can change its first-use display while loading a reopened
empty dialog, so a restart is not a substitute for pressing this button. The action has no deep-link
parameter or unblock behavior. It is distinct from `start_bot`, which restarts a bot **process**.

`type_message` requires existing conversation history. A new bot chat must be started first;
a scenario may also use the existing synthetic-message API to prepare an established fixture.
Each call checks an empty native draft, enters the raw text using Android accessibility, verifies
the resulting draft, and activates the original Send control once. It does not call a hidden
application text setter or insert a synthetic send as an Android fallback.

Both methods return `operation`, `chat_id`, raw `text`, `native` and `sends`. Each accepted receipt
contains its durable `request_id`, persona message `position` and complete semantic `message`.
The current profile produces one message, represented as a list to keep the result explicit.
Formatting delimiters can disappear from accepted text; entity offsets use UTF-16 code units.
Android results additionally retain input targeting/verification evidence, observed UI, launch
output when a launch occurred and elapsed duration. A retained first-use screen has no new launch
output. Input duration includes launch/observation and is not a gesture-only latency measurement.

The chat determines the virtual sender. Invalid chat IDs, unsupported input, stale Start Bot
requests and typing into a new empty conversation fail before input. Composer, Start Bot and
inline-button actions share the 64-record per-run limit and the same renderer lock as captures.
Shared scenario clients can call concurrently, but actual guest actions execute serially.

Each call is a new physical or virtual action. Equal text sent twice receives distinct send
identities. The SDK never retries after a lost response. Transport loss and backend errors report
`outcome_uncertain=True`; inspect retained receipts, history and events before choosing another
action. A backend failure records the failure and marks the run failed even if the scenario
catches its exception. A bot reply can arrive before or after the input method returns.

## Current text profile and remaining work

The independent model preserves Unicode and trims boundary ASCII space/LF. It supports plain
text and disjoint bold, italic, spoiler, strikethrough and single-backtick code delimiters. The
ordinary one-message boundary is 4096 UTF-16 code units of raw input. Invalid Unicode, empty text
and formatting ranges emptied by trimming are rejected.

The following contracts remain unfinished and are rejected before action in both modes:

- Splitting long input, including the pinned hard-split/surrogate concern.
- Fenced or repeated backticks and interacting/nested delimiter combinations.
- Link-like input and text transformed into links; full native URL recognition is not modeled.
- Standalone configured dice emoji, including formatting that turns into dice text.
- Existing styled drafts, rich spans, custom emoji, attachments, replies, scheduling and alternate senders.

These are explicit experimental limits, not claims that Telegram rejects those inputs. The full
composer fidelity target remains open. The pinned English client profile uses its default
Send-by-Enter preference; arbitrary client preference changes are not exposed by this runner.
The [source review](composer-text-references.md) records why these surfaces require further
native observations. Simulation tests cannot establish their rendering or server semantics.

## Example and evidence

Run [the composer example](../../examples/composer/scenario.py) in the
[consumer environment](consumer-runner.md):

```sh
gramlab run examples/composer/run.toml --output artifacts/composer-example
```

With the approved local APK and Android profile configured through the
[capture environment](scenario-captures.md):

```sh
gramlab run examples/composer/android.toml --output artifacts/composer-android-example
```

The example retains the original Start Bot screen, the first formatted exchange and the final
conversation. Complete histories, ordered events, accepted receipts and raw inputs remain in
JSON; the existing HTML report embeds original PNGs. Generated artifacts and provisioning paths
stay ignored. Empty-chat captures use `contains=[]`, verify empty authoritative history and wait
for the native chat title. A nonempty chat still requires expected message text.

[Core tests](../../tests/test_composer_input.py) compare all seven original Android text fixtures,
Unicode properties and length boundaries, exact HTTP results, distinct sends, invalid states,
lost responses after commit and 64 concurrent mixed input actions. A controlled external-renderer
failure exercises the real world/control boundary after commit; it is not an Android UI test.
The separate native harness covers actual stale-draft rejection and interrupted-response recovery.

[Consumer tests](../../tests/test_runner_composer.py) compare complete world metadata, histories,
events and semantic send results across simulation and actual Android, including the original
Start Bot touch and three accessibility Send actions. Original before/after screenshots were
retained. The core gate passes 215 tests at 80.99% coverage; the installed wheel's example also
passes offline. The full Android gate has 21 passes, including this consumer case, and one failure
in the older interrupted-send probe. Its focused rerun passes without a production change, so that
intermittent failure remains open; current diagnostic trials are recorded in the handoff. Original
PNGs were inspected directly. The report serves all three embedded images over local HTTP, but
configured browser navigation fails, leaving browser layout review unverified.
