# Scenario-driven inline-button input

The experimental consumer SDK can select a bot message's inline callback button in either
simulation-only or headless Android mode. Both paths create the same world callback and let a
real bot answer it and edit its message. Android input goes through the actual upstream button
view and existing client callback adapter. No APK or client-derived source change is required.

## Consumer contract

```python
interaction = lab.tap_inline_button(chat_id=chat["id"], message_id=message["id"], row=1, column=0)
callback = interaction["callback"]
```

Indices start at zero and refer to the current message's inline keyboard. The chat identifies
its virtual user; input cannot impersonate a different user in that chat. The message must come
from the chat bot and contain the requested cell. Invalid identifiers, Boolean/negative indices,
out-of-range cells and removed keyboards fail before input. At most 64 input records are retained
per run; further requests fail before executing.

The result contains `chat_id`, `message_id`, `row`, `column`, `native` and `callback`. The callback
retains the world representation, including its message, persona, callback data and current answer.
Use `get_callback` to wait for the answer; the bot may answer before or after the input call returns.
Simulation has `native=False`. Android has `native=True` only after actual input produces a matching
callback, and includes the observed UI, button attributes, coordinates and elapsed duration in an
`android` member. That duration includes client launch/observation and is not gesture-only latency.

Each call is a new action. The client never retries it automatically. The per-call socket timeout
defaults to 180 seconds; the manifest bounds the whole run. Transport loss, malformed success
responses and native backend failures have `outcome_uncertain=True`. Inspect world events before
deciding whether to perform another action. Backend failure marks the run failed even when the
scenario catches its exception. Reports retain interaction records and any preceding captures.

## Actual client targeting

The trusted controller opens the requested chat in the dedicated guest, restoring its synthetic
persona through the existing bridge. It finds the accessible message by its text and complete
keyboard, then selects the matching child button by row/column. Repeated button labels within
one keyboard are supported. Duplicate message text within the chat is currently rejected because
accessibility does not expose the semantic message ID. Missing, ambiguous, disabled, partially
visible or off-screen targets fail explicitly. There is no automatic scrolling or coordinate API.

Supported rich messages use their ordered readable fragments and the complete keyboard. The
matcher excludes the pinned English host's receipt paragraph; text styling and RTL metadata do
not establish identity. Whole-history checks reject indistinguishable rich messages even when
one is off-screen. This deliberately conservative matching can also reject distinct messages
when all fragments of one occur in the other. Closed-details descendants, textless content and
unverified host locales cannot establish a target. Ordinary messages retain exact full-text
equality for ambiguity checks, so a separate message equal to only the first line of a multiline
target does not block the complete target.

The current implementation uses the pinned 320×640 display at 160 dpi and verifies button bounds
inside that profile's chat viewport. It checks for a known message change immediately before input,
then taps once and waits up to 15 seconds for a matching callback event. It does not create a
synthetic callback as a fallback in Android mode. Changes after validation can still race the tap;
unexpected callbacks fail visibly and remain in the event trace. Sequence other callback actors
when validating a particular native action: event matching is not a causal proof under concurrent
same-persona input. Captures and native actions share one renderer lock within a run.

Opening the chat currently cold-starts the client. Capturing the bot edit afterward also verifies
that edit through restored client state; this example does not establish live-update latency.
The dedicated harness separately verifies live callback/edit rendering and client recovery in
[the original interaction loop](android-callbacks.md). [Start Bot and composer text](scenario-composer.md)
now have separate SDK support. Scrolling, other non-callback
buttons, interactive mode and broader lifecycle/fault controls remain unfinished.

## Runnable example and evidence

The [inline example](../../examples/inline/scenario.py) sends mixed Persian/English text through a
real bot, captures its keyboard, chooses the second-row “Confirm” button and captures the bot edit.
The first row contains another “Confirm” with different callback data, so selecting by label alone
would produce the wrong result. Use the [consumer environment](consumer-runner.md) for simulation:

```sh
gramlab run examples/inline/run.toml --output artifacts/inline-example
```

With the approved APK and Android runtime profile provisioned as described in
[scenario captures](scenario-captures.md), select the headless manifest:

```sh
gramlab run examples/inline/android.toml --output artifacts/inline-android-example
```

Normal execution remains contained and offline. Generated PNG/XML, reports and local provisioning
paths stay ignored. HTML includes original explicit captures and a separate interaction section;
JSON retains full evidence.

[Core tests](../../tests/test_runner_interactions.py) exercise both public runner entry points,
invalid/removed targets, exact bot edits and response loss after the callback actually commits.
Four concurrent actors verify distinct callbacks and enforcement of the shared per-run limit.
[Android tests](../../tests/test_runner_android.py) compare final worlds and histories across modes,
verify exactly one callback from the repeated-label keyboard, and reject ambiguous native targets
without a second callback while preserving earlier screenshots in the failed report.

The [rich inline example](../../examples/rich_inline/README.md) exercises the same repeated-label
selection on a heading, table and styled bilingual paragraph, then captures the real bot's RTL
rich edit. Its [public runner tests](../../tests/test_runner_rich_buttons.py) compare complete
simulation/Android histories, callback content and normalized events; reject an off-screen
formatting-only duplicate before another tap; and preserve ordinary multiline targeting. The
worker's focused native cases pass with the unchanged APK. Combined integration checks are
recorded in the handoff rather than inferred from these focused results.

The final milestone gate passes 147 core tests at 81.86% coverage and all 18 Android tests. Static
checks, Nix/workflow validation, offline distributions and privacy/local links pass. Desktop/mobile
report inspection confirms both original 320×640 images load without external resources or
horizontal overflow. The approved client APK remains unchanged.
