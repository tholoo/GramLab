# Licensing boundaries

The root [MIT license](../../LICENSE) covers original GramLab scaffold/core/SDK work, not acquired
third-party code. No Telegram code or assets are bundled in this scaffold.

Android-derived components must preserve the applicable upstream license and notices. Telegram
Android includes a [GPLv2 license](https://github.com/DrKLO/Telegram/blob/master/LICENSE); inspected
core source headers specify GPLv2-or-later. Do not apply the Web A GPLv3 assumption to Android, or
relicense copied/generated client-derived code as MIT. Audit per-file/dependency/asset terms.

Maintain an independently written simulator/SDK and a separately identified client-derived
adapter/application. A directory boundary or IPC connection alone is not a legal determination
about a combined distribution. Review actual dependencies and packaging before publication.

Before distributing client-derived artifacts, include applicable license texts, notices, source
and build/patch information and assess corresponding-source obligations. Audit fonts, emoji,
stickers, codecs and example media independently. Publicly accessible is not equivalent to a
redistribution license. Use original/deterministically generated fixtures where practical.

Follow upstream's [branding guidance](https://github.com/DrKLO/Telegram/blob/master/README.md):
identify GramLab as unofficial and use distinct app branding. Do not reuse Telegram's standard
logo as GramLab's logo. Preserve in-chat rendering fidelity without implying affiliation.

consumer application informed the quality principles and initial tooling choices. Its runtime code,
credentials, game assets and deployment scripts have not been copied or relicensed here.
