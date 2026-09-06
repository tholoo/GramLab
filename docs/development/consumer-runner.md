# Experimental consumer runner

`gramlab run` executes a declared Python scenario and real local bots in the existing offline
runtime. It prepares selected files without importing consumer code, then starts trusted world
services and separate private scenario/bot components. The scenario uses the
[Python SDK](scenario-sdk.md); bots use the local HTTP Bot API. [Scenario captures](scenario-captures.md)
add original screenshots in headless Android mode. This interface remains experimental.

## Run the example

Provision the [development environment](environment.md) first. From the repository:

```sh
nix develop
uv sync --locked --offline
mkdir -p artifacts
uv run --locked --offline gramlab run examples/echo/run.toml --output artifacts/echo-demo
```

The offline sync requires dependencies already provisioned; first-time acquisition is a separate
setup step. The runner itself never installs dependencies. `python -m gramlab run` is an equivalent
entry point once the package is installed. The command uses `GRAMLAB_RUNTIME_PROFILE` supplied by
the Nix shell; `--profile` can select another **trusted, already provisioned** runtime profile.
Runtime profiles are not consumer manifests and must not be accepted from untrusted projects.

The [example scenario](../../examples/echo/scenario.py) checks two complete conversations with an
[ordinary HTTP echo bot](../../examples/echo/bot.py), including mixed Persian/English and emoji.
Open the resulting `report.html` locally. No Telegram credentials or Android installation are
needed for this simulation-only run. The command performs its own namespace containment; the
development test suite also uses the [outer network guard](runtime-boundary.md).

The output directory must be new and its parent must exist without symlinks. Existing files,
directories and symlinks are refused. Each run gets a fresh private directory, world identity,
network namespace, loopback endpoints and credentials. Simultaneous invocations are supported.

## Manifest and inputs

The [example manifest](../../examples/echo/run.toml) declares:

```toml
schema = 1
mode = "simulation-only"
seed = 7
now = 1700000000
timeout = 15

[scenario]
entry = "scenario.py"
files = ["scenario.py", "helpers.py", "fixtures/input.json"]

[bots.echo]
entry = "bot.py"
files = ["bot.py"]
```

Every listed file must exist; the additional helper/data names above illustrate explicit inputs.
Paths are relative to the manifest directory and retain their layout inside the component's
`/work`. Nested entry files are supported. Symlinks, directories, special files, absolute paths,
parent traversal, duplicate paths, unknown fields and labels that collide after credential
redaction are rejected before output creation.
Ambient project files, `.env` files and host environment variables are not copied automatically.
The scenario's root `gramlab` package is reserved for the supplied SDK.

Declare pure Python dependencies and data as individual `files`, or use dependencies already
provided by the trusted runtime closure. `/work` is on the component's Python import path.
There is no requirements resolver, wheel installer, arbitrary command language or framework
adapter yet. Native dependencies need a compatible provisioned closure. Consumer code is never
executed on the host or inside trusted orchestration as a discovery or installation step.

`seed` and `now` are required nonnegative signed 64-bit integers. `now` initializes the synthetic
world clock; wall-clock polling does not advance it. `timeout` defaults to 30 seconds and accepts
positive finite seconds up to one day. It bounds component startup/execution inside the supervisor;
the outer runtime allows another 15 seconds for cleanup and shutdown. Input staging and host-side
report serialization are outside that execution timeout.

Limits are 64 bots, 512 selected files, 32 MiB per file, 128 MiB total input and 64 KiB of TOML.
Repeated files copied to different components count separately. Bot aliases use lowercase letters,
digits, underscores and hyphens, start with a letter, and have at most 64 characters.

## Process contract

The runner creates each manifest bot identity before launching consumer processes.
`Scenario.bots()` returns the alias-to-world-ID mapping, for example `{"echo": 1}`. Creating
another bot identity through `create_user(is_bot=True)` does not launch a process.

Each bot receives only `GRAMLAB_BOT_API` and `GRAMLAB_BOT_TOKEN` for its local API connection.
The scenario receives its separate control endpoint, capability and world identity. Each component
has private files and PID/mount namespaces. The supervisor owns the world database and services;
consumer code cannot read their files through `/work` or `/proc`. Provisioned profile environment
and the explicit component variables are the only supplied environment settings.

Bots start before the scenario. Updates remain queued while a bot initializes. A nonzero bot or
scenario exit fails the run. A zero-exit bot is allowed, including one-shot consumers. Once the
scenario exits successfully, still-running bots and all component descendants are terminated and
waited for. Expected bot cleanup does not turn a successful scenario into a failure. A passing run
means the scenario's own checks succeeded and no process failure was observed before cleanup.
It does not independently establish Telegram conformance or correctness of an empty scenario.

Stdout/stderr are drained while components run. Each stream is limited to 1 MiB, with a 2 MiB
aggregate run limit; exceeding either fails the run and stops its components. Process evidence
includes exit codes, whether the runner stopped the process, and whether each stream reached EOF
before cleanup. Logs stopped early are explicitly incomplete. Consumer-created files remain in
their private run directories; filesystem, memory and process quotas are not implemented yet.

## Results and limitations

Exit codes are `0` for passed, `1` for an executed failed/incomplete run, and `2` for rejected
configuration or preparation errors. Invalid input does not create an output directory. Later
setup/storage errors can leave a partial output directory; use a fresh destination for a retry.

After normal execution, scenario/bot failure, timeout or unavailable runtime startup, the runner
retains `result.json` and `report.html`, with world state/history/events when world creation
succeeded. Process logs are redacted before the supervisor stores `observation.json`; the final
JSON and HTML also receive credential redaction. Full semantic evidence remains in `result.json`;
HTML sections over 128 KiB show a labeled 16 KiB preview. The report records source hashes, the
runtime profile fingerprint and the immutable Python executable. `profile.json`, `run-input.json`,
the copied sources, private component files and the SQLite world remain local for diagnosis.

Keep run directories ignored. Arbitrary consumer-created files are not automatically sanitized
exports; review them before sharing. Neither the JSON nor the report claims that arbitrary secret
encodings or secrets supplied as ordinary prose can always be detected.

`simulation-only` and [headless Android captures](scenario-captures.md) are connected to this
command. `interactive-android` fails explicitly during preparation. [SDK inline-button input](scenario-input.md) is supported; composer input,
restarts/faults, expanded dependency packaging and workload diagnostics remain active work.
Overall elapsed time covers trusted execution and cleanup; Android metadata separately records
guest boot duration. Neither is an individual Bot API latency measurement.

## Verification

[Runner tests](../../tests/test_runner.py) invoke the actual CLI inside the outer network guard.
They verify the complete private scenario/real-bot exchange, nested entries and selected data,
input rejection, separate concurrent worlds, environment clearing, redacted failure state, bot
failure, output bounds, runtime unavailability and timeout cleanup of a detached descendant.
A large-world case preserves complete JSON evidence while keeping HTML bounded. The
[control tests](../../tests/test_world_control.py) verify scoped, read-only named bot identities.
The documented two-conversation example also runs through the installed console entry point.

The inline-input milestone passes 147 core tests at 81.86% measured statement coverage and all 18
Android tests; lint, formatting, strict typing, Nix/workflow checks and offline wheel/source
builds pass. Selected Python API tests explicitly trace actual contained supervisor execution
using the [test-only fixture](../../tests/conftest.py). CLI/guest behavior checks do not imply
additional measured coverage. [Capture evidence](scenario-captures.md) includes semantic parity,
two successive client personas, failure capture retention and Android startup timeout.
