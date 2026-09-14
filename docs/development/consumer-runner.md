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
When a bot needs dependencies outside GramLab's profile, bind its declared alias to a separately
provisioned profile:

```sh
gramlab run run.toml --output artifacts/run \
  --bot-profile my_bot=/trusted/profiles/my-bot-runtime.json
```

Repeat `--bot-profile ALIAS=PROFILE` for bots with different runtimes. Python callers pass the
equivalent `bot_profiles={"my_bot": RuntimeProfile.load(path)}` mapping to `runner.run`. Unknown
aliases and repeated CLI bindings fail before output creation. These paths are trusted provisioning
arguments rather than manifest fields, so a consumer project cannot select host mounts by changing
its scenario manifest.

The trusted `--bridge-version` option selects 3 (default), 4, 5 or 6 for a compatible reviewed Android
APK; Python callers pass the same explicit `bridge_version`. The choice is recorded with the Android
inputs and is not a scenario manifest field. Version4 adds the
[custom-emoji contract](custom-emoji.md); version5 adds
[ordinary-document dependencies and bytes](documents-implementation-contract.md#bridge-version-5),
and version6 adds atomic media-group topology. `--android-theme light|dark` selects and records the
guest system appearance before the client starts; Python callers pass `android_theme`.
The public bridge5 workflow now passes a real contained Bot API consumer, original inline tap,
callback answer, stable-file reuse and two inspected original captures; exact transfer/cache bytes
remain covered by the dedicated document native gates.

The [example scenario](../../examples/echo/scenario.py) checks two complete conversations with an
[ordinary HTTP echo bot](../../examples/echo/bot.py), including mixed Persian/English and emoji.
Open the resulting `report.html` locally. No Telegram credentials or Android installation are
needed for this simulation-only run. The command performs its own namespace containment; the
development test suite also uses the [outer network guard](runtime-boundary.md).

The output directory must be new and its parent must exist without symlinks. Existing files,
directories and symlinks are refused. Each run gets a fresh private directory, world identity,
network namespace, loopback endpoints and credentials. Simultaneous invocations are supported.

## Persistent playground

`gramlab playground start` runs the same declared setup scenario but, after that scenario exits,
captures its World and consumer files as a baseline, restarts the declared bots, and keeps their
offline supervisor alive. Start is a foreground owner; control it from another terminal:

```sh
gramlab playground start run.toml --output artifacts/playground
gramlab playground status --output artifacts/playground
gramlab playground send --output artifacts/playground --chat-id -1 --actor-id 3 --text /game
gramlab playground tap --output artifacts/playground --chat-id -1 --actor-id 3 --label Continue
gramlab playground capture --output artifacts/playground --chat-id -1 --actor-id 3 \
  --label current --contains "Ready"
gramlab playground add-bot --output artifacts/playground \
  --group "Try the bot" --bot echo --actor mina
gramlab playground reset --output artifacts/playground
gramlab playground stop --output artifacts/playground
```

The control file is a private regular file containing the run identity, one random capability and
the fixed relative Unix-socket name. The owner rejects missing, malformed, wrong-run and wrong-
capability commands. A second start cannot reuse an existing output. Stop removes the live control
files, writes the normal redacted result/report, and is safe to repeat against that completed
result.

Trusted integrations may nominate declared bots that must reach the Bot API polling boundary before
the setup scenario starts. Playground setup uses semantic input and capture while Android boots in
parallel; once both are ready, later controls switch to native input and the final setup capture is
rendered once in the original client. This preserves a real running Android surface without paying
for every deterministic seed action through accessibility. The private emulator uses a bounded
four-core cold boot. It deliberately does not reuse AVD snapshots: snapshots are unreliable with
the isolated software renderer, and a strict attempted reload on the pinned emulator failed.

`send` applies the normal scenario composer contract as the explicit synthetic actor. `tap` selects
one unambiguous rich button with the exact visible label from the newest matching message. In
headless Android mode those operations use the existing original composer and native rich-button
input; simulation uses their semantic equivalents. With `mode = "interactive-android"`, start also
requires `--display-socket`, an Android runtime profile containing `scrcpy`, and a reviewed APK. It
opens the original Telegram Android screen in a clickable desktop window while keeping the emulator
headless and isolated internally. The selected Unix display socket is the only host display path
mounted into the viewer; guest IPv4 and IPv6 egress remain blocked. `capture` applies the normal
semantic expected-text check and retains an immediate PNG in Android mode.

The visible window accepts ordinary pointer and keyboard interaction through scrcpy. Its Telegram
composer and rendered controls act on the same authoritative World as the command helpers. The
`tap` helper is deliberately stricter than a human click: it rejects a target unless GramLab can
map current original-client geometry and effect evidence. A layout rejected by that evidence seam
can still remain visibly clickable for manual review.

`add-bot` resolves one unique seeded group title, configured bot alias and seeded actor username.
The actor must already be the group's creator or administrator and the selected bot must be absent.
Acceptance inserts the membership atomically and queues the ordinary `my_chat_member` update; the
real consumer can then answer in that group. Consumers that need a target-free group can seed it
with another declared inert bot until Android supports a zero-bot synthetic group.
This operation is an authenticated World transition, not a native Telegram administration screen;
the interactive client does not yet support adding the bot through Telegram's member picker.

Reset first terminates each consumer namespace and all of its descendants. It then replaces only
the owned World and bot directories from the post-setup baseline, restarts the declared bots and
refreshes the active Android chat when present. Consumer startup may update operational files such
as heartbeats after restoration; `at_baseline` therefore compares authoritative World state while
the containment acceptance separately proves that restored consumer files exclude prior mutations
and that retired descendants cannot write afterward. The playground lifetime is bounded to one
day even when the setup timeout is shorter.

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
provided by GramLab's runtime closure or the bot's selected trusted runtime profile. `/work` is on
the component's Python import path. GramLab does not create these profiles or install dependencies.
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

Each bot receives only `GRAMLAB_BOT_API` and `GRAMLAB_BOT_TOKEN` for its local API connection,
in addition to the explicit environment from its trusted runtime profile. A profile override uses
that profile's Python executable and read-only dependency closure. The outer trusted supervisor can
see the union needed to create nested mounts, but each bot component receives only its own selected
closure; bot restarts retain the same selection.
The scenario receives its separate control endpoint, capability and world identity. Each component
has private files and PID/mount namespaces. The supervisor owns the world database and services;
consumer code cannot read their files through `/work` or `/proc`. Provisioned profile environment
and the explicit component variables are the only supplied environment settings.

Bots start before the scenario. Updates remain queued while a bot initializes. An unexpected nonzero bot or
scenario exit fails the run. [Explicit scenario stops](scenario-lifecycle.md) are recorded separately
and allow generation-checked bot recovery. A zero-exit bot is allowed, including one-shot consumers. Once the
scenario exits successfully, still-running bots and all component descendants are terminated and
waited for. Expected bot cleanup does not turn a successful scenario into a failure. A passing run
means the scenario's own checks succeeded and no process failure was observed before cleanup.
It does not independently establish Telegram conformance or correctness of an empty scenario.

Stdout/stderr are drained while components run. Each generation’s stream is limited to 1 MiB, with a 2 MiB
aggregate run limit across all generations; exceeding either fails the run and stops its components. Process evidence
includes exit codes, whether the runner stopped the process, and whether each stream reached EOF
before cleanup. Logs stopped early are explicitly incomplete. Consumer-created files remain in
their private run directories; filesystem, memory and process quotas are not implemented yet.

## Results and limitations

Exit codes are `0` for passed, `1` for an executed failed/incomplete run, and `2` for rejected
configuration or preparation errors. Invalid input does not create an output directory. Later
setup/storage errors can leave a partial output directory; use a fresh destination for a retry.

Rich-button runs retain a separate [durable interaction recovery artifact](scenario-rich-buttons.md#lost-replies-and-recovery).
It remains available after abrupt supervisor termination; malformed journals fail visibly and are
never replayed. The recovery descriptor is included in `result.json` and `report.html`.

After normal execution, scenario/bot failure, timeout or unavailable runtime startup, the runner
retains `result.json` and `report.html`, with world state/history/events when world creation
succeeded. Process logs are redacted before the supervisor stores `observation.json`; the final
JSON and HTML also receive credential redaction. Full semantic evidence remains in `result.json`;
HTML sections over 128 KiB show a labeled 16 KiB preview. The result records source hashes, the
GramLab runtime profile fingerprint and a SHA-256 fingerprint for every bot profile override,
without adding profile paths to portable manifest inputs. `profile.json`, optional
`bot-profiles.json`, `run-input.json`, the copied sources, private component files and the SQLite
world remain local for diagnosis.

Keep run directories ignored. Arbitrary consumer-created files are not automatically sanitized
exports; review them before sharing. Neither the JSON nor the report claims that arbitrary secret
encodings or secrets supplied as ordinary prose can always be detected.

`simulation-only`, [headless Android captures](scenario-captures.md), and `interactive-android` are
connected to this command. Interactive Android additionally exposes the same original client through
the explicitly selected local display socket. [SDK inline-button input](scenario-input.md)
and [Start Bot/composer input](scenario-composer.md) are supported within their documented profiles;
broader composer fidelity, client restarts and faults, expanded dependency packaging and workload
diagnostics remain active work.
Overall elapsed time covers trusted execution and cleanup; Android metadata separately records
guest boot duration. Neither is an individual Bot API latency measurement.

## Verification

[Runner tests](../../tests/test_runner.py) invoke the actual CLI inside the outer network guard.
They verify the complete private scenario/real-bot exchange, profile-only bot dependencies,
per-bot closure isolation, profile-binding rejection, nested entries and selected data, input
rejection, separate concurrent worlds, environment clearing, redacted failure state, bot failure,
output bounds, runtime unavailability and timeout cleanup of a detached descendant.
A large-world case preserves complete JSON evidence while keeping HTML bounded. The
[control tests](../../tests/test_world_control.py) verify scoped, read-only named bot identities.
The documented two-conversation example also runs through the installed console entry point.

The lifecycle milestone passes 151 core tests at 81.88% measured statement coverage and all 19
Android tests; lint, formatting, strict typing, Nix/workflow checks and offline wheel/source
builds pass. Selected Python API tests explicitly trace actual contained supervisor execution
using the [test-only fixture](../../tests/conftest.py). CLI/guest behavior checks do not imply
additional measured coverage. [Capture evidence](scenario-captures.md) includes semantic parity,
two successive client personas, failure capture retention and Android startup timeout.
