# Integrate public list captures, input and original rendering

Type: task
Status: ready-for-agent
Work state: resolved after coordinator integration
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

Native list inline red observed the fully rendered message, then rejected it with no callback
because the matcher found no readable identity. Three lines of traversal now visit item blocks
in order and preserve hidden-details exclusion. The positive callback/RTL-edit and offscreen
metadata-only ambiguity cases pass together in 178.46 seconds. All static scopes and the Nix
workflow check pass. Screenshot review identified an unwrapped advertised wrapping line and
the original ordered-marker/checkbox overlap; the example worker is refining the visual catalog
without changing supported input or rendering code. Native checkbox input now targets the
inspected single-line row midpoint; the combined gate will verify that final coordinate choice.

The final midpoint passes in the first concurrent trial and again alone in 74.91 seconds.
The final reusable example passes its corrected native trial. The concurrent startup failure and
test-assertion correction are retained in tickets 06 (developer tooling) and 10. Browser review of
the three-image public report and five-image checkbox report passes at desktop/mobile widths:
all original 320 x 640 images load, with no page overflow or external resource requests. The
coordinator-owned preview is stopped and its browser tab closed. The 38-case serial combined
Android gate is running; final acceptance remains pending.

Coordinator acceptance: the serial list-inclusive Android gate passes all 38 cases without skips
in 2,362.99 seconds. The full core gate passes 326 tests at 80.52% coverage; scoped/full static
checks, workflow validation, installed-wheel scenario and original report review pass. This closes
the bounded list work; the separately tracked rich-text normalization correction and wider
rich-action/media inventory remain open.
