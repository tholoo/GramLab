# Native atomic-media-group codec probe

This GPL-2.0-or-later fixture launches the reviewed Android APK's actual `BridgeProbe`, semantic
adapter, Telegram `TLRPC` carriers and serializers. The applicable license is
[the Android adapter GPL text](../../../clients/android/patches/COPYING); the root MIT license does
not relicense this adapter-bound fixture.

The independently authored Python oracle serves strict bridge-v6 responses over the contained
loopback fixture boundary. This launcher contains no replacement Telegram schema or renderer and
does not start an application, account, native transport or file download. It exists so an older
APK can supply the required unsupported-v6 red and the album-era APK can prove canonical group IDs,
flag 17, complete topology, response-local dependencies, split-cursor recovery and one serialized
`TL_updates` envelope for each complete live group.

Compile only from cached inputs in the pinned Android shell:

```sh
tools/dev android --offline --command bash \
  tests/fixtures/android_media_groups/compile.sh \
  .cache/android-media-groups-codec-probe-RUN
```

The runtime test must use the shared `android-gate` lock and the mandatory loopback-only namespace.
It proves adapter decoding and original TL serialization, not rendering, media transfer, collage
geometry, retry behavior or cold-restart persistence; ticket114 owns those native surfaces.
