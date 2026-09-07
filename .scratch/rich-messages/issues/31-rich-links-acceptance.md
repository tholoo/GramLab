# Prove rich-link semantics, captures and original native rendering

Type: task
Status: ready-for-agent
Work state: claimed by coordinator
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
eleven valid/26 malformed rich cases through the original native serializer. Missing/wrong/extra
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
