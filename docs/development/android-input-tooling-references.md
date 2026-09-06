# Android Unicode input tooling references

Reviewed 2026-09-06. The initial static SDK and official-source review established a candidate
independent shell helper without package acquisition or runtime execution. Subsequent
[focused guest integration](android-composer.md) now proves connection, repeated Unicode input,
original Send activation and the stale-literal-hint rejection described below. Source findings
and remaining proposed checks are distinguished from that bounded runtime evidence.

## Candidate and source boundary

Use Android accessibility to replace the original editable node's text, verify the resulting
text, and activate the original Send control. This exercises the framework action exposed by
the application; it requires no application-specific text setter or copied Telegram UI code.
The [ACTION_SET_TEXT contract](https://developer.android.com/reference/android/view/accessibility/AccessibilityNodeInfo.AccessibilityAction#ACTION_SET_TEXT)
accepts text through a Bundle. In inspected AOSP,
[TextView](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/core/java/android/widget/TextView.java#15005) accepts it only when enabled
and editable, applies the CharSequence and places selection at the end. Unicode therefore
travels as text rather than as individually mapped virtual key events. In contrast,
[input text](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/services/core/java/com/android/server/input/InputShellCommand.java#374)
uses the virtual keyboard's KeyCharacterMap and special percent-space handling. It is not a
reliable arbitrary-Unicode transport.

AOSP tag `android-16.0.0_r1` resolves to framework commit
`99b01a65cc4c104933788b3143285ab6bae65827`; citations below use that immutable revision.
It is an Android 16 source reference, not a demonstrated exact source match for the provisioned
emulator image. Keep the existing [toolchain/image pin](../../clients/android/toolchain.json).
The installed platform-36 android.jar was inspected with javap: public UiAutomation exposes
root lookup and service configuration; AccessibilityNodeInfo exposes ACTION_SET_TEXT,
ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, performAction, getActionList and refresh. Hidden connection
construction and connect/disconnect methods are absent from those SDK stubs.

## Shell connection and lifecycle

The same-revision
[UiAutomationShellWrapper](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/cmds/uiautomator/library/testrunner-src/com/android/uiautomator/core/UiAutomationShellWrapper.java#25)
is a direct precedent: prepare the main looper explicitly for AccessibilityInteractionClient,
start a HandlerThread, construct UiAutomation with its looper and a UiAutomationConnection,
then connect. Disconnect before quitting the HandlerThread. Do not omit main-looper preparation
merely because callbacks have a separate thread.

[UiAutomation](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/core/java/android/app/UiAutomation.java#287) retains hidden public
constructors taking Context or Looper plus IUiAutomationConnection. The Looper overload assumes
the default display. [connectWithTimeout](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/core/java/android/app/UiAutomation.java#363)
accepts flags and a bounded timeout; connect(int) also exists. Since the SDK excludes this
setup, an original helper can compile against public android.jar and resolve only the hidden
setup reflectively. Actual hidden-API access and boot-class availability remain guest tests;
source visibility does not guarantee reflection permission.

[UiAutomationConnection](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/core/java/android/app/UiAutomationConnection.java#101)
has a public no-argument constructor, records the connecting UID, and registers with the system
accessibility service. [The service](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/services/accessibility/java/com/android/server/accessibility/AccessibilityManagerService.java#1626)
requires RETRIEVE_WINDOW_CONTENT, which the
[AOSP shell manifest](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/packages/Shell/AndroidManifest.xml#176) requests. Run as the
existing dedicated guest's shell identity, not under the target application's run-as identity.
No installed accessibility service, app permission grant or shell-permission adoption is implied
by this candidate. Observe the actual UID and registration result during the first proof.

Only one [automation registration](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/services/accessibility/java/com/android/server/accessibility/UiAutomationManager.java#108)
can be active. Serialize this helper with uiautomator dump and other automation consumers.
FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES can preserve existing services; do not use
FLAG_DONT_USE_ACCESSIBILITY because it disables the required operations.
[Connection configuration](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/core/java/android/app/UiAutomationConnection.java#669)
includes view IDs and window-content retrieval. These are automation privileges within the
existing isolated guest, not permission to inspect another runtime.

Always disconnect in cleanup and stop/join owned threads with bounded waits.
[UiAutomation.disconnect](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/core/java/android/app/UiAutomation.java#438) shuts down its
internal callback thread; the caller still owns its supplied HandlerThread. System registration
also links to owner death, but forced-process cleanup needs a subsequent connection test.
A failure to connect must not fall through to an input command or successful result.

## Safe input framing and targeting

Recommended original helper protocol: a bounded UTF-8 JSON document on stdin, with an explicit
operation, target package, expected current text and replacement text. Use a fixed app_process
command and fixed staged DEX/JAR path; feed bytes through subprocess stdin without a PTY.
Never embed the replacement text in shell arguments, shell expansions, environment variables
or command strings. Alternatively push a bounded request file to a fixed guest path and read
it directly; path generation remains trusted. Reject invalid UTF-8/unpaired surrogates and
oversized requests before obtaining or mutating a node. Do not log full request bodies.
This framing is a GramLab tooling recommendation, not a tested command.

Find a unique visible, enabled, editable node in the intended package/window and require that
it advertises ACTION_SET_TEXT. Validate existing content before replacement. Invoke performAction
with ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, then re-fetch or refresh and compare exact text.
A true action result does not prove text was preserved: input filters or text watchers can
change it. Re-fetch the Send control after text changes; reject missing or ambiguous controls.

The pinned [Telegram composer](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/ChatActivityEnterView.java#L3475)
sets a localized Send content description and a click listener. Its
[editable view](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/ChatActivityEnterView.java#L5659)
is a custom EditText subclass. These are targeting leads; inspect the actual exposed tree.
Perform ACTION_CLICK on the original control when advertised. If actual touch input is required,
use fresh verified accessibility bounds with the existing input injector and retain screenshots.
Keep input methods distinguished in reports. Never retry an uncertain Send action automatically.

## Alternatives and required proof

If hidden setup is unavailable, a separate test instrumentation APK can obtain public
[Instrumentation UiAutomation](https://developer.android.com/reference/android/app/UiAutomation)
without altering Telegram UI. This adds packaging/provisioning work and needs its own review;
it is not implemented here. A dedicated test IME is another input-system option, but adds an
installed component and input-method lifecycle. Clipboard or keyevent shortcuts do not establish
arbitrary-Unicode fidelity and should not silently replace failed accessibility input.

Root must prove reflective startup, shell identity, exact Persian/ZWNJ/combining/emoji/newline
round trips, unchanged original composer behavior, one Send action and one authoritative world
mutation. Also prove stale/ambiguous/wrong-package/disabled-node rejection, malformed framing,
input filtering, timeout and repeated connect/disconnect after failures. UI text acceptance alone
does not prove message acceptance; pair this with the
[composer acknowledgment contract](android-composer-references.md). Preserve upstream code and
state the remaining unavailable cases explicitly.

## Integration findings

The initial guest checks reached reflective connection but exposed a root-readiness race.
AOSP's own [DumpCommand](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/cmds/uiautomator/cmds/uiautomator/src/com/android/commands/uiautomator/DumpCommand.java#86)
waits for idle before looking up the active root. Successful connection establishes the client
connection, not an available window. A bounded read-only wait may resolve a missing root;
an unexpected package must still be rejected. Foreground screenshots alone do not establish
the package returned by the active-window lookup.

The pinned [EditTextBoldCursor override](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/EditTextBoldCursor.java#L1265)
exposes an empty editor's custom hint as node text without marking it as showing a hint.
Comparing text to a localized hint is unsafe: a draft can contain that literal text. The
[AOSP TextView metadata](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/core/java/android/widget/TextView.java#14255)
retains a useful distinction. Selection/movement actions and movement granularities are supplied
only for nonempty underlying text; the
[View selection initialization](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/core/java/android/view/View.java#11524)
likewise leaves empty text selection undefined. Telegram's later hint substitution preserves
these fields.

The conservative pinned-client predicate combines selection indices `-1/-1`, zero movement
granularities and absence of selection and next/previous movement actions, after verifying one
enabled editable non-password node. A literal `Message` draft at cursor zero must fail this
predicate. Do not execute selection actions to inspect emptiness; those actions can move the
cursor and start selection mode. This source-derived predicate is not a general guarantee for
arbitrary custom widgets, and separate validation/action calls are not an atomic compare-and-set
against concurrent user edits. The focused guest test now verifies this literal-draft rejection
and successful known-draft replacement. Broader wrong-window, ambiguous-control and concurrent-edit
cases remain unverified.
