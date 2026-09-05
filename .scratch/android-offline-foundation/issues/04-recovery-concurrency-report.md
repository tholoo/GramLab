# Prove recovery, concurrency and diagnosable failures

Type: task
Status: needs-info
Work state: open
Blocked by: 03

Extend the verified round trip with interrupted execution and an HTML report. Keep renderer-free
load and resource-bounded Android concurrency separate.

## Acceptance

- Bot/client restarts recover defined state; concurrent worlds and same-world users remain correct.
- Reproduce duplicate delivery, stale actions and a committed operation whose response is lost.
- Retain seeds/traces and relevant state; one failed run cannot poison a clean rerun.
- Report requests/updates, IDs, consumer logs/state hooks and Android artifacts without secrets.
- Distinguish observed/applied/verified fixes and record decisions with before/after evidence.
- Measure bot, simulator, renderer and injected-delay contributions under a stated workload;
  identify slow operations without claiming production Telegram throughput equivalence.
- Validate the report with synthetic malicious text and credential-shaped fixtures to catch
  unsafe HTML rendering and redaction failures.

## Comments

Consult the user if achieving persistence/replay requires a consequential architecture change.
