# Offline execution requirements

Status: a [Linux process boundary](runtime-boundary.md) now enforces and tests namespace/mount
isolation for bounded processes. Dedicated AOSP guest startup, local traffic and external IPv4/IPv6
denial are tested. The [world/bot prototype](world-bot-prototype.md) adds scoped local capabilities
and contained HTTP exchange. A [native JNI guard](android-native-guard.md) rejects transport
request/initialization calls. [Synthetic application startup](android-application.md) now has
restricted lifecycle/transport paths and real rendering evidence. Complete application-specific
enforcement remains incomplete; the requirements below
are not yet satisfied end to end.

Real bot launches now use [private component filesystems and process namespaces](component-boundary.md)
on the run's isolated network. The emulator has a separate component filesystem and PID namespace,
with explicitly selected KVM access. Trusted world/ADB orchestration owns the broader run data
mount. Resource quotas, per-component control-port restrictions and the remaining application
network surfaces still require separate evidence.

## Boundary

Normal runs may communicate only with explicitly selected local simulator, bot, fixture and Mini
App endpoints. They must not contact Telegram production or Test DCs, cloud Bot API endpoints,
external asset URLs, push providers, analytics or arbitrary Internet hosts. No real tokens,
API hashes, phone numbers, purchased sessions or personal client data belong in this repository.

Dependency provisioning/upstream source acquisition happens separately before tests. External
reference research does not grant a running simulator network access. A future conformance runner
must have distinct configuration, explicit authorization and artifacts; offline execution must
never fall back to it.

## Required implementation evidence

- Enforce an explicit endpoint allowlist and independent OS/runtime egress isolation. Test IPv4,
  IPv6, DNS, redirects, WebSockets, native transport, WebViews, media and background services.
- Account for emulator-to-host routing explicitly. Loopback aliases or an HTTP proxy alone do
  not establish isolation. Blocking TCP in Python does not constrain Android/native processes.
- Start from clean dedicated runtime data with synthetic identities and test-only credentials.
  Never attach to the user's personal device/client or reuse Telegram auth state.
- Test that attempts to reach external destinations are rejected and observable. Capture evidence
  from every relevant process/runtime, not merely an absence of logged bot calls.
- Resolve media locally and validate paths/archive entries. Scope cleanup to owned run directories
  and dedicated runtime instances; validate identities before reset or deletion.
- Bind control interfaces narrowly, authenticate where needed, and separate world identifiers from
  authorization. Do not let arbitrary local callers control another run or read its artifacts.

## Artifacts

Reports need run/worker IDs, seeds, software/profile versions, relevant semantic IDs and failure
state. Redact credentials before storage, including URL paths, headers, exception text, logcat,
HTML and screenshots. Prefer synthetic IDs and never load real secrets merely to redact them.
Treat recorded user-supplied HTML/text as data when generating reports.
