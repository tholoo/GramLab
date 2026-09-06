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

2026-09-06 report follow-up started from the verified callback/formatting/recovery scenarios while
the broader foundation dependencies remain open. Implement self-contained HTML evidence with
explicit outcomes, profile/seed/run identity, structured exchanges/history, findings and actual
Android screenshots. Test the generated report boundary with malicious text and credential-shaped
fixtures as required above. Keep selected assets and report output local/ignored; this does not
authorize publication or close concurrency, fault-injection and performance acceptance.

2026-09-06: [Local HTML reports](../../../docs/development/reports.md) now retain the verified
recovery scenario's complete semantic state and original Android screenshots. Seven report
boundary tests cover malicious HTML, credential redaction, PNG integrity/limits and exclusive
publication including concurrent writers. The core gate passes 73 tests at 91.47% coverage; the
focused real Android recovery case passes. Desktop/mobile browser inspection verifies actual
captures and inert text. The report includes app-launch measurements only. Automatic failure
collection, consumer state/log hooks, replay, workload concurrency and separated latency
diagnosis remain open; this ticket is not complete.
