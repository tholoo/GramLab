# Rich inline callbacks

This public example sends an actual HTTP bot a bilingual message. The bot replies with a heading,
table and styled paragraph plus a repeated-label callback keyboard. The scenario captures the
original message, selects row 1/column 0, verifies the callback, and captures the bot's RTL rich
edit. The bot checks that the complete callback message equals its original Bot API reply.

After [provisioning](../../docs/development/environment.md), run in the
[offline guard](../../docs/development/offline-safety.md):

```sh
tools/dev default --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/gramlab run examples/rich_inline/run.toml --output artifacts/rich-inline'
```

For Android, provision the approved APK and runtime, set `GRAMLAB_ANDROID_APK` to its local path,
and use the shared guest lock with a fresh output directory:

```sh
tools/worktree lock android-gate tools/dev android --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/gramlab run examples/rich_inline/android.toml --output artifacts/rich-inline-android'
```

Both modes retain structured history and callback evidence in `result.json` and `report.html`.
Android adds original before/after PNGs. Input uses the actual accessible button, its complete
keyboard and the rich message's ordered readable content. It fails if another world message can
match that native identity, including an off-screen duplicate with different text formatting.
It never creates a synthetic callback in Android mode or retries a tap automatically.

This observation contract uses the pinned English Android host and its existing display profile.
Other UI locales, changed receipt metadata, textless rich content and content that cannot be
observed fail explicitly. Details descendants are only identity evidence when initially open;
formatting, RTL, IDs and dates cannot distinguish equal readable content. Conservative content
matching can also reject a message whose fragments all appear in another richer message.
Scrolling and interactive details expansion remain unimplemented. The richer layout is preserved;
text extraction is only used to verify native input identity, never to render a replacement.
