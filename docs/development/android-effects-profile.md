# Android effects profile

This note bounds the effects question for the pinned Telegram Android 12.10.1 source at
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. It records source-derived expectations and a
native comparison procedure, followed by a verified runtime comparison using the original
Power Usage controls. The launcher defaults and upstream renderer remain unchanged.

## Source-derived gates

[`SharedConfig.measureDevicePerformanceClass()`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SharedConfig.java#L1649-L1711)
selects LOW, AVERAGE or HIGH from Android version, logical CPU count, maximum CPU frequency, the
application's Android memory class and total RAM. Its LOW branch is a disjunction: Android below
21, at most two CPUs, memory class at most 100 MiB, several explicitly conjoined CPU/frequency/
memory/version cases, or known total RAM below 2 GiB each suffice. If none selects LOW, its
AVERAGE branch independently accepts fewer than eight CPUs, memory class at most 160 MiB, a known
maximum CPU frequency at most 2055 MHz, or the final conjoined unknown-frequency/eight-CPU/old-
Android case. A stored `overrideDevicePerformanceClass` takes precedence over measurement; the
measured value is cached in the process but is not written by this method.

[`SharedConfig.canBlurChat()`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SharedConfig.java#L1748-L1754)
requires AVERAGE on Android 12/API 31 or newer and HIGH on older Android versions (apart from the
private debug-build exception). `chatBlurEnabled()` additionally requires
`LiteMode.FLAG_CHAT_BLUR` (`256`). Power saving matters because
[`LiteMode.isEnabled()`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/LiteMode.java#L102-L118)
uses the zero-valued `PRESET_POWER_SAVER` while the battery percentage is at or below a configured,
positive threshold. [`ChatActivity`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java#L2615-L2639)
constructs its RenderNode-based noise suppressor only on Android 12 or newer when
`chatBlurEnabled()` is already true. The composer otherwise draws the
[opaque panel fallback](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/ChatActivityEnterView.java#L4710-L4717).
Thus an available software GPU alone cannot enable chat blur.

On a fresh preferences store,
[`LiteMode.loadPreference()`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/LiteMode.java#L202-L285)
chooses one [built-in mask](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/LiteMode.java#L38-L90)
by performance class:

| Class | Built-in mask | Chat blur | Liquid glass |
| --- | ---: | --- | --- |
| LOW | `198684` | off | off |
| AVERAGE | `204383` | off | off |
| HIGH | `262143` | on | off |

Liquid glass is the distinct `FLAG_LIQUID_GLASS` bit (`1 << 18`, or `262144`). No built-in preset
contains it. Migration from `lite_mode5` to `lite_mode6` explicitly clears it. The
`lite_app_options.settings_mask` arrays delivered through app config may
[replace all three preset masks](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/LiteMode.java#L176-L200),
but a persisted `lite_mode6` value remains the selected value. The offline synthetic adapter does
not by itself prove which app config or preferences were applied at runtime.

The [blur3 factory](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/blur3/BlurredBackgroundDrawableViewFactory.java#L57-L85)
forwards the liquid-glass flag only on Android 13/API 33 or newer and only for a RenderNode-backed
drawable. Its implementation uses `RuntimeShader`/`RenderEffect`; the
[scrollable noise suppressor](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/blur3/DownscaleScrollableNoiseSuppressor.java#L26-L59)
requires a hardware-accelerated canvas. These are later rendering prerequisites, not alternatives
to the LiteMode bit. Theme colors and wallpaper content determine how visible a captured blur is.
Alert-dialog blur has an additional dark-theme condition, but `SharedConfig.chatBlurEnabled()`
itself has no theme check.

## Current GramLab baseline

The dedicated launcher creates a fresh AOSP API 36 x86_64 guest with two virtual CPUs, 2 GiB of
RAM and `swangle` (SwiftShader through ANGLE). Existing native evidence uses a 320×640 viewport at
160 dpi, upstream default theme and fonts, English client UI and Persian/English message content;
animation timing is not normalized. The two-CPU condition is sufficient, from source alone, to
select LOW unless a stored performance override is present. LOW then defaults both chat blur and
liquid glass off. This is a deduction from the launcher and pinned source, not an observation of
the live Java fields or pixels.

Earlier conversation screenshots establish real upstream rendering under this baseline. The
separate four-state comparison below now records settings and original captures from one world;
it does not change the default profile used by consumer scenarios.

## Prepared debug build and persistent settings

The custom `TMessagesProj_GramLab` application depends on the `TMessagesProj` library.
[`BuildVars`](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/BuildVars.java#L19-L27)
reads the library's `org.telegram.messenger.BuildConfig`, not the application's separate namespace.
The prepared library debug BuildConfig has `DEBUG_VERSION`, `DEBUG_PRIVATE_VERSION` and
`GRAMLAB_OFFLINE` true. That establishes source/build eligibility for the upstream Force
performance class menu and the private-debug exception exposing blur/glass rows even at LOW.
The runtime comparison below separately verifies those rows and selected effects. Recheck generated
variant outputs if the build changes; keep their actual local paths out of tracked notes.

The account-zero `mainconfig` SharedPreferences store contains these integer keys:

| Key | Meaning |
| --- | --- |
| `overrideDevicePerformanceClass` | -1 uses measurement; 0 LOW, 1 AVERAGE, 2 HIGH |
| `lite_mode6` | Persisted selected effect mask; absence selects the class preset |
| `lite_mode_battery_level` | Battery threshold, 0–100; 0 disables this power-saver gate |

The [performance override method](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SharedConfig.java#L1182-L1186)
reloads LiteMode but removes only the obsolete `lite_mode` key. Existing `lite_mode6` therefore
continues to win after changing class; selecting HIGH alone does not replace it with HIGH's mask.
Record mask presence/value before the change and enable the intended exposed rows explicitly.
Retain battery percentage and threshold with accessible checked states, because the effective
mask can be zero while the stored flags remain enabled. Settings use asynchronous `apply()`;
read back the persisted selected values before force-stop. Reconstruct the chat on cold launch
because its blur objects snapshot relevant flags in their constructors. The debug device/class
screens can expose current and measured class; actual hardware-accelerated RenderNode/shader
execution still needs its own runtime evidence.

## Smallest native observation and comparison

Use the focused `tests/test_android_effects.py` probe rather than running the full Android suite. Coordinate the guest with the owner of the `android-gate` lock and retain all
machine paths in ignored notes. Use one fresh dedicated guest and the already approved APK.

1. After the synthetic chat becomes stable, retain API level, online CPU count, total RAM,
   SurfaceFlinger's GLES line, battery percentage, UI hierarchy and a screenshot. Retain the
   package's `mainconfig` preferences through `run-as`, redacting them before any report. The
   absence of `overrideDevicePerformanceClass` and `lite_mode6` is meaningful and must not be
   rewritten as an observed LOW value.
2. Open the upstream Settings debug menu's `Force performance class` dialog and retain the choice
   marked `(measured)`. Also capture Power Usage with its Chat group expanded: on this pin the
   release builds omit chat-blur and liquid-glass rows for LOW, while the private debug flag
   bypasses that class restriction (liquid glass still requires API 33+), as the [pinned settings code shows](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/LiteModeSettingsActivity.java#L257-L270).
   Record exact accessible labels and checked states; source inspection alone is insufficient.
3. Capture the baseline chat at a settled point with a patterned wallpaper visible immediately
   behind the composer and navigation surfaces. Preserve the same world, theme, viewport, scroll
   position, keyboard state and animation-settle rule for the comparison.
4. In that disposable package only, expand Chat in Power Usage and enable chat blur. The pinned
   private debug build exposes it without a performance override; retain that class selection for
   an isolated flag comparison. Force-stop and cold-launch so `ChatActivity` reconstructs
   the blur3 objects, then capture the same chat and repeat the semantic assertions. Retain the
   resulting preferences and confirm the performance override remains absent and
   `lite_mode6 & 256 != 0`. This is the smallest useful chat-blur comparison; it changes no
   launcher default or APK.
5. Treat liquid glass as a separate comparison. On API 36, enable its exposed
   Power Usage checkbox, cold-launch and capture a surface that actually wires the liquid-glass
   factory (the chat composer/navigation region is suitable). Confirm hardware acceleration and
   `lite_mode6 & 262144 != 0`. Do not infer success merely because the app did not crash.

For both comparisons, inspect the original PNGs. A pixel difference is supporting evidence only:
the enabled capture must show the expected background sampling/refraction at a named surface,
while the hierarchy and complete semantic history remain equal. A disabled control, unchanged
pixels or a software-rendering exception is useful negative evidence and should remain visible.
Afterward clear only this disposable package or discard its dedicated AVD; never promote its
preferences to the baseline profile.

## Verified original-UI comparison

The dedicated [probe](../../tests/probes/android_effects.py) and
[host test](../../tests/test_android_effects.py) pass in 174 seconds with the same APK, world and
API 36 guest. Four cold-launch captures retain the complete bilingual rich history, zero accounts
and battery level 100. External IPv4 and IPv6 attempts are denied by the existing guest harness.
No performance override is stored. The original checkboxes and persisted integer values agree:

| Phase | Blur | Liquid Glass | Stored mask | Battery threshold |
| --- | --- | --- | ---: | ---: |
| Baseline | preset | preset | absent | absent (source default 10) |
| Blur | on | off | 198940 | 10 |
| Glass | on | on | 461084 | 10 |
| Restored | off | off | 198684 | 10 |

Original PNG review shows opaque white composer/action-bar islands initially, translucent
wallpaper-tinted islands with blur, and a subtler changed edge/tint with glass. Restoration returns
the islands to opaque white. It is not an identical-frame restoration: the system clock advances
and the navigation strip remains wallpaper-colored in the restored frame. No screenshot was
edited, and those differences are retained rather than normalized away.

A one-shot external JDWP breakpoint observes the original `LiquidGlassEffect.update` on the
main thread with `foregroundColor = 0xd8ffffff` (alpha 216). Its source path constructs
`RuntimeShader`/`RenderEffect` and updates the drawable display list only on a hardware-accelerated
canvas. This runtime entry plus the source path is evidence of that original shader path; it does
not establish pixel-perfect rendering across all Telegram surfaces. The report includes all four
original captures, selected values, complete history, graphics string and launch/capture timings.

The first probe missed the breakpoint because it tapped an already-focused composer after the
initial display list was cached. The corrected trigger types a wrapping unsent draft, observes the
field grow from 40 to 82 pixels, then deletes it without sending. A second attempt reached that
method but stopped at the optional notification sheet during restoration. The passing probe
retains breakpoint evidence immediately and dismisses only that observed sheet with Back. These
were observation-harness failures, not demonstrated renderer defects. No APK rebuild was needed.

## Development cost

The later list-inclusive 38-case Android gate accepts the streamlined effects probe with 20
navigation captures instead of 39. All four original states, complete history and shader-entry
evidence remain; the four retained images were inspected. The case takes 132.683 seconds versus
175.800 seconds in the preceding gate. Different run load prevents attributing the whole duration
change to the reduced navigation. No APK, renderer, timeouts or fidelity profile changed.

The rich-message checkpoint's complete Android gate contains 29 tests and takes about 27 minutes,
while the
focused application probe has one guest boot and already retains launch, hierarchy and screenshot
evidence. Reusing that guest for baseline and enabled captures avoids a second boot and avoids an
APK rebuild because the comparison uses upstream settings. Static source/profile checks should run
before acquiring `android-gate`; if they fail, no scarce guest time is consumed. The full gate is
appropriate only after a production/profile change, which this investigation does not make.

## Remaining evidence

The measured Java performance class is not directly observed. The comparison establishes the
named original shader method on this profile, not universal device or surface conformance. Any proposal to raise the default CPU
count, persist HIGH, inject app config or enable either effect belongs to the coordinator because
it changes the fidelity profile and may change runtime cost and screenshots.
