# Default automatic rich-text detection

Status: pinned input/output paths inspected; automatic enrichment rules remain unverified.
This is an operational requirement, not completed by explicit structured-link support.

The pinned Bot API decoder treats omitted `skip_entity_detection` as false and passes the inverse
to TDLib's `inputRichMessage`
([decoder](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12462-L12479)).
For structured blocks, TDLib converts the recursive input and sets `noautolink` to the inverse of
that detection flag. It forwards the blocks and flag in the server request
([conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/RichMessage.cpp#L89-L103),
[request](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/RichMessage.cpp#L285-L287)).
The retained implementation does not run the ordinary-text `find_entities` pipeline over those
blocks. Its ordinary-text parser cannot establish equivalent server-side RichText enrichment.

Explicit URL/email/phone, named-user mention and custom-emoji nodes survive as distinct wire
objects. Input mention/hashtag/cashtag/command/bank-card and internal automatic-link wrappers are
reduced to their child text on the outbound path
([input nodes](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L239-L321),
[wire conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L506-L573)).
On return, automatic URL/email/phone nodes become the public link shapes with metadata derived
from their recursive visible text
([output conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L704-L717)).
That conversion observes an already enriched result; it does not prove scanning grammar or scope.

## Evidence still needed

Compare complete output for omitted, false and true skip flags across these independent axes:

- URL/email/phone and mention/hashtag/cashtag/command/bank-card candidates, punctuation, invalid
  candidates, Unicode and Persian/English boundaries.
- Tokens inside styles or code, split across concatenated siblings or nested styles, and beside
  or inside explicit links, named-user mentions and custom emoji.
- Paragraphs/headings/footer/pre, quote text and credits, details summaries, table captions/cells,
  list text and button labels.
- Send/edit/no-op behavior, complete response/update shapes and persistence/native projection.

The retained sources establish neither code suppression nor cross-node token joining, precedence,
normalization, or per-block scanning. A global flag is not evidence of identical treatment for
every block role. Do not silently implement guessed rules and call them exact Telegram behavior.

No runtime/DC/account-backed observation is authorized. Independently supplied observations or
additional public primary evidence may reduce uncertainty. A documented local emulation policy
requires consultation before implementation because it changes the fidelity target. The current
explicit-skip requirement remains an honest limitation while other operational work proceeds.
