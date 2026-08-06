# What this reconstruction cannot do yet

The accuracy tables in the README say how wrong the model is. This file says *why*, for the parts
that are not going to be fixed by mining another piece — so that a future campaign spends its API
calls on something that can move, and so that a reader who finds one of these does not think it is
new.

Everything here is a measurement, with the probe that produced it. Nothing here is a guess about
what the tokenizer "probably" does.

## 1. A piece's cost depends on what precedes it

This is the big one, and it is a *model* limitation, not a vocabulary gap.

`engine.tile` is a min-cost segmentation over a context-free vocabulary: every piece costs exactly
1, everywhere. That is false. The combining marks price differently depending on what they follow.

The minimal case is Ewe's nasal vowel, `ɔ̃` — U+0254 LATIN SMALL LETTER OPEN O followed by U+0303
COMBINING TILDE, which has no precomposed form, so NFC leaves it decomposed:

| message | ours | `count_tokens` |
|---|---:|---:|
| `̃` (the mark alone) | 10 | 10 |
| `ɔ` | 11 | 11 |
| `ɔ̃` | 12 | **13** |
| `ɔ̃a` | 13 | **14** |
| `ã` (precomposed by NFC) | 9 | 9 |

(v3; v4.7 is the same shape at +4.) The mark alone costs one token — that is exactly what the
shipped witness for the bare `̃` piece records, `{"probe": "̃", "raw": 10, "without": 11}`, and it
holds. After a byte-floor character it costs two. Our vocabulary holds one `̃` at one price and
uses it in both positions, so we under-count every such cluster by one.

The same shape is already recorded in `tests/gates.py` for the one held-out Rosetta document that
does not reproduce: a marked span that "costs 3 after a word boundary and 2 after a symbol's last
byte, which no single piece covers".

**Why no piece fixes it.** A piece is a (string → 1) entry. Expressing "this mark costs 1 here and
2 there" needs either a context-dependent cost function in the tiler, or a vocabulary that
enumerates every (preceding-context, mark) pair — and the second is not a vocabulary any probe in
the inventory can measure, because the templates supply their own left context.

**Where it shows.** Scored against `count_tokens` on external Glot500 text, the languages that
under-count are Dhivehi −1.31% (v3), Sinhala −0.67% / −0.52%, Ewe −0.44% / −0.38%. On UDHR it is
28 documents on v3 and 29 on v4.7 — including Evenki (−1.65%), Ditammari (−1.28%) and Assyrian
Neo-Aramaic (−1.16%), which have sat in the worst-20 list across several campaigns. On FineWeb the
aggregate sign is negative: a 550-document sample read 75.8% exact at a signed **−304** tokens.

Mining cannot touch any of it. Adding a piece only ever *lowers* our count.

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
below the oracle's reading of it. That second condition is only checked against the words the
campaign priced. A piece mined from Odia is never asked what it does to Tamil.

It does something. After the first cluster campaign, UDHR Tamil moved from +1.56% (v3) to −0.55%
(v4.7) — over-counting to under-counting, straight past exact. The fix is not cleverer mining, it
is a wider validation set: price the words of every language the pieces can reach, and drop
anything that pushes one below its recorded count. `scripts` for this live in the mining repo; the
shipped consequence is that a family's pieces are only as trustworthy as the breadth of text that
was priced when they were accepted.

## 4. Two UDHR documents have no reachable source

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

## 5. Access and scale

- **StarCoder is gated.** `bigcode/starcoderdata` and `bigcode/the-stack-dedup` both require
  authentication. The corpus sweep uses `bigcode/the-stack-smol-xs` (same Stack lineage, open) and
  `codeparrot/github-code-clean` instead.
- **A 10M-document sweep is ~215 hours of API time** at the ~13 documents/second this sustains for
  documents of a few thousand characters. The sweep is written to resume from disk for that reason;
  it is not something a single session finishes.
