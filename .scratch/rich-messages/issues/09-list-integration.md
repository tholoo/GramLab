# Integrate public list captures, input and original rendering

Type: task
Status: ready-for-agent
Work state: claimed by coordinator
Blocked by: none

Coordinator owns public traversal in src/gramlab/_captures.py and src/gramlab/_android.py,
public capture/button tests, a reusable real HTTP list example, native rendering tests,
shared documentation and combined verification. Integrate the frozen core/native branches
under the parallel-work workflow before using their behavior.

The coordinator delegates examples/rich_lists/ and tests/test_runner_rich_lists.py to the
worker on ticket 10. This keeps example/simulation work independent of native build and probe work.

Follow the pinned rich-list contract. Visit items[].blocks recursively in item order;
labels, values, checkbox metadata and empty items cannot identify readable message text.
Preserve closed-details visibility rules for native inline targeting. Establish a public
capture regression before changing traversal, then prove native list button identity with
actual callbacks and a rejection for indistinguishable messages.

Use one incremental contained APK build after fresh patch applicability and source identity
verification. Observe the full valid native codec catalog and all malformed rejections.
Real bot send/edit/cold-restart evidence must retain structured content and original images
for ordered labels, nested markers, wrapping, RTL indentation, checked/unchecked bot rows
and invisible empty items. Observe that user input cannot mutate bot-owned checkbox state.
Keep the original renderer and authorization gates intact; no new toggle API is assigned.

Run focused checks during iteration, then the applicable combined core/Android/static gates.
Keep machine-specific build/run details ignored. Update support documentation only to the
extent established by actual integrated evidence. This ticket does not complete the wider
rich-message/media/custom-emoji/Mini-App goal.

## Integration evidence

The reviewed Python branch is integrated. All 82 focused World and real HTTP tests pass,
including the unchanged Unicode property test, in 23.42 seconds without a concurrent guest.
Scoped lint, format and source typing pass. The earlier worker deadline failure is not
reproduced by this run; no deadline or test semantics were changed.

Public capture regression: the real bot sent canonical lists, but capture rejected nested item
text before traversal was added (one failed, one passed). Both expanded capture cases now pass,
including metadata and cross-fragment rejection. The native patch is integrated and builds offline
incrementally in 151 seconds; fresh preparation retains all 6,666 original UI/resource files and
the unchanged rich renderer. The full native list catalog and 42 malformed cases pass. Review
strengthened invalid type/value labels so label mismatch cannot mask missing validation.

The dedicated real-bot checkbox scene passes in 71.97 seconds. Original checkbox accessibility
reports two visible read-only rows while an empty item remains only in canonical content. A normal
tap opens the original message menu; the probe retains that observation, dismisses it with Back,
and verifies identical checkbox attributes, complete snapshot and events. The bot's live edit
reverses both states and switches to RTL; native serialization and cold restart retain the result.
All phase/menu images were reviewed. Initial diagnostic runs missed an over-specific private
breakpoint, then reached the original rich touch handler but left its menu covering the chat.
The passing probe removes the debugger and handles only the observed menu. No renderer or input
retry change was made. Public native list inline targeting and the combined gates remain pending.
