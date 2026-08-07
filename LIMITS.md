# What this reconstruction cannot do yet

The accuracy tables in the README say how wrong the model is. This file says *why*, for the parts
that are not going to be fixed by mining another piece — so that a future campaign spends its API
calls on something that can move, and so that a reader who finds one of these does not think it is
new.

Everything here is a measurement, with the probe that produced it. Nothing here is a guess about
what the tokenizer "probably" does.

## 1. Some clusters under-count, and the cause is a stream-spelling question

Certain decomposed clusters cost the oracle more than we charge. The minimal case is Ewe's nasal
vowel, `ɔ̃` — U+0254 LATIN SMALL LETTER OPEN O followed by U+0303 COMBINING TILDE, which has no
precomposed form, so NFC leaves it decomposed:

| message | ours | `count_tokens` |
|---|---:|---:|
| `̃` (the mark alone) | 10 | 10 |
| `ɔ` | 11 | 11 |
| `ɔ̃` | 12 | **13** |
| `ɔ̃a` | 13 | **14** |
| `ã` (precomposed by NFC) | 9 | 9 |

(v3; v4.7 is the same shape at +4.)

**What this is not.** An earlier version of this file read that table as proof that a piece's cost
depends on what precedes it — that `̃` is one token standing alone and two after a byte-floor
character — and concluded no vocabulary could express it. That was a leap. A count mismatch says
the total is wrong, not which part of the model is wrong, and the obvious other suspect was never
ruled out: **where the boundary markers go**. A different stream spelling for a terminal mark
produces a different tiling with the same context-free costs, and that is a vocabulary-and-encoder
question, not a limitation of min-cost tiling.

That spelling is what PR #9 changes — a terminal orthographic mark becomes its own unmarked run
between the marked letter runs rather than the last character of the word before it. So this entry
records a *measured discrepancy* and defers the mechanism, instead of asserting one.

**Where it shows.** Scored against `count_tokens` on external Glot500 text, the languages that
under-count are Dhivehi −1.31% (v3), Sinhala −0.67% / −0.52%, Ewe −0.44% / −0.38%. On UDHR it is
28 documents on v3 and v4.7 alike, including Evenki (−1.65%), Ditammari (−1.28%) and Assyrian
Neo-Aramaic (−1.16%).

What is true regardless of mechanism: **mining cannot fix an under-count**, since adding a piece
only ever lowers our number. These documents need the spelling settled, not more vocabulary.

## 2. The case markers have no instrument

`normalize.mark_case` writes `⟨shift⟩` and `⟨caps⟩` as separate marker atoms, and the vocabulary
holds some pieces that begin with them (`⟨caps⟩⟨bow⟩nasa⟨eow⟩`). Whether a marker fuses with a
*single* following letter — whether `⟨shift⟩⟨bow⟩m` is one token — is not measurable with the
templates that exist.

The `cased_bow` template is `{}Controller`. For `M` it produces the message `MController`, which
returns 13 against a base of 12, i.e. cost 1. That looks like acceptance and is not: `MController`
is a single wordy run, so the encoder writes `⟨bow⟩MController⟨eow⟩` and the thing priced at one
token is `M` as a word-**interior** prefix. `witness.places` says so, which is why `witness.verify`
rejects the piece even though its arithmetic is clean.

**Cost of getting this wrong**, measured: a mining batch of 28 pieces, eighteen of them case-marker
pieces accepted on `cost == 1` alone, took UDHR v4.7's mean absolute error from 0.067% to
**0.394%** before it was rolled back. Running `witness.verify` on each candidate rejects all
eighteen.

Until a template exists that puts a case marker in front of a lone letter without an anchor
absorbing it, this question is open and the honest answer is that we do not know.

## 3. Greedy cluster mining is only as safe as its validation set

The cluster campaign accepts a piece when it takes some word's count down by one and takes no word
below the oracle's reading of it. The second condition is the important one, and it is only checked
against the words the campaign happened to price. A piece mined from Odia is never asked what it
does to Tamil, because no Tamil word had a recorded count on that family.

This is not hypothetical, and the demonstration is cheap. A corpus sweep over FineWeb and the Stack
proposed eight pieces from documents it over-charged; each one satisfied the guard against its own
sample. Re-checked against a validation set that included Thai, Odia, Khmer, Lao, Hungarian and
Tamil words, seven of the eight took **305** already-priced texts below their recorded counts, and
one broke the ablation witness of `วัน`, a piece that was already in the file. One survived.

The fix is not cleverer mining. It is to price the words of every language the pieces can reach
before accepting any of them, and to run `witness.verify` over the whole file afterwards — adding a
piece re-tiles the words *other* pieces are witnessed in, so a batch can leave every accuracy gate
green and still invalidate a witness.

A caution on reading the gate for evidence of this: UDHR Tamil sits at −0.55% on v4.7 and +1.56% on
v3, which looks like a campaign having pushed it past exact. It is not — Tamil read −0.55% on v4.7
*before* any cluster piece was mined, and the two numbers are different families, not a before and
after. The families disagree about Tamil on their own.

## 4. Two synthetic templates agreeing is not enough for a combining mark

Both `a{X}a` and `.ヲ{X}ヲ.` supply their own anchor, and for a combining mark that anchor BECOMES
the mark's base. So the two probes are not independent evidence about a mark — they share the same
bias, and they can agree on a reading that is wrong in the mark's own script.

Measured: a sweep of all 52,741 BMP characters the v4.7 byte floor charges two or more tokens for
found 513 that read cheaper on `a{X}a`. The ヲ grid rejected 471 of them, and fifteen survived both
at exactly one token. Three of those fifteen were Oriya vowel signs — U+0B3E, U+0B3F, U+0B47 — and
shipping them made real Oriya words count LOW against their recorded values, breaking a run of
Oriya ablation witnesses that had held before. Both templates had measured the mark sitting on a
Latin or katakana base, which is not where Oriya puts it.

For a mark, only natural-text ablation decides (`kind: "ownscript"`). The character sweep therefore
ships non-combining characters only: `µ`, `º`, `ａ` on v4.7 and `ａ` on v3.

The other trap in that sweep is NFC. Nine of the survivors were characters NFC normalizes away —
U+1F71 GREEK SMALL LETTER ALPHA WITH OXIA becomes U+03AC, U+212A KELVIN SIGN becomes `K`. The probe
measured the normalized form, so the piece would be one the encoder can never write.

## 5. Two UDHR documents have no reachable source

- **Shipibo-Conibo** (+4.38% v3, +3.14% v4.7 — the worst document in both families) is *not* a
  vocabulary gap, and this is now measured rather than assumed. The PUCP corpus behind
  [Galarreta et al. (RANLP 2017)](https://doi.org/10.26615/978-954-452-049-6_033), shipped as the
  [AmericasNLP 2021](https://github.com/AmericasNLP/americasnlp2021) shared task, has 15,588
  sentences of Shipibo-Konibo. This tokenizer reproduces them **exactly**, in both families,
  before and after transliteration into the modern `w`/`k` orthography. Whatever that document
  costs, it is not the language's vocabulary as either orthography writes it. Unresolved.
- **Lamnso'** (+3.27% / +2.84%) has no reachable corpus at all: eBible has no `lns`, Glot500 has no
  `lns`, the Wikimedia Incubator has no `Wp/lns`, and SIL's Bloom Library has it behind a gate.
  Without external text there is no way to ask the question without spending the held-out gate.

## 6. Access and scale

- **StarCoder is gated.** `bigcode/starcoderdata` and `bigcode/the-stack-dedup` both require
  authentication. The corpus sweep uses `bigcode/the-stack-smol-xs` (same Stack lineage, open) and
  `codeparrot/github-code-clean` instead.
- **A 10M-document sweep is ~215 hours of API time** at the ~13 documents/second this sustains for
  documents of a few thousand characters. The sweep is written to resume from disk for that reason;
  it is not something a single session finishes.
