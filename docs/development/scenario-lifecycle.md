# Consumer bot recovery and fault injection

The experimental scenario SDK can observe, hard-stop and replace a configured bot process. This
works in simulation-only and headless Android modes through the same trusted supervisor. The bot
keeps its world identity, local API capability and private files; the replacement gets a fresh
component process, mount and PID namespace. No consumer code moves into trusted orchestration.

```python
current = lab.bot_status("recovery")
stopped = lab.stop_bot("recovery", generation=current["generation"])
replacement = lab.start_bot("recovery", generation=stopped["generation"])
```

## Process generations

The first process is generation 1. Status results contain `name`, `generation`, `state` and
`exit_code`. State is `running` while the supervised process is alive, `stopped` after a requested
stop, and `exited` after an unrequested exit. A running process has `exit_code=None`. This reports
process state, not application readiness; scenarios must observe their own bot's readiness signal.

Both mutations require an expected generation. Unknown aliases, nonpositive/Boolean generation
values, stale generations, stopping an already terminal process and starting an already running
bot fail without the requested mutation. Two concurrent stops cannot both stop the same generation.
Starting a successor increments its generation, so a delayed stop for the old generation cannot
kill the replacement. At most eight generations per bot are supported in one run.

`stop_bot` requests SIGKILL, drains the old process's streams and completes the existing pidfd-based
namespace cleanup before returning. Detached descendants belong to that namespace and are stopped
too. The returned exit code is the observed result; an exit can race the stop request. This is a
hard-stop fault, not a graceful shutdown, host reboot or power-loss simulation.

`start_bot` starts a successor only after the preceding process and its streams have terminated.
A normally exited zero-status bot can also be replaced. Unexpected nonzero exits retain the
runner's existing run-failure behavior; this interface does not add automatic restart policies.
A declared scenario process cannot be targeted through these bot-only methods.

## Ownership and uncertainty

The HTTP handler queues lifecycle requests to the persistent supervisor thread. That thread owns
component creation, stream collection and cleanup, avoiding the lifetime of a transient request
handler becoming the lifetime of a bot. At most 64 requests may wait in this queue. Shutdown rejects
pending requests and closes every owned component. Status reads share this ordering with mutations.

Status uses the scenario client's normal socket timeout. Stop/start use a 30-second socket timeout;
the manifest deadline still bounds the run. The SDK never retries lifecycle commands automatically.
Transport loss after a stop/start can leave `outcome_uncertain=True`: inspect `bot_status` and the
recorded generation before deciding on another command. Generation checks prevent an old request
from targeting a newer process; they do not make the transport exactly-once. Read-only status
failures have no uncertain mutation. Known validation failures return `invalid_request` without
claiming the requested action happened. Cleanup/startup failures fail the run and retain their
lifecycle failure record even if the consumer handles its SDK exception.

## Persistent state and evidence

A replacement uses the same declared entry path, selected runtime profile and private bot directory.
It does not recopy the host project, reset the world, clear files or reinstall dependencies. Files
are preserved as the stopped process left them, including partial writes; applications own their
state recovery. Bot-writable source files are also preserved, so preparation hashes describe the
original inputs rather than proving the bot never modified its own private code.

Reports keep one process record per generation: `bot:alias` for the first and `bot:alias#2` onward
for successors. Records include generation, captured streams, observed exit status and separate
`stopped_by_scenario`/`stopped_by_runner` flags. The 1 MiB stream limit applies to each generation's
stream; the 2 MiB aggregate limit includes all generations and the scenario. Restarting cannot
reset that aggregate budget. Stream-completeness flags distinguish drained streams from cleanup
that stopped observation early.

`result.json` and HTML retain an ordered `lifecycle` section for accepted mutations and backend
failures. Status reads and rejected mutations are not added to that section. World events remain
semantic message/callback events; process actions do not advance the virtual clock. Existing
[offline containment](offline-safety.md), redaction and ignored-artifact rules apply throughout.

## Recovery example

The [independent bot](../../examples/recovery/bot.py) journals a callback before acknowledging it,
signals receipt through a message, and deliberately waits. The
[consumer scenario](../../examples/recovery/scenario.py) taps its keyboard, observes that receipt,
stops generation 1 and starts generation 2. The replacement verifies that the pending callback
matches the journal, edits the original message and answers the same callback. The scenario never
repeats the tap. Its explicit stop point follows the journal write; this does not prove recovery
from arbitrary interruption of that write.

```sh
gramlab run examples/recovery/run.toml --output artifacts/recovery-example
```

With the approved Android inputs provisioned as described in [scenario captures](scenario-captures.md),
use `examples/recovery/android.toml` to run the same scenario with actual client input and original
before/after captures. The APK and client-derived adapter are unchanged.

[Lifecycle tests](../../tests/test_runner_lifecycle.py) invoke both public runner entry points and
verify full recovered history, preserved private state and per-generation logs. A detached child
holds an inherited file lock until cleanup; the replacement must acquire it. Concurrent stops,
stale requests and log-budget enforcement across generations are checked through real processes.
[Android tests](../../tests/test_runner_android.py) compare complete final worlds, histories and
lifecycle results, with exactly one native callback and two original screenshots.

Graceful signals, automatic crash policies, client restart controls, timed fault schedules,
network/storage faults and deterministic performance diagnostics remain separate work.

The milestone passes 151 core tests at 81.88% measured coverage and all 19 Android tests. Static,
Nix/workflow, offline distribution and privacy/local-link checks pass. Desktop/mobile report
inspection confirms two original 320×640 captures and lifecycle evidence without external resources
or horizontal overflow. The approved APK fingerprint is unchanged.
