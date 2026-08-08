# What this reconstruction cannot do yet

The README says how wrong the model is. This says *why*, for the parts that will not be fixed by
mining another piece — so a future campaign spends its API calls on something that can move, and so
a reader who hits one of these does not think it is new.

Everything here is a measurement with the probe that produced it. Nothing here is a guess about what
the tokenizer "probably" does.

## 0. Where the error actually is, over 350 languages

**Measured 2026-08-08, v4.7:** 350,000 rows of `goldfish-models/fish-food` — 1,000 rows from each of
its 350 languages, probed round-robin so every language is sampled equally, rows truncated at 4,000
characters. Two hours of API time. Nothing was mined against it; it exists to say where mining
should go.

```
all 350 languages   96.07% exact   error mass 0.0890%   over 17,756   under 20,950
minus syr_syrc      96.22% exact   error mass 0.0545%   over 17,560   under  5,811
```

**80% of all error is in 20 of the 350 languages**, and 59 languages reproduce every one of their
1,000 rows. Two facts do most of the steering:

**Syriac was the largest single defect, and the 2026-08-08 follow-up found its stream law.** In the
original sweep `syr_syrc` carried 15,139 tokens of under-count — 72% of all under-count in 350
languages — concentrated in long, diacritic-dense Peshitta rows. One 4,000-character row read 7,764
against a recorded 8,408. It now reads 8,408.

The shortest discriminating rows name two classes. U+0730–U+073F are ordinary Syriac vowel points:
`ܒܰܒ` stays one word and was already exact. Every mark in U+0740–U+074A instead stands outside the
word: `ܒ݁ܒ` and `ܒ݂ܒ` each cost two more than the old stream, while `ܒ݁ ܒ` costs one more because
the separator prevents seam-space absorption. A later vowel point rides the same unmarked mark run:
`ܒ݂ܶܒ` is exact without opening a stray marked word on `ܶ`.

There is a second, host-sensitive class. On a Syriac letter, every assigned mark in the existing
`CHARGING_MARK` range U+0300–U+0362 except U+0345 closes the run after the complete combining-mark
suffix. U+0345 and U+0363–U+036F do not. A complete block sweep on a noncomposing Latin host showed
that the newly found population does not close Latin runs. This is one script-host rule over an
already defined range, not 85 enumerated exceptions.

Five one-character pieces — U+0302, U+0303, U+0304, U+0327 and U+0331 — are pretoken-context
vocabulary. A six-host Latin grid gives at least three discriminating rows per mark and supports one
shared piece over per-pair explanations; standalone and Syriac-host rows byte-price them. The
existing forced-floor mechanism therefore keeps the pieces available in their measured Latin
context and blocks them on Syriac.

On the 100 Goldfish rows used to develop the rule, exact reproduction moved from 38 to 98, absolute
error from 1,551 to 4, and the worst row from −504 to −3. On a second frozen 100-row Goldfish draw,
exact moved from 42 to 97, absolute error from 1,479 to 3, and worst from −747 to +1. The compact
grid is exact in both v3 and v4.7. Neither UDHR nor MultiPL-E selected any part of the rule.

**The largest minable pools are not where the earlier sections of this file point.** Over-charge with
no under-count to confound it:

| language | exact | over-charge | error mass |
|---|---:|---:|---:|
| `ben_beng` Bengali | 28.3% | 2,251 | 0.794% |
| `asm_beng` Assamese | 31.5% | 1,901 | 0.570% |
| `aze_latn` Azerbaijani | 45.7% | 1,289 | 0.692% |
| `lmo_latn` Lombard | 43.3% | 1,086 | 0.816% |
| `bod_tibt` Tibetan | 75.0% | 605 | 0.116% |
| `tha_thai` Thai | 49.9% | 564 | 2.153% |
| `jpn_jpan` Japanese | 79.1% | 447 | 0.261% |
| `cat_latn` Catalan | 79.3% | 364 | 0.257% |

By script the over-charge is Latin 7,549, Bengali 4,497, Cyrillic 2,127, Tibetan 834 — so most of it
sits in scripts where the synthetic templates are known to work, and Bengali is a large Brahmic pool
that is clean (3 tokens of under-count against 2,251 of over).

**Thai is fourth, not first.** The section below reads as though Thai and Tamil were the whole
residual; they were the whole residual *of the eight corpora that happened to be on disk*. Azerbaijani,
Lombard, Catalan and Ossetian sit at 43–79% exact in reliable-template scripts and none of them has
been mined at all. That is the sampling error of §5 at the level of a whole campaign: **a corpus
chosen for convenience cannot rank the languages.**

### What that ranking bought, 2026-08-08

The Latin and Cyrillic pools above were then mined — 45 pieces, on Goldfish rows only. The step that
made it work was localizing first: pricing each WORD of an over-charging row alone, as its own
message. That said where the defect lived before any candidate was proposed, and it is worth doing
before a miner runs, because the answer differs by language:

| | over-charge inside single words |
|---|---:|
| `cat_latn` Catalan | 98% |
| `aze_latn` Azerbaijani | 71% |
| `lmo_latn` Lombard | **21%** |

Catalan and Azerbaijani are word-vocabulary problems and were mined out. Lombard is not — four
fifths of its error is in how words JOIN, so word pieces cannot reach it, and it remains the largest
over-charge left in this group at 854. Knowing that cost 3,000 API calls and saved mining the wrong
thing.

```
14,000 Goldfish rows, 14 languages    exact 79.9% -> 91.9%    error mass 5,122 -> 2,047
UDHR (held out, chose nothing here)   exact 365/501 -> 407/501
```

Per language, rows exact out of 1,000: `aze_latn` 457 → 993, `azj_latn` 700 → 1,000, `aze_cyrl`
858 → 1,000, `oss_cyrl` 763 → 989, `cat_latn` 793 → 990, `ron_latn` 786 → 972, `lmo_latn` 433 → 502,
`abk_cyrl` 932 → 949. Slovene, Hungarian, Bulgarian, Serbian, Yoruba and Mari were carried along as
controls and did not move — nothing bought here cost them anything.

The single most valuable piece was `ən`, an Azerbaijani schwa bigram that repairs 296 words on its
own; §6 records why an earlier version of the control refused it.

## 1. Unconstrained Brahmic/SEA fragment mining manufactures pieces

The measurements in this section are real and its lessons hold, but read §0 first for how much of
the error they cover. Replayed against recorded counts on external corpora (FineWeb, FineWeb-2, the
Stack, github-code — none of them gates), documents reproducing exactly, v4.7:

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

**Correction, 2026-08-08.** The inference from that batch to “the residual is structural” was too
strong. A candidate being one of the equal-cost explanations of two long lines is not a membership
proof, and judging 175 such candidates as one set hides genuine pieces among the false ones. A
candidate-by-candidate court exposed two ordinary Tamil suffix pieces at the virama/punctuation
seam: `்,⟨eow⟩` and `்.⟨eow⟩`. Six consonant bases, three placements and both families agree; the
parallel `? ! ; :` candidates are directly refuted. On the cached Thai/Tamil line set the two pieces
move v4.7 from 529/906 to 744/906 exact and total absolute error from 720 to 292; v3 moves 265/680 to
325/680 and 1,071 to 700. Some formerly exact lines become nonexact because this real token exposes
an independent under-count that the missing token had masked.

What the failed 175-piece batch establishes is narrower: **fitness on long natural text proposes a
piece but does not prove it**. A candidate still needs a minimal own-script grid and an individual
corpus court. Thai remains open after that stricter pass: the highest-scoring post-correction
candidate, `ึ⟨eow⟩้`, is refuted by a six-consonant grid whose rows are already exact without it.
There is not yet evidence that the remaining Thai residual is structural rather than lexical.

The corollary is worth stating because it is tempting and wrong: *"every piece is witnessed, so a
document we over-charge must be missing a piece"* holds only if the structure is right. Witness
coverage certifies the vocabulary, not the encoder. Where the two disagree, this is how it shows.

**Three courts, 2026-08-08, all empty — and where that leaves Thai.** With the candidate-by-candidate
method above, and its control that a candidate's probes must be WRONG without it:

| court | candidates | probes | kept |
|---|---:|---:|---:|
| virama × punctuation seam, every Brahmic script | 37 | 179 | **0** — every row already exact |
| Thai word-final letters | 30 | 227 | **0** — every row already exact |
| Thai word-final clusters, ≤3 characters | 3,245 | 20,344 | **0** — nearly all push some word BELOW |

The seam court independently reproduces Sol's refusal of the Tamil `? ! ; :` candidates, which is
the reassuring part: the control refuses the right things without being told about them.

The cluster court is where the useful correction is. `อ⟨eow⟩` repairs `คือ`, `ก็คือ`, `กือทือ` and
`กล่าวคือ` and takes `กอ` below the oracle — the four it repairs share `ือ`, and the single
character was the wrong span. Widening to three-character suffixes and demanding that no probe fall
below its recorded count leaves nothing at all: **every** word-final Thai cluster that repairs some
word breaks another.

And the reason is that Thai words are mostly not broken. Over 1,157 distinct Thai words priced from
the corpus:

    ours − api      −2: 1     −1: 62     0: 1,057     +1: 37

**91% exact, and the residual leans UNDER, not over.** Concatenating words into a single run tracks
the sum of the parts. So the Thai over-charge that shows on whole lines is not in Thai words, and a
word-piece campaign is looking in the wrong place — the material to examine is what surrounds them
on a line. (The hand-picked examples that suggested otherwise — `คือ`, `นักแสดง`, `สินค้า` — came
from a list of over-charging probes, so they over-charged by construction. A sample drawn from the
symptom cannot measure how common the symptom is.)

## 2. The span miner was blind, and is not any more

Worth recording because the symptom was indistinguishable from success: the miner proposed
candidates by MERGING adjacent tiles of the current tiling, which can only reach a span that begins
and ends on a boundary that tiling already chose. The pieces still missing are exactly the ones it
did not choose.

Two pieces already in the file demonstrate it. `a www b` tiles as a single `⟨bow⟩www⟨eow⟩`, so
`ww⟨eow⟩` is a SUB-span and no merge reaches it. `ododic` tiles `⟨bow⟩od` + `od` + `ic⟨eow⟩`, so
`odod` straddles a boundary and no merge reaches that either. Both were bought by other means and
neither could have been proposed by the generator that was running.

The fix is to propose every bounded span of the stream rather than every merge, and the check that
it worked is a **positive control**: hide a piece known to be real and confirm the loop buys it
back. `ww⟨eow⟩` and `odod` are both re-bought; `்,⟨eow⟩` is proposed and correctly reports that no
synthetic template can reach it.

With the generator fixed and that control passing, 28,000 candidates over 22,000 lines of Glot500
and FineWeb-2 yield **no new piece on either family**. That is now a measurement about the corpora
rather than about the tool: the 1,208 tokens of over-charge left on 570 lines are not reachable by
any span a shipped template can price at one token. **A miner that returns nothing should be made to
re-buy something known first** — otherwise "exhausted" and "blind" produce identical output.

## 3. An under-count cannot be mined away

Adding a piece only ever lowers our number, so a document we already count *below* the oracle is out
of reach of any vocabulary work. This is not a small residue: of the 21,512 tokens of absolute error
on those 18,000 Thai and Tamil lines, **3,784 were already under-count before a single piece was
proposed**. On UDHR the same shape shows as Evenki (−1.64%), Ditammari (−1.28%) and Assyrian
Neo-Aramaic (−1.16%), which sit among the worst documents in both families and cannot improve by
mining.

Those need a structural reading — a spelling, a boundary rule, a frame — not more vocabulary. The
useful consequence is a triage rule: **read the sign before spending API calls.**

## 4. Synthetic probes cannot settle a stream-spelling question

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

## 5. An ablation witness expires when the vocabulary grows, and can certify a piece that is not one

An `ownscript` witness says: delete this piece, and a real word of its own script costs one token
more. That is a sound argument only *relative to the rest of the vocabulary at the moment it is
measured*. If the piece the encoder actually uses is missing, deleting a longer composite of it
raises the count in exactly the same way — and the composite is recorded as a token it never was.

**Measured 2026-08-08.** Buying `ià⟨eow⟩` and `ən` on Catalan and Azerbaijani invalidated two
witnesses already in the file, and `tests/test_witness.py` caught both. Neither was merely stale:

```
xià⟨eow⟩   ownscript 'xià'    13 vs 14      direct probe '.ヲxià.'   cost 2   REFUTED
nə         ownscript 'ənənə'  15 vs 16      direct probe '.ヲnəヲ.'   cost 2   REFUTED
```

Both were retracted. `xià⟨eow⟩` was never a token; `ià⟨eow⟩` is, and it explains the same evidence.
The consequence for method: **an ablation witness is evidence about a vocabulary, not about the
tokenizer**, and it must be re-run — not merely re-read — whenever pieces are added near it. The
synthetic templates do not have this property, because they measure the span alone.

## 6. A true piece can push a word below the oracle, and that does not impeach it

This engine tiles by shortest path. The tokenizer it reconstructs merges in a fixed order, and the
two disagree on words that offer the same piece twice.

**Measured 2026-08-08.** `ən` is a verified Azerbaijani token — its own probe prices it at one, and
adding it repairs **296** standalone word counts. It also takes `cəhənnəm` one token *below* its
recorded count: that word contains two `ən`s, and shortest-path spends both where merge order did
not. No vocabulary change fixes this, in either direction.

So a push-below control has to be **net rather than absolute**. An absolute one — refuse the piece
if any word drops below — refused `ən` outright, and with it the single largest repair in the
Goldfish campaign: Azerbaijani sat at 45.7% of rows exact for one word out of ten thousand. The
control still earns its place; it is what refuses pieces that repair nothing and break something.
It just cannot be read as a proof of falsity when the witness is sound.

## 7. Two UDHR documents are unexplained

Shipibo-Conibo (+4.38% v3, +3.14% v4.7) and Lamnso' (+3.27% / +2.84%) are the worst documents in
both families and nothing in this campaign touched them. Lamnso' has no reachable corpus at all —
eBible has no `lns`, Glot500 has no `lns`, the Wikimedia Incubator has no `Wp/lns`, and SIL's Bloom
Library has it behind a gate — so the question cannot be asked without spending the held-out gate.

## 8. Access and scale

- **StarCoder is gated.** `bigcode/starcoderdata` and `bigcode/the-stack-dedup` both require
  authentication. The external replay above uses `bigcode/the-stack-smol-xs` (same Stack lineage,
  open) and `codeparrot/github-code-clean` instead.
- **A 10M-document sweep is on the order of 200 hours of API time** at the throughput this
  sustains for documents of a few thousand characters. Any sweep at that scale has to resume from
  disk; it is not something one session finishes.
