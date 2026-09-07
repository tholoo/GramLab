# Prove rich-link semantics, captures and original native rendering

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: tickets 29/30 for green behavior; red fixtures are independent

Coordinator owns `tests/fixtures/rich-links-scene.json`,
`tests/probes/rich_links_round_trip.py`, `tests/probes/android_rich_links.py`,
`tests/probes/android_message_codec.py`, `tests/test_rich_links_round_trip.py`,
`tests/test_android_rich_links.py`, `tests/test_runner_rich_link_captures.py` and this ticket.
Worker implementations must not change these independent oracles.

Reuse the real form-encoded rich bot/lifecycle. Compare full initial/edited World/API content,
events/history/snapshot and empty queue for URL/email/phone metadata plus recursive multilingual
labels. Check public CLI captures against labels and rejection of destinations, stale metadata
and text spanning distinct fragments. Simulation captures must remain explicitly unrendered.

Use one trusted canonical/adversarial snapshot codec in a dedicated offline guest, bypassing only
Python content validation in the fixture server. Compare the full unchanged baseline and all
eleven valid/29 malformed rich cases through the original native serializer. Missing/wrong/extra
metadata, wrong visible-text shape, unknown type and unrequested cached-page fields reject.
The reverse URL serializer independently checks the native zero cached-page identity.

The real-bot Android scenario must retain complete native content, visible labels without hidden
destinations, live edit, both cold-launch statuses, account-free component/network separation,
original PNG/XML and reviewed report timings. No destination is opened. Retain old core/native
rejections and actual full-gate limits; resolve only after integrated acceptance. This does not
complete navigation, default automatic detection, mentions, media or custom emoji.

Independent acceptance fixtures are prepared before worker integration. On the unchanged core,
the real form-encoded bot fails at `sendRichMessage` with HTTP 400 (one failure, 0.99 seconds).
The public CLI capture scenario also fails at the unsupported rich send (one failure,
1.12 seconds). Original logs and JUnit results are retained outside version control. All six
new Python acceptance/probe files pass scoped Ruff, formatting and strict project mypy checks;
their type-check command is maintained in contributor guidance and CI. Native old-APK red and
integrated green checks remain pending. The earlier 43-case native baseline excludes these two
new Android tests and cannot prove their acceptance.

The combined integration selection passes 144 cases in 60.27 seconds after correcting a primary
editable install that imported the polling worker. Earlier integration results affected by that
environment error are not acceptance evidence. The public bot and captures now pass complete
state/visible-label expectations. The native malformed-record oracle uses the established
`GRAMLAB_BRIDGE_INVALID_RICH_MESSAGE` diagnostic, as specified by the independent existing
rich-button codec contract; the initial fixture incorrectly used the ordinary-message diagnostic.
Old-APK rejection is being repeated with the verified primary import before native integration.

The corrected old-APK red reproduces valid-link rejection in 60.26 seconds. Normal15 compiles,
but its first native acceptance run stops after valid baseline/scenes/URL variants: missing URL
metadata yields no JSON. A diagnostic repeat retains exit 137, empty stdout and `Killed` stderr
in 49.63 seconds. The source's missing-field `get` lies outside its classified error path; no
Java exception stack was captured. Ticket 32 adds narrow presence checks and the independent
catalog adds missing visible text for each type, bringing malformed cases to 29. Normal16 and
original rendering/combined native acceptance remain pending; no failed result is relabeled green.

Normal16 passes both native tests in 135.98 seconds, including baseline, 11 valid and 29 malformed
shapes, complete real-bot/native semantics, actual bilingual/RTL labels, metadata/text edit,
both cold-launch statuses and independent account-free containment checks. All three original
PNGs and desktop/mobile reports were inspected; embedded bytes match, all images load, timings
use milliseconds, and neither viewport overflows or requests external resources. The remaining
43 Android cases run on the same immutable APK after verifying retained source/profile/import
inputs; full 45-case acceptance remains pending.


## Combined integration acceptance

The corrected normal16 inventory passes all 45 distinct Android cases: two focused rich-link
cases in 135.98 seconds plus the remaining 43 in 2525.72 seconds. The coordinator independently
verifies exact collection coverage with no duplicate or missing cases, unchanged source/fixtures,
APK and runtime profiles, and the primary checkout import. This is resumed coverage on one
immutable APK, not one uninterrupted run. No earlier contaminated result is reused.

The 447-case core gate passes at 81.18% coverage, and applicable static/workflow checks pass.
Fresh quoted-code edit/restart and list restart PNGs were inspected alongside the already reviewed
rich-link originals and reports. Original missing-field, disk-space, late-launch and import
failures remain retained; passing this gate does not establish their broader causes as fixed.
The assigned feature/fix is integrated and accepted. Media, mentions, automatic rich detection,
custom emoji and the full operational milestone remain unfinished.
