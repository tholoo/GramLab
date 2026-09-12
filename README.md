# GramLab

<p align="center">
  <img src="https://raw.githubusercontent.com/tholoo/GramLab/main/docs/assets/gramlab-preview.png" width="320" alt="An English GramLab conversation in the Telegram Android renderer, with rich text, buttons and glass effects." />
</p>

[Original Android capture](https://github.com/tholoo/GramLab/blob/main/docs/assets/gramlab-preview.md), with glass effects enabled.

Test Telegram bots locally and inspect their messages in the actual Telegram Android client.
No Telegram account or production token is needed.

**Experimental.** Text, callbacks, rich messages, photos, documents, albums and custom emoji have
tested original-Android workflows. Mini Apps, HTML parse modes, grouped-media edits, external
Telegram conformance and interactive Android mode remain unfinished.
See the
[compatibility matrix](https://github.com/tholoo/GramLab/blob/main/docs/compatibility/matrix.md)
for the supported scope.

## Install

GramLab currently requires Python 3.13 on a supported Linux host. Install the experimental
prerelease explicitly:

```sh
uv add "gramlab==0.1.0a1"
```

The package includes the `gramlab` command and typed Python scenario interface. Android captures
require separately prepared local tooling and are not distributed in the Python package.

## Write a scenario

Create a user, talk to a real local bot, check its reply and capture the conversation:

```python
from gramlab import Scenario

lab = Scenario.from_environment()
chat = lab.conversation(user=lab.user("Alex", language_code="en"), bot="echo")
chat.send("Hello!")
history = chat.wait_for_messages(2, timeout=5)

if history[1].text != "Echo: Hello!":
    raise AssertionError("Unexpected bot reply")
chat.capture("hello", contains=["Echo: Hello!"])
```

This runs inside a scenario process. The
[English echo example](https://github.com/tholoo/GramLab/blob/main/examples/echo/hello.toml) uses
this exact [scenario](https://github.com/tholoo/GramLab/blob/main/examples/echo/hello.py),
with the bundled bot and manifest, and the runner supplies the environment. Simulation records the conversation state;
headless Android also captures the original client. Both modes produce a local HTML report.
The typed handles are additive: advanced scenarios can still use the raw JSON-shaped operations
on `Scenario`. The Python interface is still experimental.

## Try it

Start with the
[development environment](https://github.com/tholoo/GramLab/blob/main/docs/development/environment.md).
On a supported Linux
host with Nix and user namespaces:

```sh
nix develop
uv sync --locked
mkdir -p artifacts
uv run --locked --offline gramlab run examples/echo/hello.toml --output artifacts/echo-demo
```

Open `artifacts/echo-demo/report.html`. Use a new output directory for each run.
The runner isolates bot and scenario processes; dependency setup happens before execution.
Android captures require the separate
[Android setup](https://github.com/tholoo/GramLab/blob/main/docs/development/android-build.md).

More examples: [button presses](https://github.com/tholoo/GramLab/tree/main/examples/inline),
[rich messages](https://github.com/tholoo/GramLab/tree/main/examples/rich),
[rich buttons](https://github.com/tholoo/GramLab/tree/main/examples/rich_inline), and
[bot restart](https://github.com/tholoo/GramLab/tree/main/examples/recovery).

## Work on GramLab

- [Contributor setup and checks](https://github.com/tholoo/GramLab/blob/main/CONTRIBUTING.md)
- [Current handoff and remaining work](https://github.com/tholoo/GramLab/blob/main/docs/development/handoff.md)
- [Architecture](https://github.com/tholoo/GramLab/blob/main/docs/architecture/overview.md) and [product scope](https://github.com/tholoo/GramLab/blob/main/docs/product/requirements.md)
- [Offline execution rules](https://github.com/tholoo/GramLab/blob/main/docs/development/offline-safety.md)
- [Working in parallel](https://github.com/tholoo/GramLab/blob/main/docs/development/parallel-work.md)
- [Release history](https://github.com/tholoo/GramLab/blob/main/CHANGELOG.md)

Original core and SDK code uses [MIT](https://github.com/tholoo/GramLab/blob/main/LICENSE). Two
TDLib-derived Python modules retain
[BSL-1.0](https://github.com/tholoo/GramLab/blob/main/LICENSES/BSL-1.0.txt). Android-derived patches
and fixtures retain GPL-2.0-or-later. See the
[license map](https://github.com/tholoo/GramLab/blob/main/NOTICE) and
[licensing boundaries](https://github.com/tholoo/GramLab/blob/main/docs/development/licensing.md).
This is a source repository. No Android APK release or completed dependency license audit is offered.

GramLab is unofficial and is not affiliated with or endorsed by Telegram.
