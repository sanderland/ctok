# What this reconstruction cannot do yet

The README says how wrong the model is. This says *why*, for the parts that will not be fixed by
mining another piece — so a future campaign spends its API calls on something that can move, and so
a reader who hits one of these does not think it is new.

Everything here is a measurement with the probe that produced it. Nothing here is a guess about what
the tokenizer "probably" does.

## 1. Brahmic and South-East Asian clusters are the whole remaining error, and mining them makes it worse

Replayed against recorded counts on external corpora (FineWeb, FineWeb-2, the Stack, github-code —
none of them gates), documents reproducing exactly, v4.7:

| source | docs | exact | error mass |
|---|---:|---:|---:|
| FineWeb (English) | 200 | 100% | 0.000% |
| github-code C / Java | 388 | 100% / 100% | 0.000% |
| the Stack rust / python / perl | 289 | 100% / 99% / 98.9% | ≤0.012% |
| FineWeb-2 German | 200 | 99.0% | 0.001% |
| FineWeb-2 Hindi | 200 | 98.0% | 0.008% |
| FineWeb-2 Russian | 200 | 92.5% | 0.018% |
| **FineWeb-2 Thai** | 199 | **5.5%** | **0.640%** |
| **FineWeb-2 Tamil** | 200 | **5.0%** | **0.718%** |

Thai and Tamil carry 1.36% of the error mass against 0.02% for everything else combined. That is
where a campaign should go, and it is also where the instruments break.

**Measured, 2026-08-07.** A cluster campaign over 18,000 Thai and Tamil lines proposed seven pieces
— `ัง`, `ัน`, `ับ`, `ัก`, `ือ`, `ิน`, `ํา` — each accepted on the ヲ grid and each passing the shipped
`witness.verify`, placement check included. Applied:

```
without the seven   over-charge 17,728   under-count  3,784   total |err| 21,512
with the seven      over-charge 10,200   under-count 12,253   total |err| 22,453
```

They remove 7,528 tokens of over-charge and introduce 8,469 tokens of under-count. Every one is
individually well-witnessed and the batch is a net loss. They were discarded.

The obvious reading is that the scaffold is at fault: `.ヲXヲ.` supplies a katakana anchor that
becomes the cluster's base, and Thai does not put it there. So the campaign was re-run with the
scaffold removed entirely.

**The own-script instrument fails harder.** `witness._fitness_candidates` needs no anchor at all: it
takes a Thai line and its recorded count and enumerates, from the tiling DP, every single piece
whose addition would make that line reproduce. The probe is the Thai. Requiring at least two
independent lines to agree on exactly one piece — `_verify_fitness`, the strictest test in the
repo — yields 175 pieces from 1,200 lines. On 17,962 lines of FineWeb-2 Thai and Tamil:

| vocabulary | over-charge | under-count | total \|err\| | exact |
|---|---:|---:|---:|---:|
| shipped | 17,620 | 3,778 | 21,398 | 8,927 |
| + 99 own-script pieces (≤2 chars) | 10,108 | 85,759 | 95,867 | 6,415 |
| + 175 own-script pieces | 10,057 | **139,735** | 149,792 | 6,167 |
| + 7 ヲ-grid pieces | 10,200 | 12,253 | 22,453 | — |

**Read the over-charge column.** Three unrelated instruments — a katakana scaffold, an own-script
fitness proof, and a length-restricted subset of the same — all stop at ≈10,100 and cannot go
below it, while the under-count they create ranges over an order of magnitude. A missing-vocabulary
residual does not behave like that: the right pieces would drive over-charge toward zero without
manufacturing under-count. A piece that fixes one line and breaks thirty is not a piece the
tokenizer has; it is a patch over a tiling that is wrong somewhere else.

So the conclusion is the opposite of where this started. **Thai's residual is structural, not
lexical**, and roughly 10,000 of the 17,620 tokens of over-charge on this corpus are reachable by
vocabulary while the rest is not. Mining it is not merely difficult with the current instruments —
it is the wrong tool, and every instrument built so far says so by hitting the same floor.

The corollary is worth stating because it is tempting and wrong: *"every piece is witnessed, so a
document we over-charge must be missing a piece"* holds only if the structure is right. Witness
coverage certifies the vocabulary, not the encoder. Where the two disagree, this is how it shows.

## 2. An under-count cannot be mined away

Adding a piece only ever lowers our number, so a document we already count *below* the oracle is out
of reach of any vocabulary work. This is not a small residue: of the 21,512 tokens of absolute error
on those 18,000 Thai and Tamil lines, **3,784 were already under-count before a single piece was
proposed**. On UDHR the same shape shows as Evenki (−1.64%), Ditammari (−1.28%) and Assyrian
Neo-Aramaic (−1.16%), which sit among the worst documents in both families and cannot improve by
mining.

Those need a structural reading — a spelling, a boundary rule, a frame — not more vocabulary. The
useful consequence is a triage rule: **read the sign before spending API calls.**

## 3. Synthetic probes cannot settle a stream-spelling question

Two synthetic templates agreeing is not evidence, and neither is twenty-two.

**Measured, 2026-08-07.** Every combining mark in Unicode (2,450) was probed 22 ways and scored
against four candidate spellings crossed with two cost states, returning a verdict only where
exactly one combination reproduced every probe. For the 86 marks then under discussion the battery
was *unanimous*: the mark is an unmarked separator and not a token. Implemented and run on the
corpora, that spelling more than doubles UDHR error — 0.1403% against 0.0643% on v4.7, 0.1932%
against 0.1094% on v3.

The tell was visible before the corpora, in the battery's own output: the verdicts split about 2:1
*inside* single script blocks — Hebrew 31/15, Latin-combining 7/14, Philippine 14/15. A real law does
not split a script down the middle; a vocabulary artifact does. Two spellings that differ by one
token are decided by whichever one some piece happens to cover, and that is a property of the
vocabulary, not of the encoder.

The rule that survived instead came from asking what an engineer would plausibly have written —
`\p{L}\p{M}*`, so a mark is in the letter class only when a letter precedes it — and was then
checked on the corpora rather than on the grid. **Parallel corpora arbitrate; synthetic grids
propose.**

A related trap in the same family: `a{X}a` and `.ヲXヲ.` both supply their own anchor, and for a
combining mark that anchor BECOMES the mark's base. They are not independent evidence — they share
one bias and can agree on a reading that is wrong in the mark's own script.

## 4. Two UDHR documents are unexplained

Shipibo-Conibo (+4.38% v3, +3.14% v4.7) and Lamnso' (+3.27% / +2.84%) are the worst documents in
both families and nothing in this campaign touched them. Lamnso' has no reachable corpus at all —
eBible has no `lns`, Glot500 has no `lns`, the Wikimedia Incubator has no `Wp/lns`, and SIL's Bloom
Library has it behind a gate — so the question cannot be asked without spending the held-out gate.

## 5. Access and scale

- **StarCoder is gated.** `bigcode/starcoderdata` and `bigcode/the-stack-dedup` both require
  authentication. The external replay above uses `bigcode/the-stack-smol-xs` (same Stack lineage,
  open) and `codeparrot/github-code-clean` instead.
- **A 10M-document sweep is on the order of 200 hours of API time** at the throughput this
  sustains for documents of a few thousand characters. Any sweep at that scale has to resume from
  disk; it is not something one session finishes.
