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
residual; they were the whole residual *of the eight corpora that happened to be on disk*.
Azerbaijani, Lombard, Catalan and Ossetian sat at 43–79% exact in reliable-template scripts and none
of them had been mined at all. That is §1's own sampling error — a sample drawn from the symptom
cannot measure how common the symptom is — repeated at the level of a whole campaign: **a corpus
chosen for convenience cannot rank the languages.**

### What that ranking bought, 2026-08-08

The Latin, Cyrillic and Arabic-script pools above were then mined — **90 pieces over 33 languages,
on Goldfish rows only**. The step that made it work was localizing first: pricing each WORD of an
over-charging row alone, as its own message. That says where the defect lives before any candidate
is proposed, and it is worth doing before a miner runs, because the answer differs by language:

| | over-charge inside single words |
|---|---:|
| `cat_latn` Catalan | 98% |
| `aze_latn` Azerbaijani | 71% |
| `lmo_latn` Lombard | **21%** |

Catalan and Azerbaijani are word-vocabulary problems and were mined out. Lombard is not — four
fifths of its error is in how words JOIN — and §2 below says what it turned out to be.

```
33,000 Goldfish rows, 33 languages     exact 88.2% -> 96.1%    over-charge 6,686 -> 2,380
UDHR (held out, chose nothing here)    exact 365/501 -> 448/501
```

Eight of the 33 now reproduce 999 or 1,000 of their 1,000 rows: `azj_latn`, `aze_cyrl`, `chv_cyrl`,
`bug_latn`, `slv_latn`, `srp_cyrl`, `kjh_cyrl`, `tam_latn`. The largest movers were `aze_latn`
457 → 993 rows exact, `oss_cyrl` 763 → 989, `cat_latn` 793 → 990, `ron_latn` 786 → 972.

**Five languages did not move, and that is the useful part of the reading.** `srp_latn` (101),
`snd_arab` (65), `knc_arab` (148), `glk_arab` (118) and `yor_latn` (173) each kept essentially all
their over-charge across two mining rounds. The Arabic-script three are one group and worth a
campaign of their own: the miner priced their words, found them wrong, and could not propose a span
any shipped template would accept — the same shape as the Brahmic wall in §1, in a different script.

The single most valuable piece was `ən`, an Azerbaijani schwa bigram that repairs 296 words on its
own; §8 records why an earlier version of the control refused it.

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

## 2. A span that mixes a HARD character with a space or a stop has no template

Lombard was the one language in the campaign where localizing said *don't mine this* — only 21% of
its over-charge was inside a word — and shrinking its wrong rows to minimal failing substrings
returned, over and over, two strings three characters long: `².` and `² e`.

**Measured 2026-08-08.** U+00B2 SUPERSCRIPT TWO costs exactly one token too many whenever a space or
a punctuation mark follows it, and nothing at all otherwise:

```
a²   +0     a².  +1     a² b  +1     a²a  +0     km²  +0     km² e  +1     km². E  +1
a³   +0     a³.  +0     a³ b  +0        ¹ ½ ¼ ¾ ⁴ ₂ read +0 in every one of those frames
```

It is not a class rule: `³ ¹ ½ ¼ ¾ ⁴ ₂` share `²`'s category (`No`) and its HARD class and are exact
in the same frames, so this is a vocabulary difference, the same shape as the `±`/`©`/`®` note in
`normalize._is_symbol_text`. Nor is it a stream rule about absorbing the space: absorbing it would
take `a³ b` *below* its recorded count.

The fitness enumerator names the missing pieces — `² ` and `².` — and no shipped template can price
either. `²` is HARD, a space and a full stop are not, and `mine_stream.probe_of` refuses mixed
material because no template owns it: the ヲ grid would put a letter against it, and the digit
anchors would read a punctuation run. So this is a **no-instrument** gap rather than an unmined one.

It is also the whole of Lombard's residual, which is what makes it worth a section. 859 occurrences
of `²` followed by a space or a stop in 1,000 rows, against 854 tokens of remaining over-charge.
There is a second, uniform fact in the same grid: *every* `No` character over-charges by one in
`1X  1`, a space RUN, where the other classes do not. That one is class-level and looks like a rule,
but a superscript before a double space is rare enough in real text that it buys nothing.

## 3. The span miner was blind, and is not any more

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

## 4. An under-count cannot be mined away

Adding a piece only ever lowers our number, so a document we already count *below* the oracle is out
of reach of any vocabulary work. This is not a small residue: of the 21,512 tokens of absolute error
on those 18,000 Thai and Tamil lines, **3,784 were already under-count before a single piece was
proposed**. On UDHR the same shape shows as Evenki (−1.64%), Ditammari (−1.28%) and Assyrian
Neo-Aramaic (−1.16%), which sit among the worst documents in both families and cannot improve by
mining.

Those need a structural reading — a spelling, a boundary rule, a frame — not more vocabulary. The
useful consequence is a triage rule: **read the sign before spending API calls.**

## 5. Synthetic probes cannot settle a stream-spelling question

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

## 6. `ownscript` is retired: there was a frame for combining marks all along

`ownscript` was a bespoke per-piece argument — delete this piece and a real word of its own script
costs one token more — and it existed because of one sentence: "combining-mark pieces cannot be
moved onto the Latin/Katakana witness scaffolds: the host becomes the mark's base and the probe asks
about a different cluster." It was introduced in `3dafb2b` and converted **1,560 `no-instrument`
records** — an honest declared gap — into witnessed ones, which is how the file reached 100%.

**The premise is half true and the conclusion does not follow.** Measured 2026-08-08 with a
differential that needs no template constant, `delta(H, X) = count(".HXH.") - count(".HH.")`:

```
host          a    e    o  |  ᛒ    ꓘ    ʣ    ヲ
U+0301        0    0    0  |  3    3    3    3
```

On a *composing* host the objection is real and large — U+0301 between two `a` costs nothing,
because NFC has turned the probe into `á` and you are pricing a precomposed letter. On a host that
precomposes with nothing it evaporates, and all four such hosts agree on every mark tried. The
frame existed; nobody had looked for it.

Controls matter more than the frame here, and they killed three of the four candidate templates.
`.ᛒ{}ᛒ.` passes — fifteen known single tokens read 1, spans nothing merges read 3 or 4 — while
`.{}ᛒ.`, `.ᛒ{}.` and a derived `.{}.` overhead each read **0 of 15** and were discarded. `ᛒ` is not
itself a single token, which cancels in the two-sided anchor and does not at a word edge. Without
those controls all three would have looked like instruments.

**One correction the controls did not catch, and the corpus did.** A mark that closes its own word
does not sit inside the frame the way the anchor does:

```
probe   ⟨bow⟩.⟨bow⟩ᛒ⟨eow⟩்⟨bow⟩ᛒ⟨eow⟩.
anchor  ⟨bow⟩.⟨bow⟩ᛒᛒ⟨eow⟩.
```

It adds an `⟨eow⟩` and a `⟨bow⟩` on top of itself, so a real token reads **3**, not 1 — and 23 of
the 24 word-closing marks read exactly 3. Read as refutations, they made every virama in the file
look false. Leave-one-out on the mining corpus is what exposed it: four of them — Tamil, Sinhala,
Malayalam and Myanmar — were worth **21,580 tokens**, against 129 for all the other v4.7
refutations combined. Hence two kinds sharing one probe string, `mark_mid` (overhead 10) and
`mark_sep` (overhead 12), chosen by `is_terminal_separator` rather than by which number comes out.

The outcome, with every record re-asked on a fixed template:

| | re-witnessed | retired |
|---|---:|---:|
| v3 | 346 | 291 |
| v4.7 | 372 | 148 |

**The 439 retired cost real accuracy and went anyway.** UDHR falls 448 → 439 on v4.7 and 314 → 310
on v3; leave-one-out priced the whole v3 set at 4,159 tokens on the mining corpus. A piece the
measurement calls two tokens cannot stay because it happens to help — what it was masking is now an
honest over-count, which is a thing that can be mined. Rosetta and MultiPL-E still reproduce every
document: one Rosetta file did break, and came back when the single-codepoint retirements were
re-asked on the `char` template (`a{}a`) instead of the ヲ grid, which is the right frame for one
codepoint and reads 1 where ヲ reads 3.

Three lessons worth more than the pieces:

* **A "no instrument" claim is a claim, and it needs the same evidence as a measurement.** This one
  stood for two days over 1,560 pieces and was refuted by seven probes.
* **Control every frame in both directions before judging anything with it.** Three of four here
  were wrong, and the wrong ones fail silently — they return numbers.
* **An ablation witness is evidence about a vocabulary, not about the tokenizer**, so it expires
  when the vocabulary grows. `_verify_ownscript` asserted two things: `without_n == raw + 1`, which
  is vocabulary-relative, and `with_n == raw`, which compares against a recorded `count_tokens`
  value and is not. Only the first can expire; the second failing means the model has begun counting
  a real message *below* the oracle. Of thirty Thai witnesses invalidated by buying `ิน`, 17 were
  the second kind.

## 7. Where the under-count comes from, now that the false pieces are gone

Retiring `ownscript` took under-count across 44 Goldfish languages from thousands to **789**, and
what is left is concentrated in six: Malayalam 188, Khmer 180, Lao 119, Tamil 94, Myanmar 76,
Sinhala 74. Under-count should be impossible — the tiler takes a shortest path over a vocabulary
meant to be a SUBSET of the real one — so each case is one of three things, and they need different
fixes: a false piece, a missing boundary, or merge order (§8).

**Most of it is five real pieces applied one character too far.** The vocabulary holds five
`virama + space` pieces — Devanagari, Tamil, Malayalam, Sinhala and Myanmar. They are not junk;
removing them is catastrophic, because a terminal separator blocks seam-space absorption and these
are what pay for the space it leaves behind:

| | exact, with the five | without them |
|---|---:|---:|
| `mal_mlym` | 877 | 164 |
| `tam_taml` | 479 | 58 |
| `sin_sinh` | 598 | 89 |
| `mya_mymr` | 950 | 504 |

But removing them also takes Malayalam's under-count from 188 to 8, Tamil's 94 to 0 and Sinhala's 74
to 0. So they are real pieces used in a place the tokenizer does not use them, and the place is
measured:

```
x ക് ക x   +0   separator, space, LETTER
x ക് 5 x   -1   separator, space, DIGIT
x ക  5 x   +0   no separator            <- control
x .  5 x   +0   punctuation, space, digit <- control
x ക് , x   +0   separator, space, punctuation
```

The reason is that **a digit run absorbs no adjacent space, on either side**, where a word does:

```
a b      2 content tokens   ⟨bow⟩a⟨eow⟩ · ⟨bow⟩b⟨eow⟩      the space is absorbed into the ⟨bow⟩
a 5      3                  ⟨bow⟩a⟨eow⟩ · ␣ · 5            it is not
5 a      4                  ⟨bow⟩ · 5 · ␣ · ⟨bow⟩a⟨eow⟩     nor on the other side
998 999  4                  ⟨bow⟩ · 998 · ␣ · 999           a digit run opens with ⟨bow⟩, closes with nothing
```

So the space next to a digit is not part of anything — it stands alone and costs a token — which is
precisely why it is still there for the glue piece to swallow:

```
x ക് 5 x   api 19   ours 18
  ours    ⟨bow⟩x⟨eow⟩ · ⟨bow⟩ · ക⟨eow⟩ · `് ` · 5 · ␣ · ⟨bow⟩x⟨eow⟩    = 7
  oracle  ⟨bow⟩x⟨eow⟩ · ⟨bow⟩ · ക⟨eow⟩ · ്   · ␣ · 5 · ␣ · ⟨bow⟩x⟨eow⟩  = 8
```

With a letter after the space instead, the glue produces the right total: `x ക് ക x` reads 7 with it
and 8 without, and 7 is recorded. **But it produces it for the wrong reason**, and the probe says so:

```
.ᛒ्ᛒ.    24        the bare virama
.ᛒ् ᛒ.   24        the virama and a space — IDENTICAL
.ᛒ्  ᛒ.  25        a space run is not absorbed
```

The space costs nothing when a letter follows, because the oracle absorbs it into the next `⟨bow⟩`
like any other seam — and `_seam_sub` exempts terminal marks from exactly that. So the space was
never a token, the `virama + space` piece is a modelling device standing in for an absorption the
stream does not perform, and the `mark_sep` witness attached to it during the `ownscript` retirement
is degenerate: it cannot tell `्` from `् `, so it certifies the bare virama and says nothing about
the pair. The same failure as `xià⟨eow⟩` in §6, found by asking the question one level lower.

The five are now gone, under a rule rather than a per-script judgement: **whitespace is either the
whole piece or not in it**, asserted by `tests/test_witness.py`. Whether the space is absorbed does
vary by script, and the correlation with the glue pieces is exact —

| | bare | + space | absorbed? | had a glue piece? |
|---|---:|---:|---|---|
| Devanagari, Tamil, Malayalam, Sinhala, Myanmar | 3 | 3 | yes | yes |
| Khmer, Thai, Lao | 3 | 4 | no | no |

— but that table is a *symptom*, not a rule, and it must not be written into the encoder. Five
scripts absorbing and three not is eight data points; an allowlist built from them would be the
fitted special case this file exists to warn about (§1, §5), dressed up as a law. **The rule that
produces that split is not known.** What the split does establish is that the glue pieces were never
independent of it: nobody chose which scripts got one, it fell out of fitting the corpus.

So the pieces are gone and the compensating stream rule is *not* invented in their place. UDHR pays
for it — 439/501 → 430 on v4.7, 310 → 307 on v3 — and the residual is now an honest over-count in
the scripts that used to absorb, which is a thing that can be measured and mined rather than a
number that happened to come out right.

357 such sites sit in these corpora against 733 tokens of under-count, and the count overshoots in
Tamil and Sinhala because some rows also over-charge and the two cancel.

**Khmer and Lao are NOT this**, and the table above says why: their separator does not absorb the
following space, so they never needed a glue piece and have none. Together they are 299 of the 733,
and ablating all five moves neither by a token. Their under-count is a separate mechanism and has not
been found — but it is now known not to be this one, which is worth more than it sounds.

Two instrument notes, both learned by getting it wrong here first:

* **Shrinking a failure to a bare substring puts it against the message edge, and the edge has its
  own rules.** Unpadded, this search "found" that a terminal separator followed by one trailing
  space under-counts — true, reproducible in six languages, and the explanation for none of the
  corpus: not one under-counting row ends that way. Every measurement above is taken inside fixed
  padding.
* **A mechanism that explains the shrunk case still has to be counted at corpus scale.** The first
  padded reading said the fault was the glue piece used twice consecutively — which is real, and
  covers 4 of 733.

### The rule the glue pieces were standing in for

**Measured and implemented 2026-08-08.** The pieces were compensating for a class of character the
stream builder never gave boundary markers to. ZWSP is category **Cf**, not a terminal separator —
`is_terminal_separator(U+200B)` is False — and it reaches `classify` with no branch of its own, so
it falls through to HARD, which writes no markers at all. It is also the word separator of Khmer and
Lao, which is why those two carried the residual.

Format characters take the border markers punctuation already takes (`normalize.py`, the
`_is_punct_text`/`_is_symbol_text` branch). Ten oracle readings pin it, and the two that discriminate
were named by an adversarial review of an earlier and wrong version of this section:

```
aZb     3   no space border, no marker — as `a!b` gets a bare `!`
aZ b    4   Z⟨eow⟩, then the seam deletes the space
aZ 5    5   Z⟨eow⟩ with no ⟨bow⟩ right of the space, so the space survives and the ⟨eow⟩ stands
aZ  5   4   a space RUN kills the marker, the same rule punct has
a Zb    4   ⟨bow⟩Z, and the seam deletes the space to its left
5 Za    6   ⟨bow⟩Z with no ⟨eow⟩ left of the space, so nothing is deleted
1 1     4   unchanged — this is what refutes "ASCII digits take a left ⟨bow⟩", which fits the
            other nine and predicts 5 here
```

Under-count over 44 Goldfish languages falls **398 → 143**: Khmer 180 → 25, Lao 119 → 51, Myanmar
34 → 17, and Malayalam, Tamil, Sinhala, Ossetian, Mari and Gilaki to zero. UDHR is unmoved at
307/501 and 430/501 (it holds almost no ZWSP) and its error mass rises slightly, 0.313% → 0.334% on
v3; Rosetta and MultiPL-E still reproduce every document.

Two notes on how this was got, both corrections to what stood here first:

* **"Absorption" was never in the code.** There is one conjunctive rewrite — `SEAM_RE` deletes a
  space iff `⟨eow⟩` stands immediately left AND `⟨bow⟩` immediately right — and nothing per-side.
  An earlier draft of this section described a per-side absorption mechanism that fits the oracle's
  *costs* and does not exist in the encoder. The cost arithmetic survived; the mechanism did not.
* **Ten numbers did not pick the rule.** Two different single-glyph changes reproduced all ten, and
  the tie broke only on `1 1` and `5 Za`. A rule that fits every measurement you have is not thereby
  the rule — ask what else it predicts, and go measure that.

## 8. A true piece can push a word below the oracle, and that does not impeach it

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

## 9. Two UDHR documents are unexplained

Shipibo-Conibo (+4.38% v3, +3.14% v4.7) and Lamnso' (+3.27% / +2.84%) are the worst documents in
both families and nothing in this campaign touched them. Lamnso' has no reachable corpus at all —
eBible has no `lns`, Glot500 has no `lns`, the Wikimedia Incubator has no `Wp/lns`, and SIL's Bloom
Library has it behind a gate — so the question cannot be asked without spending the held-out gate.

## 10. Access and scale

- **StarCoder is gated.** `bigcode/starcoderdata` and `bigcode/the-stack-dedup` both require
  authentication. The external replay above uses `bigcode/the-stack-smol-xs` (same Stack lineage,
  open) and `codeparrot/github-code-clean` instead.
- **A 10M-document sweep is on the order of 200 hours of API time** at the throughput this
  sustains for documents of a few thousand characters. Any sweep at that scale has to resume from
  disk; it is not something one session finishes.
