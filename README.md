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
| UDHR (501 languages) | v3 | 0.322% | 0.195% | 317/501 | 94.8% |
| UDHR | v4.7 | 0.163% | 0.105% | 443/501 | 96.4% |
| UDHR | v5 | 0.163% | 0.105% | 443/501 | 96.4% |
| Rosetta Code, held out (250) | v4.7 | 0.008% | 0.009% | 249/250 | 99.6% |
| Rosetta Code, held out (250) | v5 | 0.008% | 0.009% | 249/250 | 99.6% |

Two v3 documents and one v4.7 one sit over 5% — Tem (+6.23% / +6.08%) and, on v3 only, Maldivian
(+6.13%) — with 24 more v3 documents and 17 v4.7 ones in the 1–5% band; the worst of those are
Navajo (+4.86% / +4.41%), Shipibo-Conibo (+4.38% / +3.14%) and Lamnso' (+4.07% / +3.53%), languages
for which no marked-text source has been found. Weighted by speakers rather than by document, the
error is 0.063% (v3) and 0.030% (v4.7). Part of the UDHR residual is deliberate: the 2026-08-09
mark-eligibility work (LIMITS.md §11) converted under-counts in tone-marked orthographies into
honest over-counts, which moved several of these documents up the table rather than off it.

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

15 documents in each family sat over 5% off before the akshara law (a mark that closes its
orthographic syllable also closes the word, so a conjunct is two words and carries the boundary
markers that say so); one or two do now, and what is left is vocabulary rather than structure.

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
by itself. UDHR, which chose none of them, moved 365 → 448 documents exact in step.

**Bengali and Assamese were the two largest pools left, and ten pieces closed them** (LIMITS.md
§13). Both localize almost entirely inside single words — 99% and 98% on v4.7, 100% on v3 once
every word of every wrong row is priced rather than the top 4,000 — so this was vocabulary and not
structure. The whole of it is two facts about how the script is written down: `য়` is a composition
exclusion whose nukta closes the word from outside, which makes the Bengali `-ময়` suffix the piece
`ময⟨eow⟩`; and Assamese web text spells the vowel O in the pre-Unicode order `◌া◌ে`, which is one
token of its own. v3 needed four word-initial vowel signs on top, and two doubled signs that v4.7's
own probe refuses. Across the two languages, 2,000 Goldfish rows went from 1,913 wrong to 7 — and
UDHR, which chose nothing, gained its Bengali document in both families.

LIMITS.md records what the instruments can and cannot prove, including two pieces this campaign had
to *retract*: both were admitted on ablation witnesses that only looked convincing while the real
piece was missing.

**Under-count is nearly gone, and the last of it is listed rather than guessed at.** Across the
three replay corpora — 45 Goldfish languages, 43 Glot500 files and 242,188 rows of
FineWeb/Stack/github-code — under-count stands at **8 tokens in 302,418 rows**, from 18 on
2026-08-09. Both rules that closed the gap were the same kind of thing, and neither could be seen
from the Latin frames the model was mostly built on: a border ⟨eow⟩ that the seam deletes wherever
a ⟨bow⟩ follows the space, so only a right neighbour with no ⟨bow⟩ of its own — a CJK letter, an
ASCII digit run — can price it. One belongs to non-ASCII digit runs (`８ 取`, `文 ½ 文`), the other
to a word ending in a combining charging mark (`x ẹ̀ 2 x`), and the second was measured on a
15-host grid spanning nine scripts where the digit frame read exactly one below the letter frame in
every row. The gates were unmoved by both — Rosetta and MultiPL-E still reproduce every document,
and UDHR did not stir until the Bengali pieces above — which is the usual reading: the held-out
corpora hold almost none of the material these rules are about. [LIMITS.md](LIMITS.md) §12 carries
the eight that remain, each with the control that refutes its obvious explanation, and the Bengali
campaign after it left every one of them exactly where it was.

## What each piece rests on

The vocabulary is not a list of guesses. Every piece in `data/pieces_*.json` carries the probe that
put it there and the count that accepted it:

```python
from ctok import witness, pieces

witness("⟨bow⟩the⟨eow⟩", 4.7)   # {'probe': 'the', 'raw': 12, 'kind': 'raw'}
witness("ART⟨eow⟩", 4.7)         # {'probe': '.ヲART.', 'raw': 17, 'kind': 'eow'}
witness("e0a4", 4.7)            # {'probe': 'aऄa', 'raw': 15, 'kind': 'prefix', 'agree': 3}
len(pieces(4.7))                # 15150
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

**Every piece rests on a fixed template now.** The `ownscript` kind is gone. It had been introduced
to convert 1,560 `no-instrument` pieces — an honest declared gap — into witnessed ones, on the
premise that a combining mark cannot be put on a synthetic scaffold because the host becomes its
base. Half of that is true: on a *composing* host it is, and badly, since U+0301 between two `a`
costs nothing at all once NFC has made the probe say `á`. But a host that precomposes with nothing
works fine, and four of them — `ᛒ` `ꓘ` `ʣ` `ヲ` — agree with each other on every mark tried. So the
frame existed all along:

| kind | probe for `X` | overhead | what it asks |
|---|---|---:|---|
| `mark_mid` | `.ᛒXᛒ.` | 10 | a mark that stays inside its word |
| `mark_sep` | `.ᛒXᛒ.` | 12 | a mark that CLOSES its word, so the probe also gains an `⟨eow⟩` and a `⟨bow⟩` |

Which of the two applies is decided by `is_terminal_separator`, a property of the piece, never by
which number comes out. Both were controlled before anything was judged: fifteen known single tokens
must read 1 and spans nothing merges must read more. Three further frames were built and **discarded
because they failed that control** — `ᛒ` is not itself a single token, which cancels in the
`mid` anchor and does not at the word edges.

Asked on a fixed template, every `ownscript` record then resolved:

| | re-witnessed on a template | retired |
|---|---:|---:|
| v3 | 346 | 291 |
| v4.7 | 372 | 148 |

The 439 retired are pieces the vocabulary claimed as one token and whose own probe priced at two or
more. Five more went with them, under a rule rather than a measurement: **whitespace is either the
whole piece or not in it**. The stream absorbs a seam space into the following `⟨bow⟩` and spells
what it cannot absorb as its own run, so a piece holding a letter and a space is not a token — it is
standing in for an absorption the stream failed to perform, and it prices correctly only while
whatever follows happens to open a word. `tests/test_witness.py` now asserts it.

Both removals **cost real accuracy**: UDHR falls 448/501 → 439 → 430 on v4.7, and 314 → 310 → 307
on v3, because some of those pieces were load-bearing. A piece that is not a token cannot stay
because it happens to help; what it was hiding is now an honest over-count that can be mined.
Rosetta and MultiPL-E still reproduce every document.

Witnesses are measured against the family's own source model (`meta.witness.measured_on`). v5 shares
v4.7's file, so it shares its witnesses, measured on `claude-opus-4-7`.

## License

MIT
