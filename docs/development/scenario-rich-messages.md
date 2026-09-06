# Rich messages in public scenarios

The [rich example](../../examples/rich/scenario.py) uses the same public scenario and ordinary
HTTP bot in simulation and headless Android modes. The bot sends a bilingual heading, formatted
paragraph, table and nested quotation through `sendRichMessage`, then edits that message to RTL
through `editMessageText`. Both requests use the [supported structured subset](rich-messages.md)
with automatic entity detection explicitly disabled.

After provisioning the development environment, run simulation inside the documented
[offline guard](offline-safety.md):

```sh
tools/dev default --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/gramlab run examples/rich/run.toml --output artifacts/rich-simulation'
```

For Android, provision the approved rich-message APK and set `GRAMLAB_ANDROID_APK` to its locally
discovered path. Use the shared guest lock:

```sh
tools/worktree lock android-gate tools/dev android --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/gramlab run examples/rich/android.toml --output artifacts/rich-android'
```

Use new output directories for new runs. The runner retains `result.json` and self-contained
`report.html`. Android additionally retains original `captures/initial.png`, `edited.png` and
`restarted.png`, with their accessible UI evidence. The first capture precedes the edit command;
the following captures open the same persona with its cache, exercising cold restart after the
edit. The separate [native integration](android-rich-projection.md) observes the live edit without
an intervening launch and verifies actual serialization; a public capture alone is not that proof.

## Expected content and evidence

`capture_chat(contains=[...])` searches ordinary message text and text fragments inside rich
messages. RichText arrays and wrappers concatenate within one text field, so `Hello GramLab`
can span a plain string and bold wrapper. Different blocks, cells, captions and credits remain
separate: their concatenation cannot create an artificial match. Nested quotation/details blocks,
details summaries, credits, table captions and visible cell text are searchable. Type names,
languages, alignment and other metadata are excluded. Complete structured history remains intact.

These expectations assert semantic content in simulation. Android also requires each expected
string in actual accessible UI text before taking the screenshot. Collapsed or off-screen content
can satisfy semantic membership but cannot bypass the native visibility condition. No text
extraction replaces the Android layout or manufactures pixels. Rich-only messages continue to
carry their full `rich_message`; ordinary internal `text` remains empty.

The worker's public consumer tests cover positive fragments and rejection of absent, metadata-only,
cross-block, cross-cell and other-chat text without overwriting earlier evidence. The independent
[example test](../../tests/test_runner_rich_example.py) compares complete initial and edited history
with a separate fixture, then compares simulation and Android world, history and events. The nine integrated capture tests pass, including the real-bot public example in simulation;
the full core gate passes 272 tests at 81.44% coverage. Native integration of this new public
example is still pending the shared guest gate.

The [capture limits](scenario-captures.md) and baseline [rendering profile](android-effects-profile.md)
remain applicable. Native inline-keyboard targeting for rich messages is not verified. HTML,
Markdown, automatic detection, links, lists, media, custom emoji, rich buttons and streamed drafts
remain open; this example does not establish those contracts.
