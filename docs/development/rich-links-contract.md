# Structured rich link text

Status: core, independent bot/capture and focused original Android acceptance pass; combined
native inventory remains in progress.

Structured URL text is required by the first operational workflow. Add URL, email-address and
phone-number RichText values through the existing World/HTTP and original Android projection.
These nodes have the same recursive visible `text` shape and one string metadata field:

| Type | Required metadata | Original Android carrier |
| --- | --- | --- |
| `url` | `url` | `TL_iv.textUrl` with `webpage_id=0` |
| `email_address` | `email_address` | `TL_iv.textEmail.email` |
| `phone_number` | `phone_number` | `TL_iv.textPhone.phone` |

The pinned Bot API server decodes recursive text and a required string for these three nodes
([input](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12180-L12213))
and emits the same public metadata keys
([output](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L815-L860)).
Pinned TDLib recursively converts visible text and applies `clean_input_string` to each metadata
string; those branches do not impose URL, email or phone grammar validation
([conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L276-L309)).
Use the existing independently written [cleaner](rich-text-cleaning.md) within its documented
admission/size limits. Preserve empty and non-address strings as metadata rather than inventing
an address validator. Invalid Unicode, non-string/missing metadata and extra fields still reject
before mutation under the existing strict request profile.

The native types preserve recursive text, the exact cleaned metadata and the URL's absent cached
webpage identity ([URL/email](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L423-L455),
[phone](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L501-L518)).
Use the original rich-text renderer and independently round-trip its serializer. No upstream
implementation is imported into the MIT core.

## Boundaries and acceptance

Keep the current explicit `skip_entity_detection=True` requirement until its separate pipeline is
implemented. This increment is necessary for the operational workflow but does not by itself
make its default detection behavior compatible. Ordinary `text_link` entities, text mentions,
URL-action buttons, automatic detection, cached web pages and navigation remain separate work.
Storing link metadata does not authorize opening it or performing external requests. This contract
adds no network endpoint, route, SDK gesture or renderer replacement.

Compare complete World/HTTP send/edit/no-op, persistence/events/snapshots, text-to-rich transitions
and rejection atomicity with independently authored expected values. Use nested style/link nodes,
all three types, Unicode, metadata cleaning, empty strings and strings that are not addresses.
Capture matching must use only visible labels, never URL/email/phone metadata. Existing button
label restrictions and unknown-type rejection stay intact.

The coordinator owns a real-bot fixture plus canonical and adversarial native codec checks. Show
original bilingual/RTL rendering, live metadata/text edit and cold restart, with exact serialized
fields, original PNG/XML/report review and account-free offline isolation. Preserve the old
core/native rejection, one normal append-only GPL patch and unchanged original UI/resources.
No link navigation is exercised or claimed by those rendering checks.

## Integrated core evidence

The three recursive node types preserve metadata through World and JSON/form Bot API sends,
edits and persistence. Independent real-bot and public CLI captures compare complete state and
find visible labels while rejecting hidden destinations and text spanning separate fragments.
The combined rich-link/startup/polling/API selection passes 144 cases in 60.27 seconds after
verifying imports originate in the integration checkout. A prior run loaded another worktree
through a misdirected editable install and is retained as invalid integration evidence. Pytest
now rejects this condition before collection. The stale unknown-type test now uses `text_link`,
which remains unsupported, instead of the newly supported structured `url` type.

The full core gate passes 447 tests at 81.18% coverage in 104.55 seconds with Android excluded.
All 24 maintained static commands pass. No automatic detection,
navigation, media or custom-emoji support follows from the current core checks.

## Original Android evidence

Normal15 exposes a missing-field rejection defect after valid codec observations. A separate
append-only patch requires label and metadata before reading each link. Both failed runs remain
recorded; the corrected normal16 build passes offline in 1 minute 59 seconds and preserves the
original renderer/resources. Its two focused native tests pass in 135.98 seconds: complete
baseline plus 11 valid shapes and 29 exact malformed-shape rejections, then real-bot canonical
serialization, bilingual/RTL labels, live metadata/text edit and both cold-launch statuses.
Account-free component/network isolation assertions pass; no link is opened.

All three original PNGs were inspected. Desktop and mobile reports load three 320-by-640 images,
use millisecond timings and have no horizontal overflow or external resources. Embedded PNG
digests match the originals. The 43 remaining Android cases are running on the same immutable
normal16 APK after verifying all retained source, runtime-profile and import inputs. Combined
45-case acceptance is not yet claimed.
