# Preserve completed emoji fault cases when a later case fails

Type: task
Status: ready-for-agent
Work state: implemented on `task/custom-emoji-fault-checkpoints`; coordinator review pending
Blocked by: coordinator integration and native execution

Own this ticket and the test-only `tests/probes/android_custom_emoji_faults.py`; focused tests
may be added to `tests/test_custom_emoji_fault_server.py` only when they exercise meaningful
artifact behavior. Coordinator owns native execution, acceptance assertions and shared docs.
Do not change the Android adapter, scenarios, fault scheduling, expected outcomes or timeouts.

The first native fault run completed the three document-case functions but failed while waiting
for the shared thumbnail cache. The document result objects were kept only in memory until all
four cases completed, so a later failure lost the complete earlier HTTP/peer result evidence.
Preserve the original failed run. No completed subcase may be labeled passing without its full
independent acceptance assertions.

Durably checkpoint each completed document-case result before starting the next case, retaining
its exact existing structured result and binding it to its case name. Use dedicated bounded JSON
files in the run directory, no machine paths in tracked metadata and no overwriting prior evidence.
Keep final successful result shape and existing acceptance unchanged. Record a bounded failure
checkpoint identifying the phase and exception class when a later case fails. Preserve the
shared peer's existing request/asset/hold journals and latest available native trace/cache/logcat
on failure when they can be obtained within the existing run deadline; do not add guest calls on
the normal critical path or change the failed behavior into recovery/success.

Use the existing redaction and dedicated-run boundaries. Do not log tokens, arbitrary exception
messages or new unbounded output. This is a small diagnostic improvement, not a general recovery
framework. Validate syntax/static checks and the relevant existing focused tests; avoid tests
that merely mirror serialization. No guest/build/full gate assigned. Return a clean frozen branch,
exact evidence and any remaining gaps in failure artifact retention.

## Implemented checkpoint boundary

Each fully returned document case is now written before the next case starts to a dedicated,
bounded JSON checkpoint. The record binds the case name to the unchanged result object. Publication
uses a flushed temporary file, a no-replace hard link and a directory sync; an existing checkpoint
is never overwritten and temporary files are removed after a collision or publication failure.
All case capabilities are rejected from checkpoint bytes.

The outer failure record contains only the active phase, exception class, already checkpointed
document-case names and available shared-case evidence. During a shared-case failure, the probe
snapshots the existing peer document/asset journals and hold state before context cleanup. It also
records host monotonic observations for partial response, release and finished boundaries. An
eight-second failure-only budget attempts the private trace, current selected cache inventory and
the existing 2,000-line logcat capture; failures retain exception classes without messages. The
normal successful path has no additional guest command and its returned result shape is unchanged.
Every retained text artifact is checked against every case capability, including earlier document
cases that may appear in accumulated logcat. Each failure-only guest call obtains its remaining
positive timeout immediately before invocation; after the shared deadline, later diagnostic stages
record `TimeoutError` as unavailable without calling the guest.

Focused evidence is retained in `artifacts/custom-emoji-fault-checkpoints.xml`. The real loopback
server suite passes seven tests under an isolated namespace. Android collection finds all three
existing cases. Ruff, format and strict mypy with the repository's separate probe/test package-root
convention pass. No guest, APK build or full gate ran; coordinator native execution remains required.
