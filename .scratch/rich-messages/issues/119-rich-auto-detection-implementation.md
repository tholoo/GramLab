# Implement the approved offline rich-text scanner

Type: task
Status: ready-for-agent
Work state: resolved
Owner: rich-auto-detection
Blocked by: none

Implement the complete frozen policy in
[rich-auto-detection-proposal.md](../../../docs/development/rich-auto-detection-proposal.md).
Own `src/gramlab/rich_messages.py`, new focused World/Bot-API/round-trip tests and fixtures named
`*rich_auto_detection*`, `clients/android/patches/0031-rich-auto-detection.patch`, the Android patch
series/readme, and new codec/native probes and tests named `*rich_auto_detection*`. Do not edit
World storage, Bot API dispatch, album files, shared documentation or existing unrelated tests.

The coordinator additionally granted ownership of only the two obsolete omitted/false invalid
cases in `tests/test_rich_bot_api.py`; every other existing atomic-invalid case remains unchanged.

Before coding the five metadata-free generated node families, pin their exact original
`TL_textMention`, `TL_textHashtag`, `TL_textCashtag`, `TL_textBotCommand` and `TL_textBankCard`
projection from the locally retained reviewed Android source. Preserve existing URL/email/phone,
named-user mention and custom-emoji behavior. Omitted and false run detection; true remains
byte-for-byte compatible. Clean before scanning, scan only approved roles and string leaves, keep
code/pre/explicit nodes/button labels opaque, apply frozen boundary/precedence/normalization rules,
and enforce final depth/node/UTF-8 limits before publication.

Acceptance must independently cover every candidate family, invalid and near candidates,
punctuation, Unicode/Persian boundaries, every precedence pair, styles and opaque boundaries,
split siblings, all admitted text roles, send/edit/no-op/rollback/reopen/response/update equality,
and strict original-Android codec projection. Record a meaningful red before implementation, run
focused host/static checks, collect but do not run the Android case, and hand off a clean committed
branch. The coordinator owns APK construction and serialized native acceptance.

## Answer

Implementation is complete on the worker branch and remains claimed pending coordinator review and
integration. Omitted and false now clean and enrich each eligible string leaf; true preserves the
prior canonical output. The scanner implements the frozen eight-family grammar, stable overlap
ordering, Unicode/Persian word boundaries, punctuation/balance trimming, canonical URL/email/phone
metadata, Luhn validation, opaque author-controlled nodes, per-leaf/tree-role traversal and final
depth/node/UTF-8 validation. Candidate matching begins only at contract-valid boundaries, avoiding
quadratic searches on the maximum 34,996-byte plain leaf.

The locally retained pinned `TL_iv.java` defines the metadata-free recursive constructors exactly
as `textMention` (`0xcd24cf44`), `textHashtag` (`0x519524ea`), `textBotCommand`
(`0x02ff29d3`), `textCashtag` (`0x7b9e1801`) and `textBankCard` (`0xb956812d`). Patch 0031 maps the
five public canonical names to those original classes and makes `BridgeProbe` round-trip their
actual serialized types. A fresh 31-patch export applied with no fuzz or network access; its final
`GramLabRichMessage.java` and `BridgeProbe.java` SHA-256 values are respectively
`72b8b49eea428c1cc937f56b0f2fe9952f8738aa8c4b0cf57901ed28a077c0eb` and
`0058374a6a4a49e1778e091964ac93287b6fc0e699a490f3fd6b85f4892c9dfe`.

Regression evidence:

- red: `artifacts/rich-auto-detection-red-01.xml`, 86/86 focused cases failed before the behavior
  existed;
- final focused: `artifacts/rich-auto-detection-followup-focused-01.xml`, 183/183 passed with zero
  skips;
- exact final non-Android gate: `artifacts/rich-auto-detection-followup-core-01.xml`, 1,401/1,401
  passed with zero skips and 88.25% coverage;
- Ruff check/format and strict mypy pass for the owned production, host-test and Android-probe
  files;
- `tests/test_android_patch_stage.py` passes 15/15, a fresh local pinned-source preparation applies
  all 31 patches, and `tests/test_android_rich_auto_detection.py` collects exactly one Android case;
- no APK was built and no guest test was run, as required. The coordinator still owns compilation
  and serialized native acceptance.

The only existing-test edit removes the two obsolete omitted/false invalid examples from
`tests/test_rich_bot_api.py`, under the coordinator's narrow ownership grant; all other atomic
invalid cases remain. The coordinator also granted the narrow patch-queue README update. Shared
handoff, proposal status and compatibility records still require coordinator reconciliation after
integration.

Coordinator review correctly found that the original ordered-pair matrix demonstrated independent
left-to-right detections rather than overlap precedence. The follow-up names that matrix honestly,
adds public cases for every reachable nested-family URL overlap plus email/domain, phone/card and
same-start card/domain overlap, and factors selection into a non-mutating pure helper. Direct tests
prove earliest start, longest match and all 56 ordered cross-family equal-start/equal-length fixed-
priority ties. Such cross-family equal-length ties are unreachable under the frozen grammars:
leading syntax separates most families, email syntax cannot be a bare domain, and the only shared
digit-led bank-card/bare-domain start necessarily has different lengths. The synthetic pure-helper
matrix therefore pins the required deterministic fallback without making a false public-grammar
claim.

## Coordinator integration

The coordinator reviewed commits `ca0f96d` and `1bf5b3b`, including the corrected reachable-overlap
and synthetic fixed-priority evidence. The merged tree passes183 focused scanner/Bot-API cases,
15 Android patch-stage cases, strict typing and Ruff. Host behavior and patch0031 are integrated;
patch0031 is compiled into immutable normal31 and its original codec coverage passed in the
current-APK regression. The quoted-code rejection oracle was updated to retain the adapter's more
specific `GRAMLAB_BRIDGE_INVALID_CUSTOM_EMOJI` classification for an unsupported custom-emoji
entity; the exact Android case passed in `artifacts/normal31-failed-five-03.xml`. The APK was not
rebuilt.
