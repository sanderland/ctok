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

| corpus | family | error mass | mean \|rel err\| | exact | within 1% |
|---|---|---:|---:|---:|---:|
| UDHR (501 languages) | v3 | 0.149% | 0.102% | 297/501 | 97.4% |
| UDHR | v4.7 | 0.075% | 0.068% | 311/501 | 98.4% |
| UDHR | v5 | 0.075% | 0.068% | 311/501 | 98.4% |
| MultiPL-E (22 languages) | v3 | 0.016% | 0.014% | 18/22 | 100% |
| MultiPL-E | v4.7 | 0.000% | 0.000% | 22/22 | 100% |
| MultiPL-E | v5 | 0.000% | 0.000% | 22/22 | 100% |
| Rosetta Code (1,741 docs) | v3 | 0.000% | 0.000% | 1740/1741 | 100% |
| Rosetta Code | v4.7 | 0.000% | 0.000% | 1741/1741 | 100% |
| Rosetta Code | v5 | 0.000% | 0.000% | 1741/1741 | 100% |
| Rosetta Code, held out (250) | v4.7 | 0.006% | 0.007% | 249/250 | 99.6% |
| Rosetta Code, held out (250) | v5 | 0.006% | 0.007% | 249/250 | 99.6% |

No document in either family is over 5% error. Thirteen v3 documents and eight v4.7 ones remain in
the 1–5% band; the worst are Shipibo-Conibo (+4.38% / +3.14%) and Lamnso' (+3.27% / +2.84%).
Weighted by speakers rather than by document, the error is 0.045% (v3) and 0.036% (v4.7).

**UDHR and MultiPL-E are the held-out gates.** Nothing in the vocabulary is selected, accepted or
rejected because of them; they are read at the end of a campaign to find out whether it worked. Both
Rosetta samples are mining corpora — the 1,741 documents are what every campaign bisects against,
and the 250 are drawn from blocks that sample never touched, so the second rate is out-of-sample for
anything the first chose. A piece is accepted on a membership probe either way; the corpus only ever
decides which candidate gets asked.

No document in either family is now more than 5% off; 15 in each were, before the akshara law (a
mark that closes its orthographic syllable also closes the word, so a conjunct is two words and
carries the boundary markers that say so).

## Where the residual actually is

Every corpus above is scored, not diagnosed: a gate says a document is wrong, never why. So the
questions are asked on **external** text instead — real corpora in the same languages, priced by
`count_tokens` directly — which is both sharper and the only way to touch a held-out gate's
languages without spending it.

Two things that reading fixed, and one it ruled out:

- **Rosetta's v3 tail was punctuation, not words.** 129 documents over-counted and none
  under-counted. Probing every distinct *word* of those documents found four disagreements in
  2,717; probing them line by line found `+:=`, `{:>14}`, `⟨bow⟩×⟨eow⟩`, APL glyphs, and long
  `-----` / `#####` rules whose run ladders were sampled with holes — a 40-hyphen rule tiled as
  32+8 where the oracle spends one token. 64 pieces took 1,612 exact documents to 1,740. v4.7's
  ladders were already complete: 7,833 rungs probed, none of them a token.
- **Brahmic and South-East Asian clusters were the UDHR residual, as the file said.** Glot500
  slices of thirteen languages, scored against the oracle, over-charge for Burmese, Odia, Tamil,
  Malayalam, Khmer, Lao, Thai and Hungarian. Those clusters usually open on a combining mark, so
  no template in the inventory can isolate one — an anchor becomes the mark's base — and they are
  mined and witnessed by ablation in natural text instead (`kind: "ownscript"`).
- **Shipibo-Konibo is not a vocabulary gap.** It is the worst document in both families, and the
  standing note said no marked-text source had been found. One exists: the PUCP corpus behind
  [Galarreta et al. (RANLP 2017)](https://doi.org/10.26615/978-954-452-049-6_033), shipped as the
  [AmericasNLP 2021](https://github.com/AmericasNLP/americasnlp2021) shared-task data — 15,588
  sentences. This tokenizer reproduces it **exactly**, in both families, and still does after
  transliterating it into the modern `w`/`k` orthography. Whatever the UDHR document costs, it is
  not Shipibo-Konibo vocabulary as either orthography writes it.

What is left is spread in both directions rather than being a one-sided under-count, and the
under-counting half is now the sharper one. It localizes: on Ewe, `ɔ` + U+0303 COMBINING TILDE
costs us one token less than the oracle, while U+0303 standing alone costs exactly the one token
its witness records. The mark is a token in one context and two bytes in another, which a
context-free tiling cannot express — the same shape as the held-out Rosetta document that costs
3 after a word boundary and 2 after a symbol's last byte. That is a model change, not a piece,
and it is what the remaining Dhivehi (−1.31%), Ewe (−0.44%) and Sinhala (−0.67%) readings are
made of.

## What each piece rests on

The vocabulary is not a list of guesses. Every piece in `data/pieces_*.json` carries the probe that
put it there and the count that accepted it:

```python
from ctok import witness, pieces

witness("⟨bow⟩the⟨eow⟩", 4.7)   # {'probe': 'the', 'raw': 12, 'kind': 'raw'}
witness("ART⟨eow⟩", 4.7)         # {'probe': '.ヲART.', 'raw': 17, 'kind': 'eow'}
witness("e0a4", 4.7)            # {'probe': 'aऄa', 'raw': 15, 'kind': 'prefix'}
len(pieces(4.7))                # 15549
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

Three kinds are gaps in the evidence rather than witnesses, and the file says which:

- `{"kind": "unmeasured"}` — a template applies and nobody has spent the API call yet.
- `{"kind": "no-instrument"}` — nothing in the inventory reaches this piece. Whitespace runs, bare
  punctuation and lone combining marks are the bulk of it.
- `{"kind": "refuted", "refused": [...]}` — its own allowed probe priced it above one token, with
  the reading kept. Those pieces are still shipped: what removes one is a campaign that re-judges the
  corpus, not an audit.

Witnesses are measured against the family's own source model (`meta.witness.measured_on`). v5 shares
v4.7's file, so it shares its witnesses, measured on `claude-opus-4-7`.

## License

MIT
