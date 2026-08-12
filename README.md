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

| content | v4.7 ÷ v3 |
|---|---:|
| English web text | **1.44** |
| German web text | 1.39 |
| Code (Rosetta Code, 1,741 docs) | 1.22 |
| Code (MultiPL-E: Python 1.22, JS 1.27, Rust 1.29) | 1.24 |
| UDHR, 501 languages | 1.16 |
| Russian / Arabic / Hindi web text | 1.02 / 1.01 / 1.01 |
| Chinese / Japanese web text | 1.00 / 1.01 |

**The inflation is Latin-script-specific.** v4.7's vocabulary holds 14k word pieces against v3's 47k,
so Latin words fragment where they used to be whole; scripts that were already at the byte floor in
v3 — Cyrillic, Arabic, Devanagari, CJK — are unchanged. That is why a single "×1.4" figure travels
badly: it is an English number, and the same model reads ×1.00 on Chinese.

**v5 does not inflate again**: 1.00 against v4.7 on everything here.

## Accuracy

Scored offline against recorded `count_tokens` values, all from committed fixtures: `uv run pytest`.

Two corpora are *parallel* — the same content in every language, so only the language varies. UDHR
is one declaration in 501 natural languages; [MultiPL-E](https://huggingface.co/datasets/nuprl/MultiPL-E)
is 25 HumanEval problems in 22 programming languages. The third is the opposite: real, unedited
[Rosetta Code](https://huggingface.co/datasets/christopher/rosetta-code) source in hundreds of
languages, which varies everything at once.

**Every code corpus is finished.** Rosetta Code — all 1,741 mining documents and all 250 held-out
ones — and MultiPL-E's 22 languages reproduce *every* document exactly, and are gated at every
document rather than at a rate so the first regression names the file it broke. What follows is
about natural language.

**v5 is not scored separately.** It borrows v4.7's vocabulary outright and differs only in its
message frame, so it lands on the same documents with the same errors;
`test_v5_tracks_v4_7_document_for_document` asserts that equality document by document instead.

| corpus | family | error mass | mean \|rel err\| | exact | within 1% |
|---|---|---:|---:|---:|---:|
| UDHR (501 languages) | v3 | 0.005% | 0.007% | 437/501 | 100% |
| UDHR | v4.7 (v5 borrows it) | 0.000% | 0.000% | 498/501 | 100% |

**No document in either family is over 1% off, and none under-counts** — not in these 501 documents
and not in any of the several million texts ever measured against either model. Weighted by speakers
rather than by document the error is 0.002% (v3) and 0.001% (v4.7). What is left is over-count:
ordinary missing word vocabulary, concentrated in v3, whose vocabulary is three times the size and
correspondingly harder to complete.

**UDHR and MultiPL-E are the held-out gates.** Nothing in the vocabulary is selected, accepted or
rejected because of them; they are read at the end of a campaign to find out whether it worked. Both
Rosetta samples are mining corpora — the 1,741 documents are what every campaign bisects against,
and the 250 are drawn from blocks that sample never touched, so the second rate is out-of-sample for
anything the first chose. A piece is accepted on a membership probe either way; the corpus only ever
decides which candidate gets asked.

Where the vocabulary is thin was measured rather than guessed, by scoring 350,000 rows across the 350
languages of [Goldfish](https://huggingface.co/goldfish-models) against `count_tokens`. That sweep is
what the mining is aimed at, and re-deriving it matters more than quoting it: the first ranking sent a
campaign at a pool a structural fix had already removed. A ranking is a measurement with a date on it.

[LIMITS.md](LIMITS.md) records what is out of scope, which inputs could still be counted wrong, and
what these numbers do and do not prove.

## Where the boundary markers go

Before anything is tiled, the text is cut into runs of a single class and the boundary markers are
written between them. **A word is the only run that is flanked unconditionally. Everything else is
marked only where it borders exactly one space.**

| run | `⟨bow⟩` on its left | `⟨eow⟩` on its right |
|---|---|---|
| **word** — letters and the marks inside them | always, unless a contraction apostrophe already opened it | always |
| **unattached mark run** — combining marks with no letter in front of them | always: the run is a word | unless a LETTER follows, which is not the next word but the rest of this one — it writes no `⟨bow⟩` either |
| **accent, virama, tone mark** — `is_killer`, the marks that stand outside the word | only against a single space, and only if BMP | only against a single space, and only if BMP |
| **punctuation, symbols, format characters** — including ZWSP and ZWJ | only against a single space, not where it opens a word, and only if BMP | only against a single space, and only if BMP |
| **digit run** | only against a single space, and only if the run's FIRST character is a BMP non-ASCII digit | only against a single space, and only if its LAST character is |
| **Han, Hangul, astral, whitespace** | never | never |

**Nothing astral takes a marker**, whatever its category — emoji, astral punctuation and format
characters, all 30 astral terminal separators and every astral digit, measured exhaustively over both
populations in both families.

Then one rewrite over the finished string: where `⟨eow⟩` stands immediately left of a space and
`⟨bow⟩` immediately right of it, **the space is deleted**. It is a single conjunctive rule — there is
no per-side "absorption", though the costs can be read that way.

The traps in "borders exactly one space" are all measured:

* **Message start counts; message end does not.** The frame ends in `⟨bow⟩`, and that `⟨bow⟩` *is* a
  space. There is no space after the last character.
* **A run of two or more spaces kills the marker**, uniformly over run lengths 2/3/4/17. A tab or a
  newline is not a space at all and never stands in for one.
* **The border CHARACTER decides, not the run.** `٥5` writes `⟨bow⟩` and no `⟨eow⟩`; `1？。 1` and
  `1 。？1` are one over if the run is judged whole, because the marker sits on the `？` side. The
  astral rule is per character for the same reason: `x a𑄴่ 5` and `x 𑄶５ 5` keep the `⟨eow⟩` their BMP
  last character earns, while `5 𑄴่a x` and `x ５𑄶 5` are one over with it written on the astral side.
* **A HARD run splits where the character kind changes** — punctuation, number, letter are different
  pretokens however our classifier grouped them, so `文？` gives `？` a run of its own.
* **Ideographic punctuation U+3001–U+303F takes no marker at all**, 25 of 25 — it is the block that
  predicts this, not the category, the width, or being sentence-terminal.

Only one side of most of these is observable at a time, which is why they were found so late: the
seam deletes an `⟨eow⟩` written before `space + ⟨bow⟩`, so any probe whose right neighbour opens a
word reads the same with the marker and without it. **Every one of these rules was settled on a
neighbour that opens no word** — an ideograph, or an ASCII digit.

## What each piece rests on

The vocabulary is not a list of guesses. Every piece in `data/pieces_*.json` carries the probe that
put it there and the count that accepted it:

```python
from ctok import witness, pieces

witness("⟨bow⟩the⟨eow⟩", 4.7)   # {'probe': 'the', 'raw': 12, 'kind': 'raw'}
witness("ART⟨eow⟩", 4.7)         # {'probe': '.ヲART.', 'raw': 17, 'kind': 'eow'}
witness("e0a4", 4.7)            # {'probe': 'aऄa', 'raw': 15, 'kind': 'prefix', 'agree': 3}
len(pieces(4.7))                # 15214
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
| `mark_mid` / `mark_sep` | `.ᛒXᛒ.` | a combining mark that stays inside its word / that closes it |

A piece's marked form says which apply: `⟨bow⟩the⟨eow⟩` is a whole word, `⟨bow⟩TH` a prefix,
`izers⟨eow⟩` a suffix, `INT` word-interior. `ctok/witness.py` re-checks a recorded witness — that the
probe is that template, that the cost lands on 1, and that the encoder still writes the piece into
that probe — and `tests/test_witness.py` runs it over every witness in the file.

**Every piece rests on a fixed template**, and coverage is 100% of both files — 48,431 pieces on v3
and 15,214 on v4.7, every one witnessed or, for the four marker atoms, declared structural. A
combining mark is asked on a *noncomposing* host (`ᛒ`, and `ꓘ ʣ ヲ` agree with it on every mark
tried), because a composing host turns the probe into a precomposed letter and prices that instead:
U+0301 between two `a` costs nothing at all once NFC has made the probe say `á`. Which of the two
mark templates applies is decided by `is_killer`, a property of the piece, never by which number
comes out; both were controlled in both directions before anything was judged, and fifteen known
single tokens must read 1 while spans nothing merges must read more.

Two rules the vocabulary is held to, both asserted by `tests/test_witness.py`:

* **Whitespace is either the whole piece or not in it.** The stream absorbs a seam space into the
  following `⟨bow⟩` and spells what it cannot absorb as its own run, so a piece holding a letter and
  a space is not a token — it prices correctly only while whatever follows happens to open a word.
* **A witness kind nobody has classified does not count as evidence.** The kind list is derived from
  each file's own `meta.witness.templates` plus the kinds `verify` names; anything outside it is
  reported rather than assumed.

Witnesses are measured against the family's own source model (`meta.witness.measured_on`). v5 shares
v4.7's file, so it shares its witnesses, measured on `claude-opus-4-7`.

## License

MIT
