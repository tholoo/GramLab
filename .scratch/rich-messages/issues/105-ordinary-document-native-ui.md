# Prove the real-bot ordinary document UI and restart workflow

Type: task
Status: ready-for-agent
Work state: claimed
Owner: task/ordinary-document-native-ui
Blocked by: native execution requires reviewed delivery104 APK; core scenario preparation is independent

Prepare complete real-bot and original Android acceptance for the integrated typed document
World/Bot API/v5 HTTP contract. Read [documents](../../../docs/development/documents.md), the
[frozen contract](../../../docs/development/documents-implementation-contract.md) and ticket104.
Do not replace the actual renderer, fabricate successful native output or count host-only checks
as original UI evidence. General default classification, document edits and albums remain required
separate work; this task proves the implemented explicit forced-file lifecycle.

Own this ticket, new `tests/fixtures/document_bot.py`, `tests/probes/document_round_trip.py`,
`tests/test_document_round_trip.py`, `tests/probes/android_document_ui.py` and
`tests/test_android_document_ui.py`. Use existing original photo/custom-emoji fixtures and report
helpers. Do not edit production core, Android patches, shared probes/tests, runner selectors,
lockfiles or dependencies. Coordinator owns APK compilation, actual guest execution, shared-doc
updates and any host v5 selector enablement. Use a separate branch/worktree and small cached inputs.

## Shared scenario

Run an actual isolated bot using real Bot API HTTP. Send an ordinary non-image document with a
Persian/English filename, explicit force-file flag, caption formatting, a registered original
custom emoji and an inline callback keyboard. Have an actual callback cause the bot to answer and
send a second message by reusing its returned document file ID. Also verify authenticated getFile
and exact downloaded bytes, and a rejected invalid/cross-kind request without semantic mutation.
Compare independently specified complete API responses, updates, histories, events and retained
grants after reopening. Drive the same semantic flow in simulation and Android. Keep test data and
configuration independent of private consumer applications.

## Original Android evidence

Configure the dedicated original app explicitly for bridgev5 with existing local capabilities.
Reuse original install/start/capture/ADB-isolation helpers and the fixed rendering profile. Capture
original rows, filename, caption/custom emoji and keyboard; drive an actual original download
control where required and an actual ordinary callback tap. Inspect current UI structure and bind
input to its current visible target; do not hardcode a guessed cell coordinate or alter drawing.
Do not open an external file viewer, URL or Telegram endpoint.

Verify exact downloaded bytes at the original final saved destination and full trace identity,
including ordinary document ID rather than image asset ID. Confirm the reply uses the same typed
document and valid cached bytes. Cold restart the same dedicated app data, require the original
conversation/caption/keyboard, and prove cache reuse through preserved destination hashes plus
absence of a new document GET. Keep GET accounting phase-local and account for existing image/emoji
requests separately. Match the actual104 event/descriptor contract with its worker before freezing
native assertions; report missing diagnostics rather than guessing fields or relaxing outcomes.

Retain original screenshots, XML, process/API/World evidence, exact source/APK/profile identity and
a bounded self-contained report. Include zero-account and component/egress isolation checks.
Report export must stay within its supported screenshot bound. An Android launch, a returned path
or a trace event alone cannot establish the required original rendering or bytes.

## Verification and handoff

Follow TESTING.md, offline safety, licensing and parallel workflow. Exercise the real contained
core/bot scenario now, with useful invalid/retry controls, strict typing and Ruff. Native code may
be prepared against the frozen v5 interface, but native execution waits for the reviewed104 APK;
do not launch a guest, build an APK or change the live source. Mark that gate unavailable rather
than passing or replacing it. Compile/provision only minimal cached owned inputs. Hand back a clean
frozen commit, exact tests and source hashes, terminal processes, and the coordinator's runnable
native command/environment requirements. Keep transient run data bounded and machine paths ignored.

## Worker handoff

The contained real Bot API scenario now proves the complete forced-PDF lifecycle. Its independent
oracle covers the bilingual filename, formatted caption and registered custom emoji, callback
keyboard, callback answer, same-file-ID reuse, repeated authenticated `getFile`, exact Bot API and
v5 downloads, cross-kind and foreign-bot rejection, all public responses, updates, history, events,
dependencies, grants and reopened state. The final isolated host run is retained under
`artifacts/document-ui-host-02` and passes the host case; Android collection is skipped because a
reviewed delivery104 APK was intentionally unavailable.

The Android probe is prepared against worker104's exact descriptor and trace contract. It records
phase-local v5 requests, binds the download and callback inputs to current semantic UI bounds,
checks that download cannot start before the tap, captures five original screens within the report
limit, verifies the exact presentation filename and bytes separately from the `-1_-1.pdf` cache
key, requires typed document trace rows without `asset_id`, and proves cold-restart cache reuse by
destination hashes and zero later document GETs. It also retains complete Bot API/World evidence,
XML, screenshots, source revision, APK/profile hashes, zero accounts, and component/egress
isolation. No guest, APK build, live source edit, external viewer, production substitute or claimed
native result was used by this worker.

Scoped Ruff format/check and strict mypy pass on all five Python inputs. The final focused selection
passes one host case and skips the unavailable Android case under the required isolated network
namespace. Coordinator execution needs the standard `android-gate` lock plus
`GRAMLAB_RUNTIME_PROFILE`, `GRAMLAB_ANDROID_RUNTIME_PROFILE`, `GRAMLAB_ANDROID_PROBE_APK`, readable
KVM, and `pytest -m android tests/test_android_document_ui.py` inside the documented private network
guard. Keep this ticket claimed until that reviewed104 native run and screenshot inspection pass.
