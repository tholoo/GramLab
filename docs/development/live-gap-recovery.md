# Native recovery while incoming delivery is held

The original one-send regression passes after restoring the omitted periodic controller callback.
Additional native fixtures now pass distinct-timestamp ordering and a 1,000-message backlog spanning
two difference pages. The APK, controller and renderer are unchanged by those fixture additions.
The expanded Android gate passes all 28 tests; earlier intermittent startup/send failures remain
unresolved. See [transport reliability](android-transport-reliability.md) for their separate evidence.

## Reproduction and cause

The [native probe](../../tests/probes/android_live_gap.py) starts a dedicated client with one
bot message. A contained loopback proxy holds ordinary change polling. A virtual user then sends
one explicitly synthetic message and a real bot replies through the local Bot API. Those two
new messages are absent from the captured Android conversation. An actual composer send commits
position 4 while the client's update cursor is still at position 1.

The initial regression fails: that send completes, but no native difference request appears and
the missing messages do not render. The unchanged APK recovers in a separate diagnostic when a
second actual send acknowledgment arrives after the original gap wait. That request starts at
position 1 and retrieves the complete contiguous prefix through position 5. The diagnostic stops
with an intentional failure after retaining this observation; it is not a passing product test.

The pinned original `MessagesController.processNewDifferenceParams` queues the first pts gap.
Its `updateTimerProc` checks queues after the 1,500 ms wait and requests a difference. The sole
Java caller is `ConnectionsManager.onUpdate`, normally reached from the native transport loop.
GramLab disables that native transport and had omitted its periodic callback. The gap therefore
remained queued until another acknowledgment or incoming event caused another check.

[Patch 0009](../../clients/android/patches/0009-native-controller-timer.patch) schedules the original
callback on the native client's stage queue every second after replica initialization. Scheduling
is independent of the blocking HTTP polling worker. The original controller, storage and renderer
are unchanged. Native transport stays disabled; unsupported requests still return explicit errors.
This restores a runtime obligation of the existing adapter rather than implementing another gap
algorithm in the Python world or changing client cursors.

## Required evidence

The [host test](../../tests/test_android_composer.py) requires the original one-send case to recover:

- Ordinary polling remains held until the original UI shows the missing messages and own send.
- The actual native difference request and response correlate. Its unmodified HTTP response starts
  at position 1 and contains positions 2, 3 and 4, with matching cursor and head.
- No ordinary polling event has been applied before recovery. The process identity stays the same
  throughout the case and the trace contains exactly one client initialization.
- Another actual composer send succeeds. The real bot receives each user message once, replies
  once to each and acknowledges its update queue.
- The final world history and original client database contain exactly seven positive messages,
  no pending correlation, and matching seq/pts cursors at 7.
- Four original screenshots and structured evidence appear in the existing HTML report format.

The pinned client's first difference requests at least 1,000 positions, and the adapter caps it at
1,000. Ordinary polling requests 100 and stays at the initial snapshot cursor 1 while held.
The proxy holds that request, including retries. The second native difference page uses its
intermediate cursor 1001, allowing it to proceed despite also requesting 100 positions. The probe
first verifies that startup has not consumed the first difference. This selects requests without
fabricating holes, modifying responses or editing the replica. It is a controlled fresh-start
fixture, not a general fault scheduler for arbitrary polling/difference states.

Run with the [retained Android shell](environment.md), approved APK and
[outer network guard](runtime-boundary.md):

```sh
.venv/bin/pytest tests/test_android_composer.py -k native_difference
```

## Initial verified focused result

The contained strict offline build completes, and the original focused case passes in about
70 seconds. Its unmodified difference response contains positions 2, 3 and 4; the same process
then sends again and receives the two remaining real bot replies. The retained database has
exactly seven positive messages and `seq=7, pts=7`, with no pending correlation. Four original
captures appear in the report. Fresh preparation applies all nine patches and matches the five
adapter/probe Java inputs; all 6,666 original UI/resource files remain byte-identical. Static
checks pass. The broader Android gate has three passed tests and one failed composer send; the 503 cause
remains under investigation.

Screenshot review also identified the pinned client's equal-date insertion policy. All fixture
messages have the same world timestamp. Original `ChatActivity` line 25800 inserts a newly
arrived message ahead of an existing equal-date entry in its reverse list, regardless of their
positive ID ordering. The displayed order is therefore 1, 4, 2, 3 after recovery, and
1, 4, 2, 3, 5, 6, 7 after the remaining replies. The test records that exact upstream display
behavior separately from correct authoritative/stored ID order. No renderer change or invented
timestamp hides it. The separate clock fixture below verifies ordering across distinct timestamps.

## Distinct timestamps and multi-page recovery

The expanded host test retains the original same-second case and adds two fixtures using the
world's existing `advance_time` operation. Time advances by one minute before the virtual action,
first bot reply, first composer send, second composer send and final bot batch. The final two bot
replies intentionally share a timestamp. There is no post-hoc timestamp rewrite or renderer patch.

The small timed fixture requires world and native message dates at offsets
`[0, 60, 120, 180, 240, 300, 300]` seconds. The original UI displays IDs 1–4 after recovery and 1–7
after the final replies, placing the delayed older messages above the newer acknowledged send.
Both the same-second and distinct-minute cases pass in the focused run.

The multi-page fixture inserts 1,000 explicitly synthetic bot-history messages while polling is
held, then performs the same virtual-user/real-bot/actual-composer loop. The native requests and
unmodified HTTP responses are required to match these pages:

| Request cursor | Limit | Returned positions | Returned cursor | Head |
| --- | --- | --- | --- | --- |
| 1 | 1000 | 2–1001 | 1001 | 1004 |
| 1001 | 100 | 1002–1004 | 1004 | 1004 |

The actual Android case passes in about 70 seconds, including guest startup. Each native request
correlates with its response, no polling event applies before recovery, and the process identity
and single initialization stay unchanged. A later actual send succeeds. The real bot receives
only the three user messages, replies once to each and empties its update queue; synthetic backlog
entries are not presented as bot-process output.

The final world and copied native SQLite database contain all 1,007 positive messages, matching
per-message timestamps and seq/pts 1007, with no pending correlation. The visible UI matches the
chronological suffix of that complete history; a viewport screenshot is not used as proof for the
1,000 off-screen entries. Four original captures, full structured observations and the controlled
HTTP transcript appear in the existing report. Complete strict typing and lint/format pass.
The core, APK, source patches and Nix inputs are unchanged; the preceding core/package/Nix checks
remain applicable. The full expanded Android gate passes all 28 tests in about 21 minutes,
including all three live-gap fixtures and the original interruption and consumer cases. Seven
report regressions pass; local links and public-tree privacy checks pass. All handles are terminal.

## Limits

The controlled hold can cause expected native read timeouts and abandoned proxy responses. Those
observations are separate from the earlier intermittent local connection and startup failures.
These cases do not establish arbitrary-length gap schedules, concurrent personas, all partial
writes or normal input latency. The restored callback uses real scheduling, matching the existing native
gap wait; fully deterministic Android timing remains unproven. Generated artifacts and local
runtime details stay ignored. No real account, DC connection or external fallback is used.

The first broader gate stops after three passing tests when the existing Unicode composer case's
third send returns 503 without a world commit. That is not the live-gap failure above. The generic
error mapping did not retain its root exception, so no timer regression or connection cause is
claimed. [Patch 0010](../../clients/android/patches/0010-bridge-failure-classification.patch) adds an
exception-class trace correlated with the existing request token, omitting exception messages,
response bodies and capabilities. The diagnostic build passes with strict offline verification. Its focused composer rerun completes
the sends and interrupted-response recovery without reproducing the 503, then fails in the
separate codec process. The retained crash identifies a local bridge connect timeout after
3,000 ms during its final snapshot request. That failure mode predates the timer correction;
it does not explain the earlier 503. A separate focused live-gap run passes on the final
diagnostic build in about 93 seconds, including the expanded original UI assertions. All trial
handles are terminal. The full Android gate remains unproven.
