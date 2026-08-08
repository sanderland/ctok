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
| UDHR (501 languages) | v3 | 0.136% | 0.101% | 314/501 | 97.2% |
| UDHR | v4.7 | 0.052% | 0.042% | 448/501 | 98.2% |
| UDHR | v5 | 0.052% | 0.042% | 448/501 | 98.2% |
| Rosetta Code, held out (250) | v4.7 | 0.008% | 0.009% | 249/250 | 99.6% |
| Rosetta Code, held out (250) | v5 | 0.008% | 0.009% | 249/250 | 99.6% |

No document in either family is over 5% error. Fourteen v3 documents and nine v4.7 ones remain in the
1–5% band; the worst are Shipibo-Conibo (+4.38% / +3.14%) and Lamnso' (+3.27% / +2.84%), both
languages for which no marked-text source has been found. Weighted by speakers rather than by
document, the error is 0.046% (v3) and 0.016% (v4.7).

The one held-out Rosetta document that does not reproduce is a Swift file of Unicode escapes, where
a combining mark sits on U+25CC DOTTED CIRCLE — a stream-spelling question rather than a missing
piece. [LIMITS.md](LIMITS.md) records what is still open, and — more useful — what each instrument
can and cannot prove: the ヲ grid measures a Brahmic cluster on a base its script never uses, and
aggregate corpus fitness proposes a piece without proving one.

**UDHR and MultiPL-E are the held-out gates.** Nothing in the vocabulary is selected, accepted or
rejected because of them; they are read at the end of a campaign to find out whether it worked. Both
Rosetta samples are mining corpora — the 1,741 documents are what every campaign bisects against,
and the 250 are drawn from blocks that sample never touched, so the second rate is out-of-sample for
anything the first chose. A piece is accepted on a membership probe either way; the corpus only ever
decides which candidate gets asked.

Nothing in either family is over 5% off now; 15 in each were, before the akshara law (a mark that
closes its orthographic syllable also closes the word, so a conjunct is two words and carries the
boundary markers that say so). What is left is vocabulary rather than structure.

Where that vocabulary is missing was measured rather than guessed, by scoring 350,000 rows across
the 350 languages of [Goldfish](https://huggingface.co/goldfish-models) against `count_tokens`:
96.1% of rows exact, with 80% of the error in twenty languages and 59 languages perfect over a
thousand rows each. That ranking is in [LIMITS.md](LIMITS.md) §0, and it corrected the target twice
over — the error was not mainly Brahmic, and the single largest defect was Syriac, holding 72% of
all under-count.

Syriac was structural and is now implemented: its mark-run law took two independent 100-row samples
from 38/42 rows exact to 98/97, seven tokens of absolute error across all 200. What the sweep ranked
below it is ordinary missing vocabulary, and that is being mined a language at a time: **35
languages, 35,000 rows, 88.1% of rows exact to 95.6% on 100 pieces**, with eight of them now
reproducing 999 or 1,000 rows out of 1,000. The pieces are unremarkable — Catalan `-ància`/`-ències`
suffixes, Czech and Hungarian stems, and the Azerbaijani schwa bigram `ən`, which repairs 296 words
by itself. UDHR, which chose none of them, moved 365 → 448 documents exact in step. Bengali and
Assamese are the largest pools still untouched.

LIMITS.md records what the instruments can and cannot prove, including two pieces this campaign had
to *retract*: both were admitted on ablation witnesses that only looked convincing while the real
piece was missing.

## What each piece rests on

The vocabulary is not a list of guesses. Every piece in `data/pieces_*.json` carries the probe that
put it there and the count that accepted it:

```python
from ctok import witness, pieces

witness("⟨bow⟩the⟨eow⟩", 4.7)   # {'probe': 'the', 'raw': 12, 'kind': 'raw'}
witness("ART⟨eow⟩", 4.7)         # {'probe': '.ヲART.', 'raw': 17, 'kind': 'eow'}
witness("e0a4", 4.7)            # {'probe': 'aऄa', 'raw': 15, 'kind': 'prefix', 'agree': 3}
len(pieces(4.7))                # 15288
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

**Every piece in both files carries evidence, but not all of it is a template.** No piece is left at
`unmeasured` (a template applies and nobody spent the API call), `no-instrument` (nothing in the
inventory reaches it) or `refuted` (its own probe priced it above one token), and four marker atoms
are `special` because `⟨bow⟩` is not text. That leaves two tiers, and `tests/gates.py` reports them
apart:

| | on a fixed template | argued from natural text |
|---|---:|---:|
| v3 | 47,814 (98.64%) | 658 |
| v4.7 | 14,746 (96.45%) | 542 |

A template witness cannot be shaped to its piece: the probe string lives in `meta.witness.templates`,
`verify` requires the recorded probe to be *that* template applied to *this* piece, and the
arithmetic has to land on one token. The `ownscript` and `fitness` kinds are weaker — bespoke
per-piece arguments over natural text, an ablation delta or an intersection of tiling candidates,
each true only relative to the rest of the vocabulary rather than to the oracle alone. Asked on the
approved template their own marked form selects, **430 of the 1,094 that a template can reach are
refuted by it**. They are still counted, because the corpora say many are load-bearing — deleting
v3's 287 costs 27,000 tokens of error across 9,000 Brahmic rows — but they are not the headline
number. [LIMITS.md](LIMITS.md) §6 has the grid.

Witnesses are measured against the family's own source model (`meta.witness.measured_on`). v5 shares
v4.7's file, so it shares its witnesses, measured on `claude-opus-4-7`.

## License

MIT
