# Original rich-button input experiment

The opt-in [GPL observer](../../clients/android/experiments/rich-actions/README.md) now has a
passing real-bot input loop on the pinned original Android renderer. A row callback and an inline
callback each receive one ordinary guest tap. The bot answers both and edits the same message
after the second; original rendering and cold restart retain that edit. Public rich-button
targeting, clipboard semantics and a permanent observation interface remain open decisions.

## Evidence boundary

The experiment uses a separate APK containing the normal thirteen-patch source plus one GPL
helper and one installation call. All 43,250 files in the fresh normal export match before that
overlay. Its offline build passes in 2 minutes 8 seconds. Binary inspection finds the helper only
in the experimental APK. Actual paths, fingerprints and generated evidence stay ignored.

The initial native trial exposed a fixture error: buttons were visible in the original PNG, but
their labels were absent from accessibility XML. The fixture now includes an ordinary `Choose:`
anchor beside the inline button. Readiness uses that anchor; input continues to use observed native
rectangles and action identities. The corrected real-bot simulation passes in 1.12 seconds.

The normal APK then reaches the intended missing-observer rejection in 71.43 seconds, after a
successful launch and visible ordinary anchor. It performs no tap and creates no callback. The
first experimental loop passes in 82.28 seconds. Wrong-message activation produces an explicit
unavailable result and leaves World state unchanged. A fresh activation and cold process then
observe the actual row and inline targets. Samples are 315 ms and 597 ms old at the final pre-tap
checks, within the explicit five-second bound. Inspection of all five original PNGs confirms that
the recorded rectangles and tap centers align with the visible controls.

Complete assertions compare the independently authored native rich content, callback message
snapshots, two distinct callback IDs and answers, actual HTTP transcript, twelve ordered World
events, same-message edit and empty pending queue. The retained native trace has exactly two
corresponding callback request/response pairs. Zero accounts, external network denial and guest
filesystem separation pass. No native callback is synthesized by Python.

The first report passes desktop/mobile browser review at 1280×900 and 390×844. All five original
images load, there is no horizontal overflow or external resource request, and both browser
captures were inspected. The expanded lifecycle fixture then passes in 83.83 seconds on the same
experimental APK. A successful app-private directory listing after the first visible launch proves
both activation and output files absent, with unchanged World state. Wrong-message activation
produces fresh explicit unavailability in a different cold process; correct activation starts a
third process. The two final samples are 225 ms and 543 ms old. All six original PNGs were inspected,
including the added wrong-identity phase; their rectangles and tap centers match the visible
controls. The six-image report passes the same desktop/mobile checks with no external resources
or horizontal overflow. Both browser captures were inspected, and the owned preview/tab are closed.

After the shared probe hooks and startup collector merge, the existing normal rich-message and
cleaning native cases also pass (two tests in 169.61 seconds). The combined core gate passes
390 tests in 54.01 seconds at 80.99% coverage. Documented lint, formatting, strict typing and the
offline workflow check pass. These checks remain distinct from the earlier resumed 41-case normal
Android inventory and the explicit-only experiment. Tickets 17 and 19 are resolved for this bounded
callback loop; the broader rich-action inventory remains open.

## Reproduce

Select the separately built experimental APK through `GRAMLAB_RICH_ACTION_EXPERIMENT_APK`, then
run the explicit fixture with the [offline guard](offline-safety.md) and shared guest lock:

```sh
tools/worktree lock android-gate tools/dev android --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest tests/rich_action_input_experiment.py::test_experimental_original_row_and_inline_callback_taps'
```

Its simulation companion is
`tests/rich_action_input_experiment.py::test_simulation_real_bot_answers_two_rich_callbacks`.
The filename intentionally lies outside default pytest discovery. Supplying the normal APK to
the native fixture deliberately tests missing-observer refusal; it cannot supply geometry.

This is a short, top-level LTR fixture. Non-atomic observation/touch, duplicate or stale targets,
RTL/nesting, copy and disabled effects remain unaccepted. No automatic input retry, renderer
modification, exported component or public targeting API is added by the experiment. The normal
APK and ordinary scenario interface retain their separate acceptance evidence.
