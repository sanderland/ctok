# ctok

**C**laude **T**okenizer **O**ffline, **K**inda — reproduces Claude's token *counts* with no API
call, no network and no dependencies.

Unofficial, not affiliated with Anthropic. Everything here was derived by probing `count_tokens`, so
counts are reproduced but token boundaries are approximate. Write-up [here](https://open.substack.com/pub/tokencontributions/p/on-the-biology-of-claudes-tokenizer
).

```python
from ctok import token_count, tokenize

token_count("hello, world")         # 10  — v3, the default
token_count("hello, world", 4.7)    # 15  — a different tokenizer family
token_count("hello, world", 5.0)    # 10  — v4.7's vocabulary, a smaller frame

tokenize("NASA likes tokenizers")   # token_count is len() of this
# ['⟨pad⟩' ×7, '⟨caps⟩⟨bow⟩nasa⟨eow⟩', '⟨bow⟩likes⟨eow⟩', '⟨bow⟩token', 'izers⟨eow⟩']
```

Tokens carry their structure in-line: `⟨bow⟩`/`⟨eow⟩` word boundaries, `⟨shift⟩`/`⟨caps⟩` case,
`⟨0xNN⟩` sub-character bytes, and `⟨pad⟩` for the single-message frame. There is a CLI too:
`ctok "hello, world"`.

## Versions

| version | family | reconstructs |
|---|---|---|
| `3.0` – `4.6` (default) | v3 | Claude 3 … Opus 4.5/4.6 |
| `4.7` – `4.9` | v4.7 | Opus 4.7 … 4.9 |
| `5.0`+ | v5 | Opus 5 — v4.7's vocabulary, v5's frame (see below) |
| anything else | — | `NotImplementedError` |

Versions are decimals, so `4.10` means 4.1. A model id also routes:
`token_count(text, "claude-opus-4-7")` — including `claude-sonnet-5`, which counts identically to
`claude-opus-5` on all 80 corpus texts it was checked against, frame and all.

All three families are reconstructed and gated; `token_count(text, 5.0)` works like `3.0` does.

**v5 reads the v4.7 vocabulary.** Its message frame is its own — `count_tokens` on a
one-character message is 7 tokens there against 12 on 4.7 — and so are the rules at that frame's two
edges: it right-strips trailing whitespace, and it ends in no word boundary, so a leading space costs
a token while an opening digit or ideograph does not. With those three facts measured, v5 scores the
*same number as v4.7 on every corpus below*, down to the same documents. No piece has been mined
against opus-5, and nothing measured says one differs.

## What the tokenizer change cost, by content

The v4.7 family is the one that changed: same text, more tokens. Measured here as the ratio of
recorded `count_tokens` values over the corpora below, content only, with the message frame removed:

| content | v4.7 ÷ v3 | v5 ÷ v3 | v5 ÷ v4.7 |
|---|---:|---:|---:|
| English web text | **1.44** | **1.44** | 1.00 |
| German web text | 1.39 | 1.39 | 1.00 |
| Code (Rosetta Code, 1,741 docs) | 1.22 | 1.20 | 0.99 |
| Code (MultiPL-E: Python 1.22, JS 1.27, Rust 1.29) | 1.24 | 1.23 | 1.00 |
| UDHR, 501 languages | 1.16 | 1.16 | 1.00 |
| Russian / Arabic / Hindi web text | 1.02 / 1.01 / 1.01 | same | 1.00 |
| Chinese / Japanese web text | 1.00 / 1.01 | 0.99 / 1.00 | 0.99 |

**The inflation is Latin-script-specific.** v4.7's vocabulary holds 14k word pieces against v3's 47k,
so Latin words fragment where they used to be whole; scripts that were already at the byte floor in
v3 — Cyrillic, Arabic, Devanagari, CJK — are unchanged. That is why a single "×1.4" figure travels
badly: it is an English number, and the same model reads ×1.00 on Chinese.

**v5 does not inflate again.** Its ratio against v4.7 is 1.00 on everything except CJK-opening lines,
where it is *cheaper* by a token per message — the frame rule above, not the vocabulary.

## Accuracy

Scored offline against recorded `count_tokens` values, all from committed fixtures: `uv run pytest`.

Two corpora are *parallel* — the same content in every language, so only the language varies. UDHR
is one declaration in 501 natural languages; [MultiPL-E](https://huggingface.co/datasets/nuprl/MultiPL-E)
is 25 HumanEval problems in 22 programming languages. The third is the opposite: real, unedited
[Rosetta Code](https://huggingface.co/datasets/christopher/rosetta-code) source in hundreds of
languages, which varies everything at once.

**Two of the three corpora are finished and have left the table.** Rosetta Code (1,741 documents)
and MultiPL-E (22 languages) reproduce *every* document exactly, on v3, v4.7 and v5 alike. They are
still gated — asserted at every document rather than at a rate, so the first regression names the
file it broke — but a row of zeroes is not a measurement, and keeping one invites reading a finished
corpus as evidence about an unfinished model. Code is done; what follows is about natural language.

| corpus | family | error mass | mean \|rel err\| | exact | within 1% |
|---|---|---:|---:|---:|---:|
| UDHR (501 languages) | v3 | 0.154% | 0.110% | 313/501 | 97.0% |
| UDHR | v4.7 | 0.073% | 0.064% | 361/501 | 98.0% |
| UDHR | v5 | 0.073% | 0.064% | 361/501 | 98.0% |
| Rosetta Code, held out (250) | v4.7 | 0.002% | 0.002% | 249/250 | 99.6% |
| Rosetta Code, held out (250) | v5 | 0.002% | 0.002% | 249/250 | 99.6% |

No document in either family is over 5% error. Fifteen v3 documents and ten v4.7 ones remain in the
1–5% band; the worst are Shipibo-Conibo (+4.38% / +3.14%) and Lamnso' (+3.27% / +2.84%), both
languages for which no marked-text source has been found. Weighted by speakers rather than by
document, the error is 0.059% (v3) and 0.032% (v4.7).

The one held-out Rosetta document that does not reproduce is a Swift file of Unicode escapes, where
a combining mark sits on U+25CC DOTTED CIRCLE. That is a question about how the stream spells a mark
whose base is not a letter, not a missing piece — [LIMITS.md](LIMITS.md) has the measurements and
says what is still open about it.

**UDHR and MultiPL-E are the held-out gates.** Nothing in the vocabulary is selected, accepted or
rejected because of them; they are read at the end of a campaign to find out whether it worked. Both
Rosetta samples are mining corpora — the 1,741 documents are what every campaign bisects against,
and the 250 are drawn from blocks that sample never touched, so the second rate is out-of-sample for
anything the first chose. A piece is accepted on a membership probe either way; the corpus only ever
decides which candidate gets asked.

Nothing in either family is over 5% off now; 15 in each were, before the akshara law (a mark that
closes its orthographic syllable also closes the word, so a conjunct is two words and carries the
boundary markers that say so). What is left is vocabulary rather than structure — the residual is
spread in both directions instead of being a one-sided under-count — and the largest remaining piece
of it is Brahmic and South-East Asian clusters that have not been mined. Measured on FineWeb-2, that
is the whole of the error: Thai and Tamil reproduce ~5% of documents against 99–100% for English,
German, Hindi and code, and carry 1.36% of the error mass against everyone else's 0.02%.

## What each piece rests on

The vocabulary is not a list of guesses. Every piece in `data/pieces_*.json` carries the probe that
put it there and the count that accepted it:

```python
from ctok import witness, pieces

witness("⟨bow⟩the⟨eow⟩", 4.7)   # {'probe': 'the', 'raw': 12, 'kind': 'raw'}
witness("ART⟨eow⟩", 4.7)         # {'probe': '.ヲART.', 'raw': 17, 'kind': 'eow'}
witness("e0a4", 4.7)            # {'probe': 'aऄa', 'raw': 15, 'kind': 'prefix', 'agree': 3}
len(pieces(4.7))                # 15297
```

`raw` is what `count_tokens` returned for that probe. One arithmetic turns it into the piece's own
cost, and the file carries the constants it needs in `meta.witness`:

```
cost = raw − base + 1 − overhead        is_token ⟺ cost == 1
```

`base` is `count_tokens` on the message `"a"` — one known token through the same frame — so every
template's `overhead` is calibrated against it and the surrounding material is never measured
separately. `kind` names the template:

| kind | probe for `X` | what it asks |
|---|---|---|
| `raw` | `X` | the piece is the whole message |
| `word` | `.X.` | a wordy span between Latin anchors |
| `bow` / `eow` / `mid` | `.Xヲ.` / `.ヲX.` / `.ヲXヲ.` | where in a word the piece sits — ヲ (katakana WO) was measured not to share a token across a script boundary |
| `cased_*` | `XController`, `československX` | material carrying a capital, which the ヲ bow probe over-reads |
| `char` | `aXa` | one non-ASCII codepoint's intrinsic cost |
| `glued` | `aXb` | an ASCII digit piece |
| `digit_*` | `1X1`, `a X1`, `1X a`, `a X a` | punctuation, symbols and whitespace runs, on digit anchors — a digit neither rides nor seams, where a Latin anchor would fuse into one punctuation run and ヲ would put punctuation against a letter |

A piece's marked form says which apply: `⟨bow⟩the⟨eow⟩` is a whole word, `⟨bow⟩TH` a prefix,
`izers⟨eow⟩` a suffix, `INT` word-interior. `ctok/witness.py` re-checks a recorded witness — that the
probe is that template, that the cost lands on 1, and that the encoder still writes the piece into
that probe — and `tests/test_witness.py` runs it over every witness in the file.

**Every piece in both files now carries one.** 48,557 on v3 and 15,297 on v4.7, with no piece left
at `unmeasured` (a template applies and nobody spent the API call), `no-instrument` (nothing in the
inventory reaches it) or `refuted` (its own probe priced it above one token). Four marker atoms are
`special` — `⟨bow⟩` is not text, so no probe can contain it — and that is the whole of what is not a
measurement. `tests/gates.py` reports the coverage per group, so a piece added without evidence shows
up as a gap rather than passing quietly.

Witnesses are measured against the family's own source model (`meta.witness.measured_on`). v5 shares
v4.7's file, so it shares its witnesses, measured on `claude-opus-4-7`.

## License

MIT
