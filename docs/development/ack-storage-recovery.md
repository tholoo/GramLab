# Acknowledgment before client storage

The external debugger helper passes its real JVM contract, and the actual Android interruption
case passes. The original storage method receives the acknowledged positive ID while its retained
database still has only the correlated negative pending row. Cold restart recovers once and a real
bot replies once. The application, renderer and APK are unchanged from the native composer checkpoint.

## Exact boundary

The pinned [send helper](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L8325)
publishes the acknowledged message identity before queuing its storage remap. The queued work
calls [updateMessageStateAndId](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesStorage.java#L14140)
before persisting the acknowledged message. An external debugger can suspend that method at
entry on `storageQueue_0`, after the response has been processed and before the remap executes.

[The test helper](../../tests/probes/jdwp.py) implements a bounded subset of the published
[JDWP packet protocol](https://docs.oracle.com/en/java/javase/17/docs/specs/jdwp/jdwp-spec.html)
and [breakpoint/stack-frame commands](https://docs.oracle.com/en/java/javase/17/docs/specs/jdwp/jdwp-protocol.html).
It resolves one already-loaded class and exact method descriptor, installs a one-occurrence
breakpoint at method entry, and suspends only the event thread. It reads primitive arguments
from the suspended frame; it never loads classes, invokes methods, changes fields or replaces
bytecode. Invalid or ambiguous targets and unavailable debug information fail explicitly.

The actual Android probe attaches through an ephemeral ADB JDWP forward to the dedicated
debuggable client process. The forward and debugger remain inside the existing offline network
namespace. Cleanup kills that client before disconnecting the debugger, so detaching cannot
release the held write before the database is retained. No new endpoint is exposed by the
consumer runner, and normal runs do not attach a debugger.

## Observable contract

The [real JVM fixture](../../tests/test_jdwp.py) first proves the mechanism independently of
Android: storage has not written its file while the breakpoint is held, the main thread still
answers a request, and resuming the event thread writes the exact value. A missing method is
rejected before the valid target is installed. This is tool validation, not Android fidelity.

The [native test](../../tests/test_android_composer.py) has separate pre-acknowledgment and
pre-storage cases. The latter verifies:

- Actual composer input commits one world message and scoped receipt.
- The paused original method receives that receipt's random ID, peer and positive message ID,
  with `useQueue=false` on the account-zero storage thread.
- After stopping the client, its database contains exactly the prior messages plus one correlated
  negative pending row. The acknowledged positive row has not been stored yet.
- Cold restart retains the same world and client database, remaps the pending row once, restores
  exact final cursors, and leaves no negative duplicate.
- A real local bot sees one update and replies once; complete history and original captures remain
  in the existing report. The report identifies which interruption boundary was exercised.

The independent TL serialization/rejection probe now runs in its own
[codec transport test](android-transport-reliability.md), separately from both interruption cases. Both cases retain the normal
Unicode, repeated-send, stale-draft and cold-restart checks.

The focused JVM case passes in about two seconds; the focused Android case passes in about
145 seconds. At the held boundary, the actual stored cursors are `seq=7, pts=8`: acknowledgment
processing has advanced pts while the message ID remap is still pending. Restart restores both
to 8, then the bot reply advances both to 9. The complete retained message rows and random-ID
correlation establish that the earlier cursor advance did not lose the pending send. The report
contains six original captures, including the acknowledged UI before storage. The expanded
Android gate passes all 24 tests, including the standalone JVM check and both interruption cases.
Strict typing, lint/format, Nix/workflow checks, local links and public-tree privacy checks pass.
Core code is unchanged; the earlier 215-test core gate remains the applicable core evidence.

Run with the [retained Android shell](environment.md), approved APK and
[outer network guard](runtime-boundary.md):

```sh
.venv/bin/pytest tests/test_android_composer.py -k before_storage
```

The JVM-only helper check is `pytest tests/test_jdwp.py`; it uses the pinned JDK from the Android
toolchain and is included in that gate without claiming to launch an emulator.

## Limits

Debugger suspension deliberately changes scheduling. This test cannot establish normal input
latency, all possible partial database writes, live gap recovery or uninstrumented reliability.
The earlier missed-commit and startup failures remain unresolved. The initial native baseline
attempt ended in the separate codec process being killed, so it is not a valid failure at the
new storage boundary. Its retained crash trace identifies a local bridge connection timeout;
the secondary Binder crash-reporting error does not explain that timeout. The passing expanded
gate does not establish a fix for these intermittent failures. Local traces, SQLite copies and
trial handles stay ignored. Browser layout review remains unverified; original PNGs were inspected.
