# Preserve completed emoji fault cases when a later case fails

Type: task
Status: ready-for-agent
Work state: open
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
