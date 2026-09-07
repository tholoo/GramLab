# Rich lists and callbacks

This example sends a concise rich message whose readable identity exists only inside list items.
Its initial ordered list uses lowercase letters, uppercase letters and lowercase Roman numerals,
with checked and unchecked nested bullets, an empty item, Persian/English text and a wrapping line.
Selecting row 1/column 0 of the repeated-label keyboard makes the real HTTP bot
verify the complete callback message and replace it with an RTL unordered list containing uppercase
Roman and decimal items.

The scenario captures the initial message, then captures the callback edit twice through the same
public API. Every capture force-stops and cold-launches the client, so the post-edit captures are
named `after-edit` and `cold-reopen`; the separate native integration probe verifies the actual live
edit. After provisioning, run its simulation inside the
[offline guard](../../docs/development/offline-safety.md):

```sh
tools/dev default --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/gramlab run examples/rich_lists/run.toml --output artifacts/rich-lists'
```

For Android, provision the approved list-capable APK and runtime, set `GRAMLAB_ANDROID_APK`, and
serialize guest use with the shared lock:

```sh
tools/worktree lock android-gate tools/dev android --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/gramlab run examples/rich_lists/android.toml --output artifacts/rich-lists-android'
```

Both modes retain complete canonical history, callback events and three cold-launch captures in
`result.json` and `report.html`; Android adds original PNG and UIAutomator evidence. Input fixtures
never contain the output-only `label` field. Native selection uses ordered readable list descendants
and rejects another message with the same readable content even when list labels, values, checkbox
state, empty items or collapsed details differ. The example does not make bot-owned checkboxes
interactive.

The pinned native renderer has been observed drawing an ordered marker beneath an ordered item's
checkbox. The coordinator tracks that rendering quirk without normalizing or fixing it. This scene
keeps its checkboxes on nested unordered items so the `a`, `A`, `i`, `I` and `1` label samples stay
legible.
