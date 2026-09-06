# Android effects profile

This note bounds the effects question for the pinned Telegram Android 12.10.1 source at
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. It records source-derived expectations and a
native comparison procedure. No effects-enabled run was performed for this note, so it does not
establish a visual fix or a runtime value.

## Source-derived gates

`SharedConfig.measureDevicePerformanceClass()` selects LOW, AVERAGE or HIGH from Android version,
logical CPU count, maximum CPU frequency, the application's Android memory class and total RAM.
Any device with at most two logical CPUs is LOW. Other independent LOW conditions include an
Android memory class at most 100 MiB and total RAM below 2 GiB. The next branch selects AVERAGE for
fewer than eight CPUs, a memory class at most 160 MiB or a resolved maximum CPU frequency at most
2055 MHz. A stored `overrideDevicePerformanceClass` takes precedence over measurement; the
measured value is cached in the process but is not written by this method.

`SharedConfig.canBlurChat()` requires AVERAGE on Android 12/API 31 or newer and HIGH on older
Android versions (apart from the private debug-build exception). `chatBlurEnabled()` additionally
requires `LiteMode.FLAG_CHAT_BLUR` (`256`). Power saving matters because `LiteMode.isEnabled()`
uses the zero-valued `PRESET_POWER_SAVER` while the battery percentage is at or below a configured,
positive threshold. `ChatActivity` constructs its RenderNode-based noise suppressor only on
Android 12 or newer when `chatBlurEnabled()` is already true. The composer otherwise draws the
opaque panel fallback. Thus an available software GPU alone cannot enable chat blur.

On a fresh preferences store, `LiteMode.loadPreference()` chooses one built-in mask by performance
class:

| Class | Built-in mask | Chat blur | Liquid glass |
| --- | ---: | --- | --- |
| LOW | `198684` | off | off |
| AVERAGE | `204383` | off | off |
| HIGH | `262143` | on | off |

Liquid glass is the distinct `FLAG_LIQUID_GLASS` bit (`1 << 18`, or `262144`). No built-in preset
contains it. Migration from `lite_mode5` to `lite_mode6` explicitly clears it. The
`lite_app_options.settings_mask` arrays delivered through app config may replace all three preset
masks, but a persisted `lite_mode6` value remains the selected value. The offline synthetic
adapter does not by itself prove which app config or preferences were applied at runtime.

The blur3 factory forwards the liquid-glass flag only on Android 13/API 33 or newer and only for a
RenderNode-backed drawable. Its implementation uses `RuntimeShader`/`RenderEffect`; the scrollable
noise suppressor requires a hardware-accelerated canvas. These are later rendering prerequisites,
not alternatives to the LiteMode bit. Theme colors and wallpaper content determine how visible a
captured blur is. Alert-dialog blur has an additional dark-theme condition, but
`SharedConfig.chatBlurEnabled()` itself has no theme check.

## Current GramLab baseline

The dedicated launcher creates a fresh AOSP API 36 x86_64 guest with two virtual CPUs, 2 GiB of
RAM and `swangle` (SwiftShader through ANGLE). Existing native evidence uses a 320×640 viewport at
160 dpi, upstream default theme and fonts, English client UI and Persian/English message content;
animation timing is not normalized. The two-CPU condition is sufficient, from source alone, to
select LOW unless a stored performance override is present. LOW then defaults both chat blur and
liquid glass off. This is a deduction from the launcher and pinned source, not an observation of
the live Java fields or pixels.

The existing screenshots prove that the real upstream chat renders under this baseline. They are
not an effects comparison: the fixture was not chosen to expose blur boundaries, runtime flags
were not recorded, and the baseline and an enabled variant were not captured from the same world
and frame state.

## Smallest native observation and comparison

Extend the existing focused `tests/test_android_application.py` probe rather than running the full
Android suite. Coordinate the guest with the owner of the `android-gate` lock and retain all
machine paths in ignored notes. Use one fresh dedicated guest and the already approved APK.

1. After the synthetic chat becomes stable, retain API level, online CPU count, total RAM,
   SurfaceFlinger's GLES line, battery percentage, UI hierarchy and a screenshot. Retain the
   package's `mainconfig` preferences through `run-as`, redacting them before any report. The
   absence of `overrideDevicePerformanceClass` and `lite_mode6` is meaningful and must not be
   rewritten as an observed LOW value.
2. Open the upstream Settings debug menu's `Force performance class` dialog and retain the choice
   marked `(measured)`. Also capture Power Usage with its Chat group expanded: on this pin the
   chat-blur and liquid-glass rows are omitted for LOW, while API 33+ and AVERAGE or HIGH exposes
   both. Record exact accessible labels and checked states; source inspection alone is
   insufficient.
3. Capture the baseline chat at a settled point with a patterned wallpaper visible immediately
   behind the composer and navigation surfaces. Preserve the same world, theme, viewport, scroll
   position, keyboard state and animation-settle rule for the comparison.
4. In that disposable package only, use `Force performance class` to select HIGH, then expand Chat
   in Power Usage and enable chat blur. Force-stop and cold-launch so `ChatActivity` reconstructs
   the blur3 objects, then capture the same chat and repeat the semantic assertions. Retain the
   resulting preferences and confirm `overrideDevicePerformanceClass=2` and that
   `lite_mode6 & 256 != 0`. This is the smallest useful chat-blur comparison; it changes no
   launcher default or APK.
5. Treat liquid glass as a separate comparison. With HIGH selected on API 36, enable its exposed
   Power Usage checkbox, cold-launch and capture a surface that actually wires the liquid-glass
   factory (the chat composer/navigation region is suitable). Confirm hardware acceleration and
   `lite_mode6 & 262144 != 0`. Do not infer success merely because the app did not crash.

For both comparisons, inspect the original PNGs. A pixel difference is supporting evidence only:
the enabled capture must show the expected background sampling/refraction at a named surface,
while the hierarchy and complete semantic history remain equal. A disabled control, unchanged
pixels or a software-rendering exception is useful negative evidence and should remain visible.
Afterward clear only this disposable package or discard its dedicated AVD; never promote its
preferences to the baseline profile.

## Development cost

The latest recorded complete Android gate contains 28 tests and takes about 21 minutes, while the
focused application probe has one guest boot and already retains launch, hierarchy and screenshot
evidence. Reusing that guest for baseline and enabled captures avoids a second boot and avoids an
APK rebuild because the comparison uses upstream settings. Static source/profile checks should run
before acquiring `android-gate`; if they fail, no scarce guest time is consumed. The full gate is
appropriate only after a production/profile change, which this investigation does not make.

## Remaining evidence

The baseline performance class, selected masks, power-saver state, hardware-accelerated blur3
execution and visual difference remain runtime-unverified. Any proposal to raise the default CPU
count, persist HIGH, inject app config or enable either effect belongs to the coordinator because
it changes the fidelity profile and may change runtime cost and screenshots.
