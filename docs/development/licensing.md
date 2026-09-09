# Licensing boundaries

The root [MIT license](../../LICENSE) covers original GramLab scaffold/core/SDK work, not acquired
third-party code. The [root notice map](../../NOTICE) identifies the separately licensed components.
Python package metadata declares MIT AND BSL-1.0 and includes both license texts and the map. The Android patch queue now includes upstream context and retains its applicable
GPL terms with an accompanying license text. Full acquired source and generated binaries remain ignored.

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

## Image decoder dependency

The first photo profile pins Pillow 12.3.0 in the Python lock and the existing Nix input. The
installed package's license identifies Pillow/PIL under MIT-CMU and includes notices for bundled
codec dependencies. Preserve those notices when packaging the dependency; this does not relicense
third-party code under GramLab's MIT license. Local runtime uses the Nix dependency closure; host
wheel validation and distribution review are separate from Android's GPL boundary. No dependency
source is copied into the simulator and no binary distribution is authorized by this addition.

## Pinned emoji predicate reuse

Custom-emoji work reuses only TDLib's BSL-1.0 emoji membership data and predicate, independently of
the GPL Android adapter. The Python adaptation must retain its upstream copyright and the complete
Boost license in the module so a staged scenario supervisor receives those notices with the code.
That adapted module retains BSL-1.0; the root MIT license does not replace it. The accompanying
[license](../../LICENSES/BSL-1.0.txt) and [provenance](tdlib-emoji-provenance.json) pin exact source
hashes, scope and known generation limits. Preserve these notices in future packaging; no remote
publication or binary distribution is authorized. Predicate reuse supplies a documented local
coverage check, not evidence of production custom-emoji entitlement or server admission.


## Pinned document metadata reuse

The document filename/MIME helpers reuse TDLib's BSL-1.0 filename rules, Unicode predicates and
extension mapping at a pinned revision. The standalone adapted module retains the original
copyright and complete Boost license; its generated fixture directory also carries that license.
The [provenance](tdlib-document-metadata-provenance.json) identifies exact sources, hashes, generator
scope and independently executed C++ reference results. No GPL Android source/data enters these
Python helpers. Keep the notices with staged/distributed copies and preserve the distinction
between client-local metadata derivation and Telegram's unavailable server classification.
