# Local Android transport reliability

The isolated codec probe reproduces two distinct transport failures without launching the chat
application. Controlled comparisons separate Netsim forwarding stalls from reuse of an already
closed HTTP connection. The corrections are applied: select the pinned emulator's built-in
Virtio Wi-Fi forwarding path and explicitly advertise the bridge's existing connection closure.
The full core gate passes 216 tests at 81.09% coverage, and all 11 focused native checks pass.
The full Android gate stops at a separate activity-startup failure before composer input.

## Isolate the failures

The original composer fixture also ran an independent TL codec process at its end. A codec crash
there looked like a composer failure after the actual sends and recovery had already completed.
The [standalone test](../../tests/test_android_composer.py) now runs that codec in a clean dedicated
AOSP guest without installing or starting the application. It executes eight independent worlds
and verifies the full compact acknowledgment, paginated differences and 17 rejected commands per
world. That exercises 72 real HTTP requests while retaining each result separately. The existing
composer cases retain their own send, interruption, database and UI assertions.

The first isolated run passes. Repeated diagnostic runs reproduce the earlier native connect
timeout during the fifth codec invocation, on its final snapshot request. The listener accepts
that last connection immediately, but receives no HTTP request before the client times out.
Its observed TCP sockets are established with empty queues. Listener drops, overflows and host
TCP timeout counters do not increase. Earlier successful requests exhibit about half a second
between accept and completion, followed by another half second before the next accept.

The initial raw-packet observer is denied by the runtime boundary before exercising the codec.
Containment remains unchanged. The successful diagnostic observes listener accepts, handler
start/end, kernel counters and socket states instead. It records no HTTP body, authorization
header or exception text. The diagnostic wrappers remain ignored; normal tests use the actual
server and launcher directly.

## Controlled comparisons

The installed emulator's feature defaults enable `WiFiPacketStream`. Disabling only that feature
keeps Virtio Wi-Fi while selecting the emulator's built-in forwarding implementation. Google
also documents the separate [Netsim configuration surface](https://developer.android.com/studio/run/emulator-networking-advanced).
The guest's actual configured latency is already `none` and speed is `full`; this is not removal
of a scenario-requested network delay. Versions, APK, world operations and isolation remain fixed.

| Forwarding | Bridge close header | Result | Successful nine-request span |
| --- | --- | --- | --- |
| Default Netsim | Absent | Four complete runs, then native connect timeout | About 8.1–8.3 seconds |
| Built-in Virtio Wi-Fi | Absent | Six complete runs, then unexpected end of stream | About 58–118 ms |
| Built-in Virtio Wi-Fi | Present | Eight complete runs, 72 requests | About 54–96 ms |
| Default Netsim | Present | Four complete runs, then native connect timeout | The forwarding stall remains |

Spans measure first listener accept through final handler completion, not application launch,
user input latency or an end-to-end workload percentile. All comparisons use the same permitted
observer. The measurements establish this bounded difference; they do not identify the internal
Netsim defect or predict performance on every host.

The unexpected end-of-stream case has only three accepted connections when the client attempts
its fourth request. The nonpersistent bridge closes each HTTP/1.0 response but did not advertise
that closure. Explicit `Connection: close` prevents the observed reuse failure. The independent
[wire contract test](../../tests/test_client_sends.py) first fails on the missing header after
reading the complete response and observing actual EOF. It now verifies both the declared close
and actual EOF for successful sends and authentication, unsupported-route and invalid-body errors,
including exact responses and unchanged world state for rejections. Explicit nonpersistence is
also described by [HTTP connection management](https://www.rfc-editor.org/rfc/rfc9112.html#section-9.6).

## Applied changes and verification

- The semantic bridge advertises `Connection: close`; it still closes after every response.
  The two controlled native fault proxies advertise the same behavior.
- Both the consumer emulator launcher and dedicated test launcher pass
  `-feature -WiFiPacketStream`. The [pinned toolchain metadata](../../clients/android/toolchain.json)
  records that selection. No guest network privileges or external route is added.
- The codec is an independent Android test with eight fresh worlds; it no longer prevents the
  unrelated composer case from reporting its own result.
- The focused core bridge/send gate passes all 14 tests. The full core gate passes 216 tests at
  81.09% coverage. All 11 focused native checks pass: both send interruptions, live-gap recovery,
  eight independent codec worlds and all seven runtime checks, including guest egress isolation.
- The full 26-test Android gate stops with three passed and one failed test. The first composer
  launch reports `Status: timeout`; UIAutomator creates no XML, and the subsequent read fails.
  No composer input occurred. The retained evidence does not identify the startup root cause.
- Full strict typing, lint/format, Nix all-platform evaluation and declared host checks pass.
  Offline distributions build; the installed wheel runs the simulation composer example successfully
  with the exact Nix Python interpreter. An initial validation invocation selected a different
  managed interpreter and failed its runtime prerequisite; it is not a passing package result.

Use the [retained shells](environment.md) and [outer network guard](runtime-boundary.md). Focused
commands are `pytest tests/test_client_sends.py -k nonpersistent` and
`pytest tests/test_android_composer.py -k native_codec`. Keep generated traces and host details in
ignored per-run artifacts. Normal runs never capture packet payloads or raw credentials.

## Remaining uncertainty

These observations do not retrospectively identify the root exception behind the earlier generic
503 send failure. Its safe exception-class diagnostic remains available for another occurrence.
The earlier startup preference-file sync stall and missed-commit failure are also separate,
unresolved observations. A passing focused run does not establish the complete Android gate,
all concurrency patterns, every transport surface or fully deterministic Android timing.
