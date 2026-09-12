# Implement the approved offline rich-text scanner

Type: task
Status: ready-for-agent
Work state: claimed
Owner: rich-auto-detection
Blocked by: none

Implement the complete frozen policy in
[rich-auto-detection-proposal.md](../../../docs/development/rich-auto-detection-proposal.md).
Own `src/gramlab/rich_messages.py`, new focused World/Bot-API/round-trip tests and fixtures named
`*rich_auto_detection*`, `clients/android/patches/0031-rich-auto-detection.patch`, the Android patch
series/readme, and new codec/native probes and tests named `*rich_auto_detection*`. Do not edit
World storage, Bot API dispatch, album files, shared documentation or existing unrelated tests.

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
