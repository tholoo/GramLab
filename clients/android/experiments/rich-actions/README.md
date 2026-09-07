# Original rich-button geometry experiment

Unverified experiment preparation for [ticket 17](../../../../.scratch/rich-messages/issues/17-rich-button-geometry-experiment.md).
This directory is GPL-2.0-or-later, using the applicable [license text](../../patches/COPYING).
It refers to original client objects and belongs outside the MIT simulator. It is intentionally
outside the normal patch series and is not a public geometry or input interface.

After preparing a separate pinned source export with the normal patch series, copy
`RichActionGeometryProbe.java` into `TMessagesProj/src/main/java/org/telegram/gramlab/` in that export
and apply `install.patch` there with `patch -p1`. Build offline using the existing documented
Android toolchain, retaining separate normal and experimental APK fingerprints. Never modify the
acquired upstream checkout. No original renderer or accessibility file is changed by this overlay.

In the dedicated guest only, an app-private `files/gramlab/rich-action-geometry.json` opts in before
launch. It contains exactly `schema` (1), a synthetic `nonce`, `world_id`, `user_id`, `peer_id` and
`message_id`. The last two identify the native bot dialog and actual bot message. Binding must match
the loaded snapshot. An absent file installs nothing. Malformed opt-in fails experimental startup.
No endpoint, exported component, external networking or action dispatcher is added.

`rich-action-geometry-result.json` is written atomically beneath the same app-private directory.
It contains nonce, generation, guest uptime, process/message identity and either an explicit
unavailable result or observed rectangles with constituent coordinate offsets and native action
content. The probe listens for draw traversal, then posts observation onto the UI thread after
the traversal; disk writes use a separate executor. Ordinary guest input remains the only input
mechanism. This file is evidence for a bounded experiment, never an authorization token or a
promise of atomic freshness between observation and touch.

The first fixture is a short LTR message with a top-level callback row and a paragraph containing
one inline callback. The observer explicitly rejects unsupported block/transform states and expects
two targets. Real callback/answer/edit, wrong-identity rejection, PNG inspection and cold restart
remain required before claiming the coordinate mapping works. RTL/nesting, other actions and a
permanent targeting contract remain future work; no fallback synthesizes a callback.


A consuming experiment must match nonce, process and message identity, require a generation newer
than its preceding lifecycle/edit boundary, and compare sample uptime against current guest uptime
with a bounded age before each tap. Failed writes can leave the last successful file; an old file
is not evidence of a usable target. Verify expected native action bytes and current world content
again before input. These checks narrow a race window; they do not make observation and touch
atomic. Retain mismatches and never retry input automatically.
