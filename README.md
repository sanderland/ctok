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

**Every code corpus is finished and has left the table.** Rosetta Code — all 1,741 mining
documents and, since 2026-08-10, all 250 held-out ones — and MultiPL-E's 22 languages reproduce
*every* document exactly, on v3, v4.7 and v5 alike. They are still gated, asserted at every
document rather than at a rate so the first regression names the file it broke, but a row of zeroes
is not a measurement and keeping one invites reading a finished corpus as evidence about an
unfinished model. Code is done; what follows is about natural language.

| corpus | family | error mass | mean \|rel err\| | exact | within 1% |
|---|---|---:|---:|---:|---:|
| UDHR (501 languages) | v3 | 0.188% | 0.098% | 338/501 | 97.8% |
| UDHR | v4.7 | 0.058% | 0.028% | 472/501 | 99.0% |
| UDHR | v5 | 0.058% | 0.028% | 472/501 | 99.0% |

**No v4.7 document is over 5% off any more, and one v3 document is** — Maldivian (+6.13%), which
this campaign did not touch. Tem, the worst document in both families for a month at +6.23% /
+6.08%, reproduces exactly, and so do Navajo, Lingala and Yoruba, with Shipibo-Conibo at +0.01%
and Lamnso' at +0.02%: the tone-marked orthographies that used to head this list are gone from it.
Ten v3 documents and five v4.7 ones remain in the 1–5% band and every one is Brahmic or SEA —
Thai (+3.96% / +2.66%),
Thai (2) (+4.33% / +2.38%), Burmese (+4.03% / +2.33%), Mon, Sinhala. Weighted by speakers rather
than by document the error is 0.058% (v3) and 0.025% (v4.7). What moved was the combining-mark
spelling: an accent closes its word BEFORE itself rather than after, which is one boundary marker
per accent across every decomposed and tone-marked orthography in the corpus (LIMITS.md §14).

The last held-out Rosetta document to fall was a Swift file of Unicode escapes where combining
marks sit on U+25CC DOTTED CIRCLE — a stream-spelling question rather than a missing piece, and it
was the mark spelling above that settled it. [LIMITS.md](LIMITS.md) records what is still open,
and — more useful — what each instrument can and cannot prove: the ヲ grid measures a Brahmic
cluster on a base its script never uses, aggregate corpus fitness proposes a piece without proving
one, and a mark grid on a byte-floored host cannot see where the mark's word ends (§14).

**UDHR and MultiPL-E are the held-out gates.** Nothing in the vocabulary is selected, accepted or
rejected because of them; they are read at the end of a campaign to find out whether it worked. Both
Rosetta samples are mining corpora — the 1,741 documents are what every campaign bisects against,
and the 250 are drawn from blocks that sample never touched, so the second rate is out-of-sample for
anything the first chose. A piece is accepted on a membership probe either way; the corpus only ever
decides which candidate gets asked.

15 documents in each family sat over 5% off before the akshara law (a mark that closes its
orthographic syllable also closes the word, so a conjunct is two words and carries the boundary
markers that say so); one v3 document does now and no v4.7 one does, and what is left is
vocabulary rather than structure.

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

**Under-count is down to one token, and it was a word boundary in the wrong place.** Across the
three replay corpora — Goldfish, Glot500 and 242,188 rows of FineWeb/Stack/github-code — v4.7
under-count stands at **1 token in 302,418 rows**, from 8 on 2026-08-09, and v3 at 5 in 286,856,
from 6. Over-count fell with it, by 2,156 tokens on v4.7, which is the unusual part: a boundary the
model was writing one character too late is a defect in both directions at once. Read over every
text ever measured against either family — a million rows, probe grids included, which is the
denominator the old figure was never taken over — under-count goes 5,206 → 489 on v4.7 and
885 → 209 on v3, and 4,169 and 685 of those rows respectively were fixed with none broken.

**A combining accent closes its word BEFORE itself, exactly as a virama does** (LIMITS.md §14).
Nine members of the U+0300 block used to close it after the mark and five others carried a
one-token piece with a tile-contextual eligibility rule; both were artefacts of an instrument that
could not see the difference. The old test ran on byte-floored hosts, where `⟨bow⟩H⟨eow⟩` and
`⟨bow⟩H` + `⟨eow⟩` cost the same and every mark reads "splits". On a host whose whole word is one
token they separate — `x q̊5 x` = 14 against the 15 an in-word mark charges — and the answer is
uniform: every codepoint of U+0300–U+0362 except U+0345 closes before itself, on 21 hosts spanning
thirteen scripts, in both families, with U+0345 and U+0363–U+036F pinning both ends of the range
from inside the same block. The same two frames over the other 418 combining marks of the BMP split
them the way orthography does and not the way Unicode does: accents, tone marks, cantillation and
annotation stand outside the word; vowel points and combining LETTERS stay inside it.

The vocabulary moved with it, in both directions. **U+0301 is a token** — `.ᛒ́ᛒ.` = 20 / 24, cost 1
on the shipped `mark_sep` template, with fifteen marks of the same block reading cost 2 as controls
— and it is the most frequent non-composing combining mark in written text. The five mark pieces
are not tokens: they were the in-word spelling wearing a piece, and they are gone. Yoruba goes 537 →
999 of 1,000 Goldfish rows exact, Abkhaz 949 → 992, and the four Glot500 tone-marked files that
were not exact now are.

The gates moved this time, which they usually do not: UDHR 317 → 338 exact on v3 and 443 → 472 on
v4.7, and the last held-out Rosetta document — the Swift file with a mark on U+25CC — came in, so
that corpus is 250/250. [LIMITS.md](LIMITS.md) §14 carries what is left: three marks our raw byte
floor over-prices at a stray run head, the dotted İ of §12.2, and three single rows.

## Where the boundary markers go

Before anything is tiled, the text is cut into runs of a single class and the boundary markers are
written between them. **A word is the only run that is flanked unconditionally. Everything else is
marked only where it borders exactly one space** — and that one rule, discovered separately for one
class of run after another, is where most of this reconstruction's errors have lived.

| run | `⟨bow⟩` on its left | `⟨eow⟩` on its right |
|---|---|---|
| **word** — letters and the marks inside them | always, unless a contraction apostrophe already opened it | always |
| **unattached mark run** — combining marks with no letter in front of them | always: the run is a word | unless a letter follows, which continues that word |
| **accent, virama, tone mark** — `is_killer`, the marks that stand outside the word | only against a single space | only against a single space |
| **punctuation, symbols, format characters** — including ZWSP and ZWJ | only against a single space, and not where it opens a word | only against a single space |
| **digit run** | only against a single space, and only if the run's FIRST character is a non-ASCII digit | only against a single space, and only if its LAST character is |
| **Han, Hangul, astral letters, whitespace** | never | never |

Then one rewrite over the finished string: where `⟨eow⟩` stands immediately left of a space and
`⟨bow⟩` immediately right of it, **the space is deleted**. It is a single conjunctive rule — there is
no per-side "absorption", though the costs can be read that way and an earlier draft of these
docs did.

The traps in "borders exactly one space" are all measured, and each of them has cost a campaign:

* **Message start counts; message end does not.** The frame ends in `⟨bow⟩`, and that `⟨bow⟩` *is* a
  space. There is no space after the last character.
* **A run of two or more spaces kills the marker**, uniformly over run lengths 2/3/4/17. A tab or a
  newline is not a space at all and never stands in for one.
* **The border CHARACTER decides, not the run.** `٥5` writes `⟨bow⟩` and no `⟨eow⟩`; `1？。 1` and
  `1 。？1` are one over if the run is judged whole, because the marker sits on the `？` side.
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
len(pieces(4.7))                # 15146
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

Which of the two applies is decided by `is_killer`, a property of the piece, never by
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
