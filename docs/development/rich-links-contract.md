# Structured rich link text

Status: frozen implementation contract; not implemented or rendered yet.

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
