# README preview

This is an unmodified screenshot from the actual Telegram Android renderer, patched for GramLab's
local test world. It shows a heading, bold and italic text, a quotation, an inline copy button and
callback buttons. The scene and interface are English. It does not show every supported feature.

Original glass effects were enabled through the client's settings. The capture run observed
`LiquidGlassEffect.update` on the main thread, retained the same conversation through baseline,
blur, glass and restored settings, and verified zero accounts and blocked external IPv4/IPv6.
The runtime was Android API 36, x86_64, at 320 by 640 pixels. The PNG has not been cropped or edited.

The synthetic conversation was captured with the 30-patch GramLab client based on Telegram Android
revision `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. APK SHA-256:
`a964bbaccaaf59719d966a72ecd85de4288d146887e3f7ff7d50be7281df726b`.
PNG SHA-256: `2c5023942d735dd474962a36ce50f41da98bf375912d4fc7acb9e8d50fd9adb7`.

Telegram Android's interface and artwork are upstream work, not original GramLab fixture art.
See the [upstream source](https://github.com/DrKLO/Telegram/tree/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c),
[patch license and notices](../../clients/android/patches/README.md),
[license text](../../clients/android/patches/COPYING) and [GramLab notice map](../../NOTICE).
This screenshot is a preview, not an Android binary distribution or an endorsement by Telegram.
