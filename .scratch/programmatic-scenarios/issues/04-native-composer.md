# Native composer sends and durable client recovery

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: none (03 resolved)

The coordinator owns the world/bridge, GPL adapter patch, scenario integration, tests and handoff.
Implement the approved semantic request/cursor boundary using the
[pinned composer references](../../../docs/development/android-composer-references.md).
Keep the actual composer, send helper, controller and renderer. No DC/account use or alternate UI.

## Acceptance

- Authenticated text sends commit one message, event and bot update with durable request correlation
  scoped to persona and destination. Retry after lost response returns the original committed result.
- Per-persona message positions are independent of the world journal and survive migration/restart.
  Snapshot, live updates and difference recovery agree with compact send acknowledgments.
- Unsupported request flags fail before mutation. Wrong persona, destination, world, capability,
  invalid payload and inconsistent request reuse retain explicit errors.
- Actual composer input causes the mutation. Repeated equal text is distinct; accepted retries are
  not. Observe positive IDs, final send state, no pending negative duplicate and real bot replies.
- Exercise event/ack order and interrupted commit/ack/storage boundaries, then cold restart.
  Preserve correlation and the client database, with no placeholder sequence values or hidden gaps.
- Consumer simulation and Android input use the same semantic world contract; retain original
  multilingual captures and complete recovery evidence in the existing reports.
- Run focused boundary regressions before implementation, offline build and the applicable full
  core/Android gates. Preserve the license/patch boundary and update supported surfaces honestly.

The world remains the single authority and Android remains a recoverable replica, as approved in
[ADR 0004](../../../docs/adr/0004-semantic-bridge-and-world-persistence.md). This implements its
request correlation and client cursor obligations; it does not widen into an MTProto server.

Progress: [the independent send boundary](../../../docs/development/client-sends.md) has seven
new behavioral tests, 53 focused passing regressions and a full core gate of 186 tests at 82.55%
coverage. The [focused native case](../../../docs/development/android-composer.md) now passes
actual Unicode sends, distinct equal-text actions, stale-draft rejection, compact acknowledgment
and difference serialization, retained client state across restart, and response-loss-after-commit
recovery with one bot reply. Fresh preparation preserves 6,666 upstream UI/resource files.
The full 20-test Android gate passes, predating the new composer-text contract test, which then
passes its seven fixtures separately. The native
bot-history Seen display rule was verified separately from stored read state; the renderer is
unchanged. The [scenario integration](../../../docs/development/scenario-composer.md) now passes
a shared simulation/Android example with Start Bot, three typed sends, four real bot replies and
three original captures. Seven native fixtures agree with the independent bounded text model.
The new core gate passes 215 tests at 80.99% coverage. The broader Android gate finishes with
21 passed and one failure in the older interrupted-send probe, which missed its controlled commit
boundary. The new consumer case passes again; the installed wheel example also passes offline.
A focused native rerun with missed-boundary diagnostics passes without a production change;
the failure remains intermittent and unresolved. The next trial fails before input during activity
startup, with the main thread in preference-file sync. That is a distinct failure; the final bounded
trial passes after toolchain preparation, without a production change or timing workaround.
All three diagnostic trials are terminal: two pass and one fails before input. Both intermittent
failures remain unresolved, with targeted evidence retained for subsequent investigation.
Broader composer transformations
and additional interruption boundaries remain in progress; this ticket is not resolved.

The [acknowledgment-before-storage probe](../../../docs/development/ack-storage-recovery.md) now
passes the actual Android case, using a debugger to hold only the original storage thread at
ID-remap entry. Its frame arguments match the accepted receipt; the retained database has only
one correlated negative row and intermediate `seq=7, pts=8`. Restart recovers the positive row
once, aligns both cursors and allows one real bot reply. A separate real JVM fixture validates
the debugger's suspension/resumption behavior. No APK or production change was required.
The initial native baseline attempt failed in the independent codec process, not at the new
boundary. Its crash trace identifies a local bridge connection timeout, with a secondary error
during Android crash reporting. The full expanded Android gate passes all 24 tests, including
both interruption cases and the standalone JVM helper check. Static/Nix/workflow and privacy/link
checks pass; core code and the APK are unchanged. All handles are terminal. Live gap recovery and
additional partial-write points remain open alongside broader composer semantics and the unresolved
intermittent reliability failures.

The new [live-gap regression](../../../docs/development/live-gap-recovery.md) fails on the prior
APK because disabling native transport also omitted its periodic controller callback. A separate
second-send diagnostic recovers from the unchanged old cursor, isolating the missing callback.
Patch 0009 restores the original callback on the stage queue independently of HTTP polling.
The contained strict offline rebuild passes, and the original single-send case passes in about
70 seconds: native difference positions 2–4, recovery before polling release, no restart, another
successful send, once-only bot replies and exact seven-message storage with seq/pts 7. Four
original captures are retained. Equal-timestamp arrival order follows the pinned original UI;
expanded assertions against the retained XML pass and the report documents that policy.
Fresh preparation matches five Java inputs and preserves all 6,666 UI/resource files. Full
static checks and declared host Nix/workflow checks pass. The expanded Android gate stops with
three passed tests and one failed existing Unicode composer send: its third request returns 503
without a world commit. The cause remains unknown. Patch 0010 adds capability-safe exception-class
traces and rebuilds offline. The focused composer diagnostic completes its sends and recovery,
then fails in the separate codec process with the previously observed local connect timeout.
It does not reproduce or explain the earlier 503. The final focused live-gap run passes again
on the diagnostic APK with the expanded UI assertions in about 93 seconds. All handles are
terminal; the full gate remains unproven. This ticket and the full
product goal remain open. Distinct-timestamp ordering, multi-page gaps, broader input semantics and the
earlier intermittent reliability failures still need evidence.


The [transport follow-up](../../../docs/development/android-transport-reliability.md) now separates
codec verification from composer startup. Repeated isolated codecs reproduce Netsim handshake
stalls and a distinct closed-connection reuse failure. Built-in Virtio Wi-Fi forwarding plus an
explicit bridge close header pass eight independent native codec worlds (72 HTTP requests).
The core wire regression verifies real EOF, complete success/error responses and unchanged world
state after rejections. All 14 focused core tests and 216 full core tests pass at 81.09% coverage.
All 11 focused Android checks pass, including both interruptions, live-gap recovery and guest
isolation. The full 26-test Android gate stops with three passed and one failed: activity launch
reports a timeout before input and UIAutomator creates no hierarchy file. Its startup root cause
remains unproven. Static/Nix checks and the installed wheel's offline simulation example pass.
The APK is unchanged. All handles are terminal; the startup failure is the next diagnostic target.
This checkpoint does not resolve the ticket or the wider product goal.
