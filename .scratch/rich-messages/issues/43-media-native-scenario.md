# Observe the real multipart photo scenario in the original Android client

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: none for authoring; green requires core/native integration and coordinator APK

Own only `tests/probes/android_media.py`, `tests/test_android_media.py`, and this ticket.
Coordinator owns APK/source preparation, all guest execution, shared docs and integration.
Reuse the committed `media_round_trip.run(show, observe)` three-stage hook and independently
validated `assert_media_scenario`/`stage_media_scenario`; do not alter them or production code.

Write a dedicated original-app probe: install once into a fresh guest, strip stage before writing
strict config, select bridge_version 3, launch chat bot 2, capture initial and live edited media,
then force-stop and rewrite the changed endpoint before cold restart. Keep the app cache across
same-World restart. Initial contains four photos, so retain separate bottom/top captures through
ordinary swipe if needed; identify positions from current UI rather than assuming all captions
fit one screen. Preserve PNG/XML, launch traces, capability-free media trace, cache hash/size
observations and account-free state. No prefilled cache or synthetic renderer is allowed.

The normal17 worker exposes diagnostic events in existing app-private trace JSONL: each media row
has event, asset_id, cache_file, file_size, digest_ok. Values are media_load_start,
media_load_coalesced, media_cache_hit, media_load_success, media_load_failure, media_load_cancel.
Success/cache_hit have digest_ok true. A trace alone is not proof of visible decoding: retain
original screenshots and real scoped cache-file hashes for independent coordinator inspection.
Do not turn missing transfer/cache/visual evidence into passing output. Preserve artifacts before
raising on failure. Expect asset IDs 1 PNG and 2 JPEG, stable native file names 1_1.jpg and 2_1.jpg;
original path selection belongs to FileLoader, discover it read-only in the dedicated app.

Test entry stages the existing scenario and guest support, observes full existing isolation checks,
compares complete simulation semantics through assert_media_scenario, and creates a bounded HTML
report of original screenshots. Include SDK/font/theme/profile inputs as established tests do.
Label this authoring/static-only until coordinator runs an immutable reviewed APK; no worker guest,
build, fabricated green, external traffic, or broad gate. Run scoped Ruff/format/mypy, commit owned
files and return a frozen clean handoff with explicit runtime limitations and terminal resources.

## Worker evidence

The dedicated three-stage original-app probe and Android test entry are authored on
`task/media-native-scenario`. The probe installs once, removes the orchestration `stage` before
writing strict bridge-version-3 configuration, captures bottom/top initial views, observes the live
edit, rewrites the reopened endpoint, and cold-starts the same app data. It retains original PNG and
UIAutomator XML files, launch traces, capability-free media traces, failure artifacts, and read-only
SHA-256/size observations from cache locations discovered inside the app sandbox.

The test reuses the independently specified media round trip, checks the full existing guest
isolation boundary, requires successful and cache-hit diagnostics for both original assets, compares
their private cache bytes with the committed PNG/JPEG, and packages four original screenshots into
a bounded report with SDK, system-image, display, theme, fonts, APK, guest and graphics inputs.
Scoped Ruff format/check and mypy pass. This is authoring/static evidence only: this worker did not
build an APK, start a guest or claim runtime rendering, decoding, transfer, cache or report success.

Coordinator source review corrects a fixture assumption before native execution: original
ImageLoader may decode a cached file before FileLoader is called. Restart acceptance therefore
checks unchanged cache bytes and no new transfer starts alongside original screenshots; it does
not require a synthetic FileLoader cache-hit diagnostic. Runtime acceptance remains pending.

Normal18 now renders both original PNG and JPEG in the real app, with inspected initial
screenshots and verified loader success. The run fails before edit because the probe searched
only internal files; upstream AndroidUtilities selects external cache and ImageLoader selects
app-owned external image storage. The corrected probe searches both dedicated app roots, records
every matching copy, quotes discovered paths and requires exact bytes plus stable paths across
edit/restart. This changes evidence discovery only. Full lifecycle green remains required.

The next retained run completes original initial/edit/restart observation and exact semantic
comparisons, then fails a host cache-set assertion: first using the PNG in a rich receiver adds
a correct cache copy alongside the ordinary image-directory copy. All copies have original
bytes. The corrected invariant retains initial paths through edit and requires the complete
edited cache set unchanged after restart, with no new transfer starts. Both inspected edited
and restarted screenshots show the replacement photo and bilingual rich caption. Native source
and APK remain unchanged; the corrected complete acceptance run is pending.

## Retained native acceptance

The complete normal19 scenario finishes all guest observations. A final host assertion compared
restart transfers with an edited trace captured before viewport-driven cache work had finished.
The complete ordered trace proves there are no transfer starts after its second initialization.
Host assertions now use that actual restart boundary and are factored into a callable evidence
validator. Revalidation passes in 0.21 seconds with all 26 original evidence files, APK, profiles
and staged native/scenario sources unchanged; the original failed JUnit remains untouched.
The first report is preserved, and a separate report explicitly labels retained acceptance.

Four original screenshots were inspected: JPEG quadrants, ordinary PNG decoding, live PNG
replacement with bilingual rich caption, and cold restart. Desktop/mobile report layouts load
all four original images without overflow. The top capture partly clips the ordinary caption and
contains a guest screenshot toast; better viewport framing and broader native gates remain open.
This acceptance establishes the semantic/render/edit/cache/restart checkpoint, not full media
fault or production-fidelity coverage. Scoped Ruff/format/mypy and workflow checks pass.
