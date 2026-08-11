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

The shortest discriminating rows name two classes. U+0730–U+073F are ordinary Syriac vowel points
*on a base*: `ܒܰܒ` stays one word and was already exact. Every mark in U+0740–U+074A instead stands
outside the word: `ܒ݁ܒ` and `ܒ݂ܒ` each cost two more than the old stream, while `ܒ݁ ܒ` costs one
more because the separator prevents seam-space absorption. A vowel point written after such a
separator was first modelled as riding the same unmarked run — `ܒ݂ܶܒ` is exact under that spelling
— but the 2026-08-09 space-border and message-end probes refuted it: a BASELESS vowel point is a
word-forming letter, opening a ⟨bow⟩…⟨eow⟩ word of its own that a following letter continues
(`ܒ݂ܶ` = 21, `x ܒ݂ܶ x` = 23, `x ܒ݂ܶx` = 22; the mid-word row prices identically under both
spellings, which is why it alone could not tell them apart). The same law closes the 153-row stray
Syriac-vowel family (`ܑ` `!ܑ` `1ܑ` `z ◌ܑ` `x◌ܑ◌ܑx`): all 2,526 cached Syriac rows now read
2,515 exact / 8 over / 3 under, from 2,332 / 27 / 167.

This section also carried a second, host-sensitive class — on a Syriac letter the U+0300–U+0362
range closes the run, on a noncomposing Latin host it does not — and five pretoken-context mark
pieces to go with it. **Both were retracted 2026-08-10 (§14).** The range closes the word on every
host, and it closes it BEFORE the mark rather than after; there is no Syriac exception and there
are no mark pieces but U+0301. The Latin block sweep that produced the host rule was run against
`x H M z x` on hosts whose word costs two tokens, where the two spellings are arithmetically
identical — it could only ever have returned "Latin does not close".

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

**Five of the seven came back on 2026-08-10 (§17.4), and the reading above is what has to be
corrected.** `ัง` `ัน` `ับ` `ัก` `ือ` are real pieces and always were; what was false was the model
they were applied to, which was writing thousands of tokens of boundary marker in the wrong places
(§§7, 14, 15). Courted one at a time against real Thai words, each repairs dozens of distinct words
and pushes NONE below its recorded count. **The instrument lesson survives the retraction intact,
and is in fact sharpened by it: a batch hides its own failures, and the only thing wrong with this
measurement was that it judged seven candidates as one.**

The obvious reading is that the scaffold is at fault: `.ヲXヲ.` supplies a katakana anchor that
becomes the cluster's base, and Thai does not put it there. So the campaign was re-run with the
scaffold removed entirely.

**The own-script instrument fails harder.** The retired fitness enumerator needs no anchor at all: it
takes a Thai line and its recorded count and enumerates, from the tiling DP, every single piece
whose addition would make that line reproduce. The probe is the Thai. Requiring at least two
independent lines to agree on exactly one piece yielded 175 pieces from 1,200 lines. On 17,962 lines
of FineWeb-2 Thai and Tamil:

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
in the same frames, so this is a vocabulary difference, the same shape as the `±`/`©`/`®` symbol
examples. Nor is it a stream rule about absorbing the space: absorbing it would
take `a³ b` *below* its recorded count.

The retired fitness enumerator named the missing pieces — `² ` and `².` — and no shipped template
can price either. `²` is HARD, a space and a full stop are not, and the probe generator refuses mixed
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
`mark_sep` (overhead 12), chosen by `is_killer` rather than by which number comes out.

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

*The finished marker model this section discovers piecemeal is stated once, as a table, in
README.md § "Where the boundary markers go". Read that first; the subsections here are the history
of how each row of it was found, and what each one cost.*

**Every rule below has the same shape**, which is the thing worth carrying forward: a class of run
that the border-marker branch never reached, so it silently wrote no markers and the vocabulary
grew pieces to stand in for them. Format characters (ZWSP is `Cf`, not a killer, so it fell through
to HARD), terminal separators, HARD runs holding a mixed body, ideographic punctuation, digit-run
borders, and finally the combining accents of §14 — six populations, one bug, found six times.
**The class that has no branch writes no marker, and a missing marker never announces itself: it
turns into an under-count somewhere far away, or into a piece that prices correctly for the wrong
reason.**

Retiring `ownscript` took under-count across 44 Goldfish languages from thousands to **789**, and
what is left is concentrated in six: Malayalam 188, Khmer 180, Lao 119, Tamil 94, Myanmar 76,
Sinhala 74. Under-count should be impossible — the tiler takes a shortest path over a vocabulary
meant to be a SUBSET of the real one — so each case is one of two things, and they need different
fixes: a false piece, or a missing boundary glyph (§8).

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

**Correction, 2026-08-09: the last line is true of ASCII digits only, and the ⟨bow⟩ in it is the
frame's.** A NON-ASCII digit run takes punctuation's border markers on BOTH sides — see
`normalize._digit_eow`. The reason it read as "closes with nothing" is that the closing marker is
invisible almost everywhere: an ⟨eow⟩ before `space + ⟨bow⟩` is deleted along with the space, so
every probe whose right neighbour is a word, a punctuation run or another marker-taking digit run
prices the same either way. It shows only before a run that writes no ⟨bow⟩ of its own — `８ 取`,
`٥ 取`, `文 ½ 文`, `한 ５ 한` each cost one more than the marker-free spelling charges. The rows
above stay correct because ASCII digits are not in that population (`1 1` = 4, `文 5 文` exact).

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
like any other seam — and the retired seam exception exempted terminal marks from exactly that. So
the space was
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
`is_killer(U+200B)` is False — and it reaches `classify` with no branch of its own, so
it falls through to HARD, which writes no markers at all. It is also the word separator of Khmer and
Lao, which is why those two carried the residual.

Format characters take the border markers punctuation already takes (`normalize.py`,
`_is_borderable_text`). Ten oracle readings pin it, and the two that discriminate
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

### Killer runs are punctuation too, and HARD runs must not swallow it

**Measured and implemented 2026-08-08**, after the format-character rule above and by the same
argument: a class of run that the border-marker branch never reaches.

**A terminal-separator run takes punctuation's border markers.** `⟨bow⟩` when the left neighbour
ends in a space, `⟨eow⟩` when the right is exactly one space, killed by a run of 2+:

```
ກ່5  +0    ກ່ 5 +1    ກ່  5 +0    5 ່ກ +1    5 ່ 5 +2    ກ່ ກ +0    ກຸ 5 +0 (non-terminal control)
```

The word side could never have decided this: `ກ່ ກ` costs the same under both spellings, because the
new `⟨eow⟩` lets the seam delete the space that the old spelling paid for literally. Only the digit
side separates them, which is why the two pinned streams in `tests/test_api.py` changed shape while
their counts did not.

**A HARD run splits where the character kind changes.** `文？` is one run by class, so the whole-run
predicates see a mixed body, fail, and `？` loses markers the same character gets in a run of its
own: `文？ 文` and `文 ？文` each cost one more, while `文？文`, `文？  文` and `あ？ 文` are exact.

Under-count over 44 Goldfish languages falls **143 → 41**: Lao 51 → 1, Myanmar 17 → 0, Japanese
11 → 1, and Malayalam, Tamil, Sinhala and Chinese to zero. Rosetta and MultiPL-E still reproduce
every document; UDHR is unmoved on v4.7 at 430/501 and loses one on v3.

**Over-count rises 33,024 → 33,686, and that is the unfinished half.** The five killers with a fused
`K⟨eow⟩` piece in the real vocabulary — Tamil, Sinhala, Malayalam, Devanagari, Bengali nukta — now
pay for a marker we cannot spell, because we do not have those pieces. A trial patch that adds them
takes Tamil 11,792 → 1,461, Sinhala 7,942 → 706 and Malayalam 4,342 → 5 of over-charge, and leaves
Thai, Khmer and Myanmar untouched, which is consistent: those three read `+0` on the discriminating
probe and are predicted to have no fused piece. **The inventory is per piece, not per script** — a
blanket Bengali nukta piece introduced four new under-counts — so it needs a mining pass with real
witnesses rather than the five characters written down here.

## 8. An under-count is always a defect. There is no third explanation

An earlier version of this section said the engine tiles by shortest path while "the tokenizer it
reconstructs merges in a fixed order", so the two could disagree and no vocabulary change would fix
it. **That is wrong, and it was never measured — it was imported from BPE, which this tokenizer is
not.** Nothing in this repo's evidence shows a merge-ordered encoder, and min-cost tiling reproduces
1,741 Rosetta documents and 22 MultiPL-E files exactly, which is not what an algorithm mismatch
looks like.

So the inventory of causes has two entries, not three:

1. **a false piece** — the vocabulary claims one token for something that is two or more, so the
   cover we find is cheaper than any the encoder could take;
2. **a missing boundary glyph** — the stream omits an ⟨eow⟩/⟨bow⟩ the encoder writes, so we are
   tiling a shorter string than was tokenized.

Both are findable and both are fixable. The campaign of 2026-08-08 is the evidence for taking that
seriously: every under-count population examined that day resolved into one of the two — 439 pieces
whose own probes refuted them, five `virama + space` pieces compensating for an absorption the
stream never performed, and four classes of run (format characters, terminal separators, ideographic
punctuation, Quranic annotation) that never reached the border-marker branch. Under-count over 44
Goldfish languages went from thousands to 38 without once needing a third category.

**`cəhənnəm` was the test case, and it resolves to entry 1.** The false piece was not `ən` — which
is witnessed and repairs 296 standalone word counts — but `nə`, whose own template prices it at
**two** tokens (`.ヲnəヲ.` reads 21 where a piece reads 20). With both present the tiler spent two
overlapping ə-n bigrams and landed one below. `nə` came in on the retired `ownscript` kind, with the
probe `ənənə` — a string that `ən` explains exactly as well, which is instrument warning 5 verbatim.

It was already fixed: `be5beb4` retracted `nə` in the same commit that bought `ən`, so the shipped
model has counted the word exactly ever since. This section claimed otherwise for a day, and carried
a detail that would have refuted it on inspection — the word does not contain `ən` twice. **An
unfixable category was invented to explain a case that was already closed**, which is the strongest
argument available for not having the category at all.

What survives from the old section is only the operational half: a push-below control has to be
**net rather than absolute**, because an absolute one refused `ən` outright and with it the single
largest repair in the campaign. That is a statement about how much evidence one word carries against
296, not a licence to call the residue unexplainable.

**The standing rule this leaves:** never reach for an algorithm mismatch to explain a count. If a
tiling cannot be found, that is a fact about the search or the vocabulary, and the answer is to keep
looking — not to conclude the encoder works differently.

## 9. Two UDHR documents are unexplained

**CLOSED 2026-08-10 — §14.** Shipibo-Conibo (+4.38% v3, +3.14% v4.7) and Lamnso' (+3.27% / +2.84%)
were the worst documents in both families and no campaign had touched them. They now read +0.01% /
+0.00% and +0.02% / +0.01%. Neither needed a corpus and neither needed a piece: both write their
tone with combining accents, and the accent's word boundary was in the wrong place. The section
stands as a reminder that "no reachable corpus" is a statement about one line of attack — Lamnso'
still has no `lns` in eBible, Glot500 or the Wikimedia Incubator, and it did not matter.

## 10. Access and scale

- **StarCoder is gated.** `bigcode/starcoderdata` and `bigcode/the-stack-dedup` both require
  authentication. The external replay above uses `bigcode/the-stack-smol-xs` (same Stack lineage,
  open) and `codeparrot/github-code-clean` instead.
- **A 10M-document sweep is on the order of 200 hours of API time** at the throughput this
  sustains for documents of a few thousand characters. Any sweep at that scale has to resume from
  disk; it is not something one session finishes.

## 11. The contextual-mark residual: what 2026-08-09 pinned, and what it could not

**SUPERSEDED 2026-08-10 — §14.** The five pieces this section is about are gone, and so is the
grid of unexplained rows below: they were the in-word spelling of a mark that stands outside its
word. Kept as written because the instrument lesson is the point — a tile-eligibility rule that
fits 434 rows and leaves 9 is what a wrong factorization looks like from the inside.

The five word-context mark pieces (U+0302 0303 0304 0327 0331) were made tile-contextual by a
now-retired host rule: the piece prices 1 after a single-letter tile of at most two UTF-8
bytes, with or without ⟨bow⟩/case markers, and after a markerless multi-letter ASCII tile; it pays
its own bytes after everything else. That rule took the 434-row probe grid from 402 exact / 68
under to 445 / 9, and every one of the 9 residual unders predates it. They are the UNEXPLAINED
part, and their minimal grid is:

```
π̂       14   the mark prices 1 after ⟨bow⟩π          xπ̂x   17   and pays bytes after a bare π
чипа̄ли  18   prices 1 after the single tile а         бимчэ̄ 18   pays bytes after the single э
о̄мачин  17   prices 1 after ⟨bow⟩о                    мэ̄нэ  19   pays bytes after э again
до̄вани  16   prices 1 after the marker-multi ⟨bow⟩до  ба̄охан 17  pays bytes after ⟨bow⟩ба
x b̃ 2 x 20   one under with the piece priced at 1 and the ⟨eow⟩ written
```

No tile rule separates the left column from the right out of our vocabulary: `π` and `э` are unit
pieces exactly as `а` and `о` are, and `⟨bow⟩до` and `⟨bow⟩ба` are the same tile shape. Every row
on the left is consistent with a fused piece in the oracle's vocabulary that ours lacks
(`⟨bow⟩чип`-shaped hosts, or `о̄`-shaped host+mark pairs), and every such explanation is
unfalsifiable one row at a time — which is why the non-ASCII two-byte hosts keep the piece at 1
(the corpus-frequent reading) and the rows above stay listed as rows, not attributed. The UDHR
cost of the tile rule is real and deliberate: tca/oaa/snn/ame moved from small unders (hidden
errors) to larger overs (honest missing vocabulary), v4.7 443 → 442 exact and mean 0.094% → 0.105%.

The dotted capital İ first appeared to have the same shape: its unit piece seemed to pay its two
bytes where İ was word-final or followed by an ASCII lowercase letter and the tile before it
carried a marker and ended in an uppercase ASCII letter. Section 15.3 supersedes that reading. The
named words are title-case spans with a literal İ, and the few all-caps shapes that still reached
the tile rule refuted it. The rule was removed rather than retained as an exception.

One row originally stayed unexplained:

```
x novunİ x       17   İ prices 1 after the tile (un)
x Hüseynovunİ x  22   İ pays bytes after the same tile (un) — one under for us
```

The two words share their entire tail; only `⟨bow⟩H` + `ü` differ, five tiles before the İ. No
rule over the preceding tile can separate them; a piece we lack (`⟨bow⟩Hüseynovun`-shaped, which
would put a marker-carrying multi-letter tile before the İ) would, and is not attributed without a
probe that could refute it.

## 12. The last eight under-counts, 2026-08-09

**MOSTLY SUPERSEDED 2026-08-10 — §14.** Three of the four populations below reproduce now, and none
of the three was about what its heading says: 12.1, 12.3 and 12.4 are one rule about unattached
mark runs (§14.4). 12.2, the dotted İ, is untouched and still open. The
retired charging-border rule that opened this section was the U+0300 block's word
boundary read one character late (§14.1). The self-consistency check in the last paragraph — our
digit frame agreeing with our letter frame in 30 rows — is why it went in wrong; both frames were
ours.

Two rules landed this day and took the under-count over Goldfish, Glot500 and the FineWeb/Stack
slices from 18 to 8. Both were the same shape — **a border marker that is invisible wherever a
⟨bow⟩ follows the space**, because the seam then deletes the marker along with the space, so only a
right neighbour that writes no ⟨bow⟩ of its own can see it:

* a non-ASCII digit run takes ⟨eow⟩ as well as ⟨bow⟩, per border CHARACTER, and a HARD run splits
  at the number boundary (`normalize._digit_eow`, `_hard_kind`) — Japanese 4 → 0;
* a word ending in a charging mark takes the same right-hand ⟨eow⟩, which is what the retired seam
  exception was standing in for — Yoruba 5 → 0, and the last
  Glot500 Yoruba row with it.

|  | exact | over | under |
|---|---:|---:|---:|
| 44 Goldfish languages, before | 39,868 | 9,165 | 16 |
| after | 39,873 | 9,234 | 7 |
| 43 Glot500 files, before / after | 14,699 / 14,699 | 992 / 993 | 2 / 1 |
| FineWeb, the Stack, github-code (242,188 rows) | 232,631 | 30,622 | 0 (unmoved) |

**Over-count rises 70, and that is the intended direction.** Every token of the rise is a word that
was ALREADY over-charging by the same amount in the letter frame: `а́` reads +2 there both before
and after, and only the digit frame used to read +1, because a token was missing. §4 is the reason
to take that trade — an over-count can be mined and an under-count cannot.

Row-level churn was measured rather than assumed, by tiling every row twice: 3 rows that reproduced
stop and 4 that did not start, all seven in Yoruba. Not one of `abk_cyrl`'s 60 extra tokens breaks a
row — every one lands on a row that was already wrong, which is what distinguishes "a hidden error
became visible" from "the rule is wrong". The 15-host differential grid is the other half of that
argument: before the change the digit frame read exactly one BELOW the letter frame in all 30 rows
of b q ẹ ü ɔ / а и б ә / π / ܒ / ب / क / ก / ᛒ × U+0301 U+0303, and after it the two frames agree
in all 30, so there is no host on which the marker is wrong.

The remaining eight are four populations, and none of them is a rule we could not find for want of
probes. Each has a control that refutes the obvious rule.

### 12.1 A boundary between adjacent byte-floored characters — five tokens, one population

`mdf_cyrl` 1, `aze_arab` 2, `snd_arab` 1 and `lao_laoo` 1 were four separate entries in the
campaign brief. They are one measured shape: **where two adjacent NON-ASCII characters stand inside
one pretoken, no piece spans the pair, and they are not the same character, the oracle charges one
token more than we do**, and the deficit counts those junctions exactly.

Each side may be a byte-floor run or a one-codepoint piece — `ຸ່` is a floored `ຸ` next to the
`່` piece and still splits — so this is not a statement about the byte floor. What it needs is
that no single piece covers the junction and that neither side is ASCII: `t͡s` and `tɕ` and `t͡a`
are exact because the `s`, the `t` and the `a` are ASCII, and the same U+0361 in `t͡ɕ` is one under.

```
x ٘ٛ x   20 (−1)   x ٘٘ٛ x   22 (−1)   x ٘ٛ٘ x  23 (−2)   x ٘ٛ٘ٛ x 26 (−3)
x t͡ɕ x  20 (−1)   x ɕ͡t x    20 (−1)   x ɕ͡ɕ x  23 (−2)
x ٖ۽ x   20 (−1)   x ຸ່ x     19 (−1)   x ຸຸ່ x  21 (−1)   x ٰ٘ x  20 (−1)
```

Controls, exact, and they are what makes the junction count the predicate rather than the
characters: `x ٘ x` `x ٛ x` `x ຸ x` `x ٖ x` singly; `x ٘٘ x` `x ٘٘٘ x` `x ٘٘٘٘ x` `x ຸຸ x`
`x ່່ x` `x ﬞﬞ x` `x ٰٰ x` `x ɕɕ x` (identical neighbours, no junction); `x t͡s x` `x t͡a x`
`x tɕ x` (one side is ASCII); `x b̃ɕ x` (U+0303 is a killer, so the two sit in different
pretokens); `x ัิ x` `x िी x` `x ఀఀ x` (ccc-0 marks are WORDY words rather than unattached-mark
runs, and a piece spans the pair).

**And it cannot be written, because a piece we cannot see covers about half the junctions.** The
refutation is exact and same-script: `ٖٗ` (U+0656 + U+0657) rides at 19 while `ٜ٘` (U+065C +
U+0658) splits at 20 — same combining classes (220 then 230), same byte lengths, same block, same
ascending canonical order, differing only in which characters they are. `ٙٚ` `ٚٛ` `ٖٙ` `ٗٙ` ride
too, `ٗ٘` `٘ٗ` `٘ٛ` `ﬞ٘` `ﬞ֑` split. So the boundary is real and the oracle's vocabulary swallows
it for particular pairs, exactly as `±`/`©`/`®` swallow the symbol ⟨eow⟩.
Writing it unconditionally would break every identical-neighbour row above — a clean population
that reproduces today — to buy five tokens. It is listed, not implemented.

### 12.2 The dotted İ after a lone ⟨bow⟩H tile — one token

§11 left this as `x Hüseynovunİ x` = 22 against `x novunİ x` = 17 and could say only that the two
words share their tail. The trigger is now localized to the head, three tiles shorter:

```
x Hnİ x       18 (−1)      x hnovunİ x    19   x aHnovunİ x  20   x HHnovunİ x 20
x Hunİ x      18 (−1)      x RPnovunİ x   20   x Novunİ x    18   x HNovunİ x  19
x Hovunİ x    19 (−1)      x novunİ x     17   x ünovunİ x   19   x Hİ x       17
x Hnovunİ x   20 (−1)      x Hnovunİa x   20 (−1)   x Hnovunİl x  20 (−1)
```

So the İ byte-prices when the word's FIRST tile is `⟨bow⟩` plus a single uppercase ASCII letter and
every letter between it and the İ is lowercase; a second capital anywhere (`HHnovunİ`, `RPnovunİ`,
`HNovunİ`), a lowercase head (`hnovunİ` `ünovunİ` `novunİ`), or a first tile that swallows more
letters (`Novunİ` tiles `⟨bow⟩Nov`) all keep the piece at 1. That is a rule over a tile FIVE tiles
away from the İ, which the then-current tile rule could not express and which nothing else in the
model needed, so it was not written on this evidence.

The obvious mechanism — the word is title-case, the oracle writes ⟨shift⟩ and İ lowercases to the
two codepoints `i` + U+0307 — is **refuted**: `x Hnovuni̇ x` = 22 where `x Hnovunİ x` = 20, and
`x Hnovunİİ x` = 21 is one under, not two, so the cost is not per İ either.

### 12.3 A stray-mark run at message end — one token

`knc_arab`'s row is an unattached mark that ends the message. The border rule says the message end
is not a space and writes no ⟨eow⟩; here one is charged:

```
x وا۟ۖ  20 (−1)     x 1ۖ  18 (−1)     x ۖ  16 (−1)     x 1ﬞ  19 (−1)
```

with every padded counterpart exact — `x وا۟ۖ x` = 21, `x 1ۖ x` = 19, `x 1ﬞ x` = 20, `x وا۟ۖa` = 20,
`x وا۟ۖ 1` = 22 — and each mark alone exact (`x وا۟` `x واۖ`). **The obvious rule is refuted by
another mark in the same block**: `x 1٘` = 16 and `x 1٘ x` = 18 are both +1 OVER, the same offset in
both frames, so U+0658 pays no message-end ⟨eow⟩ while U+06D6 and U+FB1E do. A marker rule cannot
split two stray marks that way; a piece can, which puts this in 12.1's category rather than its own.

### 12.4 One Igbo word — one token

The last Glot500 row is `ufọkn̄wed`, and it is a word, not a rule:

```
x ufọkn̄wed x  22 (−1)     x ndin̄wam x  20     x kn̄w x  18     x bn̄w x  18
x n̄wed x      18          x n̄w x       17     x kn̄ x   18     x n̄ x    17
```

Everything the word is made of reproduces; only the whole does not. `x an̄ x` and `x an̄b x` read
+1 in the same grid, so the `n̄` neighbourhood holds an over-charge as well. This is a vocabulary
question for a miner, not a stream question.

## 13. Bengali and Assamese were a vocabulary campaign, and ten pieces closed them

**Measured 2026-08-09.** §0 named `ben_beng` and `asm_beng` the two largest minable pools. They
were, and they are now the two smallest: ten pieces over the two families take 2,000 Goldfish rows
from 1,913 wrong to 7, without moving under-count anywhere.

### 13.1 The ranking that sent this campaign was already stale

§0's table says Bengali 28.3% exact / 2,251 over and Assamese 31.5% / 1,901, measured 2026-08-08.
By the time this campaign opened, the border-marker and mark-eligibility work of the following day
had taken v4.7 to **847/1,000 exact and 203 over** for Bengali and **820/1,000 and 404** for
Assamese. The pool the ranking pointed at was three quarters gone before anyone mined it, and the
real pool was the one the sweep never measured: **v3**, where the same 2,000 rows carried 3,245
tokens of over-charge against v4.7's 607, because v3's vocabulary is three times the size and only
114 of its pieces were Bengali. A ranking is a measurement with a date on it; re-measure before
spending on it.

### 13.2 Localize first, and probe every word rather than the top four thousand

| | over-charge inside single words | words priced |
|---|---:|---:|
| `ben_beng` v4.7 | 201/203 (**99%**) | 4,000 |
| `asm_beng` v4.7 | 396/404 (**98%**) | 4,000 |
| `ben_beng` v3 | 1,709/1,709 (**100%**) | 12,328 (all) |
| `asm_beng` v3 | 1,534/1,536 (**100%**) | 12,359 (all) |

Both are Catalan-shaped, not Lombard-shaped, so a miner was the right instrument. **The word cap is
part of the measurement, though.** Run at `localize.py`'s default of 4,000 words, v3 Bengali reads
70% and Assamese 68% — and the missing third is not a joining defect, it is the 8,300 words the cap
never priced. Pricing all of them moves the reading to 100% and changes the verdict from "a third of
this is structural" to "none of it is." A localization fraction is only as good as its coverage of
the wrong rows' vocabulary, and the number to report is the one where every word of every hot row
has a recorded count.

### 13.3 Two facts about the script, each with its rival refuted

**Bengali `য়` is a composition exclusion.** NFC writes U+09DF as U+09AF U+09BC, and the nukta is a
terminal separator, so `সময়` streams as `⟨bow⟩সময⟨eow⟩়` — the word closes *before* the mark and a
following syllable opens a second word (`সময়ের` = `⟨bow⟩সময⟨eow⟩়⟨bow⟩ের⟨eow⟩`). Every wrongly
priced Bengali word on v4.7, all 25 of them, contained `ময়`. The missing token is the suffix
`ময⟨eow⟩`.

The rival — the nukta rides *inside* the word and the oracle holds `য়⟨eow⟩` — is refuted by the
words that have no ম in front:

```
নয় 3   হয় 3   আয় 3   ময় 3   য় 2      all exact today
```

Under the rival each of the first four would cost 2, one BELOW its recorded count, which §4 says is
the direction nothing can undo. It is also why `য়`-shaped candidates never reach a probe: no
template can place a piece the stream never writes.

**Assamese web text writes the vowel O in the pre-Unicode order.** U+09BE U+09C7 (AA then E) where
the modern orthography has the single U+09CB, in 45 of 1,000 rows. The rival here is that the
oracle reorders or composes the pair, and one row cannot tell:

```
ভােট 15 = ভোট 15        ােৰ 16 ≠ োৰ 15   (v4.7)      13 ≠ 12   (v3)
```

The first row is consistent with both readings; the second is not — two spellings that cost
different amounts are not the same string. So `াে` is a piece, and its `mid` probe prices it at 1
in both families. v4.7 already shipped the sibling `াি`.

### 13.4 What the two families disagree about, and the host that cannot arbitrate

v3 additionally needed four word-initial vowel signs — `⟨bow⟩া` `⟨bow⟩ি` `⟨bow⟩ে` `⟨bow⟩ো`, which
the nukta split creates and which v4.7 already had — and two doubled vowel signs, `ুু` and `াা`,
the typos a web-trained vocabulary learns. **Those two are v3-only because v4.7's own probe refuses
them**: `.ヲুুヲ.` and `.ヲাাヲ.` read cost 1 on v3 and cost 2 on v4.7. A four-host differential
`delta(H, X) = count(".HXH.") − count(".HH.")` agrees on ক, ব and ヲ — 1 for v3, 2 for v4.7 — and
names the host that must not be used:

```
delta(ন, া)  = 0    in BOTH families
```

`না` is itself a piece, so a Bengali ন host swallows any junction with a following `া` and the
differential measures nothing. That is instrument warning 4 in a new script: a probe that cannot
distinguish two candidates proves neither.

### 13.5 What the batch did, judged as a batch

Every cached row on disk, tiled twice. A piece can only change a row where its surface occurs, so
rows holding none of the ten surfaces are tiled once and their `after` is their `before` by
construction — which is what makes the whole 242,188-row FineWeb/Stack/github-code replay
affordable here.

```
v4.7   45 Goldfish languages   exact 40,693 -> 41,024   over 9,638 -> 9,033   under 7 -> 7
       FineWeb/Stack/github    exact 232,631 unchanged  over 30,622 unchanged under 0 -> 0
       43 Glot500 files        exact 14,699 -> 14,737   over   993 ->   943   under 1 -> 1
       ALL 302,418 rows        exact 288,023 -> 288,392                       under 8 -> 8
       rows broken 0    rows repaired 369

v3     30 Goldfish languages   exact  2,698 ->  3,947   over 50,410 -> 47,170  under 6 -> 6
       FineWeb/Stack/github    exact 275,775 unchanged  over  1,566 unchanged  under 0 -> 0
       ALL 286,856 rows        exact 279,012 -> 280,262                        under 6 -> 6
       rows broken 0    rows repaired 1,250
```

Per language, and note that no Goldfish language other than the two moved by a single token:

| | v4.7 exact | v4.7 over | v3 exact | v3 over |
|---|---:|---:|---:|---:|
| `ben_beng` | 847 → **1,000** | 203 → **0** | 339 → **999** | 1,709 → **1** |
| `asm_beng` | 820 → **998** | 404 → **2** | 407 → **996** | 1,536 → **4** |

Glot500's Assamese, which chose nothing, went 370/400 → 400/400 and Bishnupriya 391 → 399.
(The v3 Goldfish row count is 10,035 over 30 languages rather than 45,000 over 45, because the
350-language sweep was run against v4.7; the v3 counts for the other fifteen languages were never
bought. Nothing hangs on it — a piece made only of Bengali codepoints cannot alter a row that has
none, and `touched` is 0 for every non-Bengali source.)

The held-out gates chose nothing and moved anyway: **UDHR 316 → 317 exact on v3 and 442 → 443 on
v4.7 and v5**, error mass 0.324% → 0.322% and 0.164% → 0.163%, speakers-weighted 0.071% → 0.063%
and 0.031% → 0.030%. It is the same document in both — UDHR Bengali, +43 → 0 on v3 and +6 → 0 on
v4.7. Rosetta 1,741/1,741, the 250-document holdout 249/250 and MultiPL-E 22/22 are all unmoved.

### 13.6 What the templates refused, which is nearly everything

The interesting number is not the ten kept but the wall they came through. Replaying round 0's
proposal rule and classifying each verdict:

| | well-formed spans proposed | probed | kept | refused by their own probe | refused on placement | refused as net-worse |
|---|---:|---:|---:|---:|---:|---:|
| v4.7 | 3,503 | 1,200 | 2 | 1,198 | 0 | 0 |
| v3 | 12,943 | 1,200 | 6 | 1,194 | 0 | 0 |

The refused spans price at 2 to 13 tokens on their own templates. Not one candidate in either family
was refused by the net word control — which is worth saying plainly, because that control is the
part of the rig that exists to catch §1's failure, and in this campaign it never had to fire. The
templates did all of the work, and the batch measurement then confirmed the same answer at row
level. A second v3 round probed 103 more and kept 2; the cross-port bought 4 more probes in v4.7
and kept 0.

### 13.7 The seven tokens that are left, and what they are

```
v4.7  asm_beng 2 rows, +1 each    every word of both rows prices exactly
v3    asm_beng 4 rows, ben_beng 1 row, +1 each
        3 of the 5 hold a wrong word, and all three are Latin-glued: DMামেক, IRGCৰ, SDFৰ
        the other 2 have no wrong word at all
```

So the residual is two different things and neither is Bengali vocabulary. The rows with no wrong
word are a joining question, the Lombard shape of §0 in a script where it accounts for 2% rather
than 79%. The Latin-glued words are a mixed-script, case-carrying span, which the probe generator
refuses on purpose (§6: the `cased_*` templates answer a different question about a fused case
marker) — they need a campaign with a frame of their own, not a template stretched to cover them.

### 13.8 An instrument note: a substring shortcut has to be taken after normalization

The batch judge skips re-tiling rows that cannot contain a new piece, and the first version of that
test asked whether the piece's surface occurred in the raw row. It does not. `য়` is a composition
exclusion, so the corpus writes U+09DF where the stream holds U+09AF U+09BC: the surface `ময`
occurs in 36 of the 1,000 Bengali rows raw and in 163 normalized. The shortcut declared four fifths
of the affected rows unaffected and reported Bengali at 882/1,000 where the true figure was
1,000/1,000 — a wrong answer in the direction that looks like a modest success, which is the
dangerous direction. Any filter that decides what not to measure has to be applied to the same
string the tiler sees.

## 14. A combining accent stands outside its word, and §§11–12 were consequences of it

**Measured 2026-08-10.** The five word-context mark pieces of §11 and all four open populations of
§12 were one mistake, made on an instrument that could not see the thing it was measuring.

### 14.1 The instrument, and why the old one could not work

`EXTRA_KILLERS` held nine members of the U+0300 block, put there by
`cost(H M H) == cost(H M) + cost(H)` on **byte-floor consonant hosts**. On such a host the two
candidate spellings are arithmetically identical:

```
the word closes AFTER the mark   ⟨bow⟩H M ⟨eow⟩ ⟨bow⟩X⟨eow⟩
the word closes BEFORE it        ⟨bow⟩H⟨eow⟩ M ⟨bow⟩X⟨eow⟩
```

because `⟨bow⟩H⟨eow⟩` and `⟨bow⟩H` + `⟨eow⟩` cost the same when no piece covers `H`. Every mark
reads "splits" there and no mark can read anything else, so the test was measuring the host, not the
mark. The obvious repair — take the mark's increment over the bare host word, `x H M z x` minus
`x H z x`, so the host's own pricing cancels — has the same defect for a subtler reason: under the
right spelling the word `Hz` becomes TWO words, so the host's pricing does not cancel at all. That
is what makes the split look host-dependent, and it is a trap worth naming, because the arithmetic
looks like a controlled experiment: `q` and `б` read +2 where `ก` and `ب` read +3 only because
`x q x` = 10 and `x ก x` = 11.

**The rule that trap proposes, written out, so nobody proposes it again.** Read through that
difference the split looks HOST-dependent, and the pairs it produces look like a discovery rather
than an artefact, because they cancel the two properties a reader would reach for first: `ب` splits
and `б` does not though both are two-byte letters whose `⟨bow⟩X` is a piece and whose bare word
costs the same 15; `ก` splits and `क` does not though both are three-byte letters at that same 15.
Byte length refuted, piece-ness refuted, two scripts on each side — the shape of the answer looks
like the measured per-script population `EXTRA_KILLERS` already is, and `_ends_legacy_killer_run`
already carried a Syriac host clause as precedent. It would have been enumerable, defensible, and
wrong in every script including the ones it got right by accident. **The tell was available and was
not used: the rival predicts nothing outside the frame it was derived in.** Asked for a row where
the two spellings differ — which is what the `5` frame is — it has none.

Two frames on a host whose whole word is ONE token separate them, and both are oracle-only:

```
m   = `x qM x` - `x q x` - 1     the mark's own cost — both spellings charge m + 1 here
gap = `x qM5 x` - `x q5 x`       m if the word closes BEFORE the mark, m + 1 if it does not
```

The right neighbour has to be an ASCII digit. Against a letter the seam deletes the difference;
against `5` nothing opens a word, so the marker survives to be counted. `x q̊5 x` = 14 is the row:
the in-word spelling charges 15.

### 14.2 What the sweep says

Every codepoint of U+0300–U+036F, on 21 one-token hosts spanning Latin, Greek, Cyrillic, Armenian,
Hebrew, Arabic, Devanagari, Bengali, Tamil, Telugu, Thai, Myanmar and Hiragana, in both families.
**No host and no family dissents about any mark.**

```
closes before   U+0300-U+033F  U+0342  U+0346-U+0362        (0340 0341 0343 0344 fold away in NFC)
inside the word U+0345  U+0363-U+036F                        both ends pinned from inside the block
```

Re-scored against the shipped encoder afterwards, the whole sweep — both frames, every mark, every
host, 4,560 rows per family — reproduces exactly in both. So does the 418-mark annotation sweep,
838 rows per family, except for six v3 rows: `x qި x` `x qު x` `x qް x` and their digit frames read
one OVER, and the same three Thaana marks are exact on their own script's host (`x ހިހ x`), inside a
word (`x qިq x`) and on the `char` template. That is the ヲ hazard in miniature — a word-final
Thaana vowel on a Latin host — and it does not touch the verdict, which both frames agree on.

That is exactly the range the retired charging-border rule enumerated. Its population was right and
its reading was one step late: the extra ⟨eow⟩ it wrote at a word-final space border is the ⟨eow⟩
the word already had, one character earlier.

Asked of 418 more combining marks of the BMP, on in-script one-token hosts as well as `q`, the
answer is orthographic and not numeric — the same distinction `is_killer` already draws for Thai:
accents, tone marks, cantillation and annotation stand outside the word; vowel points and combining
LETTERS stay inside it. `гдⷭ҇и` carries both in one word: U+0487 pokrytie separates, and the
combining Cyrillic letter U+2DED beside it does not.

A second and third pass took the blocks the first one missed, and they were found the right way
round: by scanning every cached probe that still under-counted afterwards, which named N'Ko,
Mandaic and two stretches of Arabic Extended-B. 45 more marks, same two frames, same answer.
That loop — implement, re-scan the whole probe cache, let the residue name the next block — is
what a sweep should be steered by, and it is cheaper than guessing which block to buy next.

### 14.3 What that made true, and what it made false

* **The five mark pieces are false pieces.** On the `mark_sep` template every mark of the block
  except one reads cost 2 — its UTF-8 byte count — in both families. `q̃x` = 11 is
  `⟨bow⟩q⟨eow⟩` + two bytes + `⟨bow⟩x⟨eow⟩`, which is what the one-token piece plus an in-word
  ⟨eow⟩ was standing in for, and the whole of §11's tile-eligibility grid with it.
* **U+0301 is a token.** `.ᛒ́ᛒ.` = 20 / 24, cost 1 on the same template, with fifteen negative
  controls at cost 2. §12's "+2 in the letter frame" for `а́` was this piece, unattributed.
* **§11's UNEXPLAINED grid is gone.** `π̂` `xπ̂x` `чипа̄ли` `бимчэ̄` `о̄мачин` `мэ̄нэ` `до̄вани`
  `ба̄охан` `x b̃ 2 x` all reproduce, because there is no piece whose eligibility has to explain
  them.
* **§12.1, §12.3 and §12.4 are gone**, and the rule that closed them was not about marks at all
  (14.4). **§12.2 is not** — see 14.6.

Taken together that is **126 probes exact in both families**: everything §11's tile grid cites,
everything its UNEXPLAINED grid cites, all 23 rows of the retired charging-border rule, and §12.1,
§12.3, §12.4 and the Syriac-vowel law with their controls. The one row excluded from the count is
`x िी x`, which 12.1 listed as a control and which is one OVER on v3 and always was (14.6).

### 14.4 An unattached mark run is a word

A stray-mark pretoken already owned a ⟨bow⟩. It owns an ⟨eow⟩ too, against everything except a
LETTER, which continues the same word. That single rule closes §12.1's junction population,
§12.3's message-end run and §12.4's Igbo word, which is the argument that it is a law and not a
patch: none of the three was about the thing its section named it after. §12.2, the dotted İ, is
untouched by it and stays open.

The letter after it still writes its own ⟨bow⟩, and that half was measured the hard way. Dropping
it — reading the mark run and the following word as ONE word — is exact on every row of the probe
grid except one shape, because `⟨bow⟩x⟨eow⟩` costs what `x⟨eow⟩` costs and the two spellings
collapse. The shape that separates them is a baseless mark opening the message in front of a
three-byte letter with no suffix piece: `᯦ꝛ` `⳯ꝛ` `〪ꝛ` `꣠ꝛ` `゙ꝛ` and 33 more read 20 where the
fused spelling charges 19. Those 38 rows were exact before this campaign, and a full re-scan of the
probe cache is what caught the regression — a synthetic grid chosen in advance would not have
contained them.

### 14.5 What it cost, measured before and after on everything

| | v3 exact | over | under | | v4.7 exact | over | under |
|---|---:|---:|---:|---|---:|---:|---:|
| Goldfish + Glot500 + FineWeb/Stack/github-code, before | 280,262 | 49,283 | 6 | | 288,392 | 40,598 | 8 |
| after | 280,269 | 49,278 | **5** | | 289,088 | 38,442 | **1** |

**Over-count fell with under-count, by 2,199 tokens on v4.7**, which is what distinguishes a
misplaced boundary from a missing piece: it was wrong in both directions at once. The languages
that moved are the ones that write their marks separately — `yor_latn` 537 → 999 of 1,000 rows
exact and its over-count 1,163 → 1, `abk_cyrl` 949 → 992 (449 → 9), `zap_latn` 992 → 999,
`oss_cyrl` 989 → 997, `mrj_cyrl` 877 → 902 — and four Glot500 files (`ibo` `lin` `yor` `zul`) went
from imperfect to exact. The v3 side is smaller because v3's larger vocabulary already covered many
of the accented words whole.

The held-out gates, read once at the end: UDHR 317 → 338 exact on v3 (mass 0.322% → 0.188%) and
443 → 472 on v4.7 (0.163% → 0.058%), with the >5% band going 2 → 1 and 1 → 0; Rosetta's 1,741
mining documents and MultiPL-E's 22 stay at every document exact; and the 250-document Rosetta
holdout goes 249 → **250**, the last one being the Swift file whose combining marks sit on U+25CC
DOTTED CIRCLE — a stray-mark run, closed by 14.4.

The one v4.7 under-count left in 302,418 rows is an `aze_latn` row; v3's five are all `tam_taml`
and predate this campaign.

The other read is every text ever cached against either family, probe grids included — the
denominator the "under 18 → 8" figure of §12 was never measured over, which is how 793 synthetic
rows sat under-counting through three campaigns without appearing in a report:

| v3 | texts | exact | over | under |
|---|---:|---:|---:|---:|
| before | 405,312 | 379,241 | 95,041 in 25,246 rows | 885 in 825 rows |
| after | 413,541 | 396,827 | 85,967 in 16,563 rows | **209 in 151 rows** |

| v4.7 | texts | exact | over | under |
|---|---:|---:|---:|---:|
| before | 992,242 | 927,998 | 120,748 in 59,695 rows | 5,206 in 4,549 rows |
| after | 996,732 | 960,505 | 88,572 in 35,842 rows | **489 in 385 rows** |

**685 of the 825 v3 under-counting rows were fixed and none regressed.** Eleven rows are in the
after list and not the before list; every one is a probe this campaign bought after the before-scan
had already run, and the model at the start of the day under-counted every one of them by the same
amount — six dotted-İ rows of §12.2, two Thai-phinthu sweep rows, `x ͣabc x`, and the Syriac
`x ݀ͅ x` of 14.6. The after denominator is larger for the same reason: about 8,000 probes were
bought during the day. v4.7 reads the same way: 4,169 of its 4,549 under rows fixed, five in the
after list and not the before list, and the pre-campaign model under-counted all five. That check —
re-price every new under row against the OLD model — is what
separates "a probe we had not bought" from "a row we broke", and it is the check that caught the
one place this campaign did break something (14.4).

### 14.6 What is still open

* ~~**The sweep is not finished** … U+0C03, the unswept blocks~~ — **closed by §15**: the fifth
  pass folded in the forty marks whose grids the cache already held, and U+0C03 was never a killer
  at all.

* ~~**Three marks are over-priced at a stray run head, by a constant.**~~ **Closed by §16**: the
  constant was the forced raw-byte floor, and the floor was standing in for the missing word
  boundary beside it. §12.3's prediction — "a marker rule cannot split two stray marks that way; a
  piece can" — was right that it is a piece question, and the piece was one the mark already had.
* ~~**§12.2's dotted İ is unchanged.**~~ **Closed by §15.3**: the words are title-case, and İ is
  transparent to the no-other-capitals test.
* ~~**A Syriac dot with a rider is one under.**~~ **Closed by §15.4**: the absorb clause predated
  §14 and is gone.
* ~~**A word after a stray-mark run is one over on some hosts and one under on others**, and no
  spelling of that boundary gets both.~~ **Closed by §16**: there was a third spelling, and the
  reason the first two both failed is that the mark's own price was wrong at the same time. The
  word after a baseless mark is not a next word at all — it is the rest of THAT word.
* **`x िी x` = 11 on v3 and 15 on v4.7.** §12.1 listed it as an exact control; it is exact on v4.7
  and one OVER on v3, and always was. Two adjacent Devanagari vowel signs with no consonant, which
  is not a shape the corpora contain.

### 14.7 One virama is not one, and being DEFINED is how it hid

**Measured 2026-08-10.** 14.6 filed U+0E3A and U+0C03 under "already killers, so the residue is a
head price". That was an assumption about two characters, not a measurement of them, and it was
wrong about the first.

`is_killer` has two halves, and the docstring is proud of the difference: the 65 viramas are
**DEFINED** by canonical combining class 9 rather than listed, because defining them says honestly
where the rule comes from. A defined population also has no membership test, so no member of it had
ever been asked. Asking all 121 characters the predicate claims — ours against the oracle, no
derived frame, on a CONSONANT of each character's own script, which is the only host that can
answer:

```
                       x HMH x    HMH    x HM x   x HMHH x   x HHMH x
U+0E3A ก phinthu         +2       +2       +1        +1         +1     both families
U+0E48 ก mai ek           0        0        0         0          0     script-mate control
U+094D क, U+09BC ক, U+0BCD க, U+0C4D క, U+0D4D ക, U+0DCA ක, U+103A က, U+10A3F 𐨐   all 0
```

**The two frames of 14.1 cannot see this and reported "inside the word" for all nine.** For an
accent the two spellings differ in how many markers are written; for a Brahmic killer they differ
in where a single ⟨eow⟩ sits, so the frame reads `m`/`m+1` for the Devanagari virama exactly as it
does for the phinthu. An instrument that answers uniformly across a population it was not built for
is not evidence — the direct ours-vs-oracle comparison above is, and it separates them at once.

U+0E3A is now the only member of `constants.NON_KILLERS`. It reads +2 in Thai because the split is
not there to be made, and the SAME misreading is an under-count wherever the phinthu has no letter
in front of it and the `_KILLER` branch writes no boundary at all — `!ฺ` = 12 / 16 against our
10 / 14, and `1ฺ` `[ฺ]` `[文ฺ]` `◌ฺ` `!ฺ!ฺ` alike. As an ordinary mark it is the word's own material
after a letter and a stray-mark run after anything else, which is what those rows measure.

Every cached text containing the character, both families, both readings:

| | texts | exact | over | under |
|---|---:|---:|---:|---:|
| v3, as a killer | 72 | 17 | 294 | 63 |
| v3, as an ordinary mark | 72 | **69** | **280** | **0** |
| v4.7, as a killer | 139 | 25 | 206 | 136 |
| v4.7, as an ordinary mark | 139 | **123** | **184** | **0** |

Over-count falls with under-count again — the §14 signature of a boundary in the wrong place rather
than a missing piece. Across the whole cache v3 goes 209 tokens under in 151 texts to **152 in 112**,
and no group in the residue is new. Gates unmoved to the digit: UDHR 338/501 v3 and 472/501 v4.7 and
v5, mass 0.1876% and 0.0584%; Rosetta 1741/1741, holdout 250/250, MultiPL-E 22/22; 219 tests pass.

**U+0C03 TELUGU VISARGA is not the same shape and is NOT fixed.** It is exact in-script in every
frame that has material on both sides of it — `x కఃక x` `కఃక` `x కఃక క x` — and wrong only when
its word ends there: `x కః x` reads +1 on v3 and +2 on v4.7, and `!ః` `[ః]` `[文ః]` read one UNDER
on both. Myanmar U+103A asat reads +1 on that same word-final shape and nowhere else. So this is a
border question about a killer run at a word edge, not a misclassification, and the ~23 texts it
holds are the largest remaining under-count population. It is listed, not attributed.

## 15. Every under-counting text, accounted for — and the residue is two probes

**Measured 2026-08-10.** The assignment was the whole cache: every text ever measured against
either family, probe grids included, re-tiled and grouped. The fresh baselines — v4.7 had not been
re-scanned since §14.7 landed, so its stale 489 was never the number — were **152 tokens under in
112 texts on v3** and **359 in 306 on v4.7**. Every group in both lists is now either fixed with a
measured rule or listed with the probe that fails to decide it, and after the campaign the whole
of both caches under-counts by **one token in one text per family**, the same recorded shape on
each side (§14.6's stray-mark word boundary: `x ͣabc x` on v3, `x ͣthe x` on v4.7). **§16 closed
that last row too, so the number below is now zero on both sides.**

### 15.1 The inventory, both families

| group | v3 texts | v4.7 texts | disposition |
|---|---:|---:|---|
| forty unswept separator marks | 40 | 242 | fixed — `SEPARATOR_ANNOTATIONS`, fifth pass |
| U+0C03 Telugu visarga | 23 | 17 | fixed — word material + `ః⟨eow⟩` piece |
| U+0CF3 Kannada anusvara (Unicode 15.0) | 2 | 16 | fixed — WORDY; our tables are 14.0 and called it Cn |
| ⟨caps⟩ on caseless-letter spans | 36 | — | fixed — `mark_case` blocks ⟨caps⟩ only |
| dotted İ words (§12.2 + corpus) | 6 | 26 | fixed — title-case ⟨shift⟩, İ transparent |
| Syriac dot + rider | 2 | 2 | fixed — absorb clause removed |
| Greek all-caps final sigma | 2 | — | fixed — oracle lowers Σ→σ without Final_Sigma |
| `⁉️` (VS16 in a punct body) | — | 1 | fixed — selector rides its base in `_is_borderable_text` |
| emoji ⟨bow⟩ loss after format chars | — | 1 | fixed — astral is not punct KIND; mixed runs borderable |
| stray-mark word boundary (§14.6) | 1 | 1 | listed then **fixed — §16**, the mark and the letter are one word |

The counts sum to each family's list (the Shona/Japanese document and the Devanagari `परिएाजनाÓ`
row are inside the caseless-⟨caps⟩ 36; the Sorani document carried both of the last two v4.7
defects at once).

### 15.2 The visarga, and the character our Unicode tables have never met

U+0C03 sat in `EXTRA_KILLERS`, and §14.7 called it "a border question about a killer run at a word
edge". It is not a killer at all. It is a SPACING mark — Mc, ccc 0 — and the killer reading was
wrong both ways at once, the §14 signature: one UNDER on every baseless non-space shape (`!ః`
`[ః]` `aaఃb` `◌ః`), one OVER on every word-final space shape (`x కః x` `aః z` `x ః x`). A
20-policy enumeration over when its run writes ⟨bow⟩ and ⟨eow⟩ topped out at 17 wrong rows of 54 —
no border policy fits, because the character is not a separate run. As plain word material with a
`ః⟨eow⟩` piece (witnessed on the fixed eow template, `.ヲః.` = 13/17, cost 1 in both families) all
178 cached rows and 46 bought predictions are exact, in-script shapes included. The rival that
survived longest — a stray-mark word, the letter after keeping its own ⟨bow⟩ — is refuted by one
probe: `ఃꝛ` = 13/18, the visarga FUSING into the ꝛ-word, one token under the severed spelling on
the letter that has no suffix piece to collapse the difference. Mn stray marks measured the
opposite way in §14.4's 38 rows; a spacing Mc is claimed by the letter alternative, and a
combining Mn is not.

U+0CF3 is the same shape from a blind spot: assigned in Unicode 15.0 as the Kannada spacing
anusvara, unknown to our 14.0 tables, classified Cn → HARD, no word model. WORDY alone prices all
27 cached rows and eight in-script predictions (`x ೞೳ x` `ೞೳೞ` `x ೞೳ 5`) exactly, both families.

**Myanmar U+103A asat is NOT the third member.** §14.7 put it beside the visarga; asked over its
2,383 v3 / 3,487 v4.7 cached rows, the killer reading is exact on every one and the word-material
rival (with or without an `်⟨eow⟩` piece) is wrong on thousands. Its word-final +1 stays on the
over side of the ledger.

### 15.3 Case, three ways

* **`str.isupper` lies about caseless letters.** `ヲBUTTヲ`, `ロデオFUCK`, `BODYの`,
  `அறிவியலNATIONAL`, `परिएाजनाÓ` all pass it, and the ⟨caps⟩ our v3 model wrote is one to three
  tokens cheaper than the literal spelling the oracle uses. A caseless LETTER anywhere in the span
  now blocks ⟨caps⟩ — and only ⟨caps⟩: blocking ⟨shift⟩ too was tried, and the full-cache re-scan
  caught it before it shipped (twenty `.Collectionヲ.`-family bow-template witnesses ±1, the
  Assamese `Gৰ`/`Gলৈকে` spans −2). Eight of ten framed probes discriminate the spellings; every
  one picks literal.
* **§12.2 was a title-case question, not a tile question.** `Hnovunİ` takes ⟨shift⟩ with the İ
  literal in the lowered body — İ is transparent to the no-other-capitals test, and blocks only at
  the span head, where ⟨shift⟩ would assert a lowered first letter İ cannot supply. All thirteen
  §12.2 rows step off their bought lowercase counterparts by exactly the ⟨shift⟩ (`x Hnİ x` = 14 =
  1 + `x hnİ x` … `x Hüseynovunİ x` = 18 = 1 + `x hüseynovunİ x`), and so do two shapes never
  measured before (`x Hnİvo x`, `x Hİk x`), in both families. The corpus rows the v4.7 list held —
  Komi `Тшыгъялİны`, Azeri `Hüseynovu…`, Turkish `Kuvarsİz`, Zazaki — land exact with them. The
  old reading, "a rule over a tile five tiles before the İ", was the literal tiling's
  coincidences: `HHnovunİ`, `HNovunİ` and `hnovunİ` are not title-case, so their piece never
  budged.
* **The oracle's ⟨caps⟩ lowering is simple, and Python's is not.** `'ΣΚΙΕΣ'.lower()` applies
  Unicode's Final_Sigma context rule and produces `σκιες`; the oracle's caps body is `σκιεσ`, σ
  everywhere. `x ΣΚΙΕΣ x` = 16 is the σκιεσ spelling (σκιες reads 14, literal 21), and every caps
  word without a final sigma is exact under both spellings — which is why the defect survived
  every grid until two Greek documents were localized in situ. Both attempts that failed first:
  final-sigma-aware lowering (numerically a no-op — our lowering already produced ς) and literal
  all-caps Greek (+5 to +17 on four rows).

### 15.4 Two clauses that outlived their evidence, and two predicates asked per run

The Syriac absorb clause — a non-vowel mark after U+0740–074A rides the killer run — predated §14:
its motivating row `x ݂́ܒ x` has the ACUTE as rider, and the acute joins the run as a killer in
its own right since the accent sweep. Every rider the clause still touched read one under
(`x ݀ͅ x` = 16/20). Removed, the stray-word spelling is exact on ten predictions per family
(`x ݀ͣ x` `x ٰ݀ x` `݀ͅ` `x ݀ͅ 5` `x ݀ͅͅ x` `x ݀ͅa x` `5݀ͅ5`, controls `x ݂́ܒ x` `x ݂ܶ x`) and
on all 547 v3 / 1,294 v4.7 cached rows containing the dots.

The Sorani document carried two border defects at one boundary shape: an astral emoji was punct
KIND, so a format character in front of one glued into a markerless sub-run and lost its ⟨bow⟩
(`📐 ‎📝` −1, against `文 📐 ‎文` exact — the kind split saves the LRM against an ideograph, the
astral exclusion now saves it against an emoji); and a MIXED punct/symbol/format run failed all
three homogeneous predicates and lost its markers even split (`🎓 ‎⏰`). The gate is per character
now — `_is_borderable_text` — and the Mongolian row's `⁉️` is the same lesson for a variation
selector: it rides its base in the punct test as it always did in the symbol test.

### 15.5 What it cost, and what would not fit

The under side, whole cache: v3 **152 tokens in 112 texts → 1 in 1** over 413,902 texts, v4.7
**359 in 306 → 1 in 1** over 997,373. Both residues are the same U+0363 row. Over-count fell with
under on every population that was a rule: the forty marks alone were carrying 2,200 tokens of v3
over-count and 5,120 of v4.7's alongside their unders, the visarga 13 and 89, U+0CF3 3 and 9 — all
now zero. The three replay corpora — Goldfish, Glot500, FineWeb/Stack/github-code — read
**under 0 in both families** (v3 was 5 tokens, all the Tamil documents; v4.7 was 1, the Azeri İ
row), 280,276 of 286,857 rows exact on v3 and 289,129 of 302,418 on v4.7, with over-count down
net in both despite the surfaced Tamil +2s.

One trade is reported rather than celebrated: 26 Tamil documents and the Shona/Japanese one now
read +2 over where they read −2/−4 under. The caps span they share (`லிKARPURAVALLI`) prices
literal-exact framed and in the one document whose only defect it was; the +2 that surfaces in the
others is a pre-existing over-count the under-count had been masking. Four more +1s
(`வகையானADSP` `YOUTUBEல` `ดีINTRO` `តារARTIST`) are the same arithmetic, and all four spans
price literal-exact framed (`x YOUTUBEல x` = 17 …).

One population the campaign's own instrument manufactured, and then closed: the in-situ window
deletion that localized the Mongolian row produced `…ВЭ️ 2019` — a variation selector with its
base deleted — and the full re-scan surfaced it as a new under row. Re-priced against the OLD
model it was one under there too, which is the check that marks it "a probe we had not bought"
rather than "a row we broke". The shape generalizes: a VS-only run at a single-space border takes
the punctuation markers (`5 ️ 5` two under with none written, seam-cancelled against a word,
killed by a space run — the same three laws every punct run obeys), and all 712 cached rows
holding a selector now price exactly in both families.

What did not survive contact with the measurements, at the same length as what did: the blanket
caseless block on ⟨shift⟩ (caught by the full-cache re-scan, 43 rows); the 20-policy border
enumeration for the visarga (best policy 17/54 wrong); the visarga as a stray-mark word (`ఃꝛ`);
the visarga floor-priced when baseless (+1 everywhere against the char piece); asat as word
material (thousands of rows); final-sigma-aware ⟨caps⟩ lowering (a no-op — Python already does
it; the oracle is the one that does not); literal all-caps Greek (+5 to +17); an emoji ⟨eow⟩ at
the space border (refuted by `文 📐 ‎文` and `1 📐 ‎1` exact); and the m/gap frames for the forty
marks, not because they failed but because they were never needed — the 45-shape grids were
already in the cache, and the direct ours-vs-oracle table over 5,646 rows is the stronger
instrument.

The held-out gates, read once at the end, moved the way they should: UDHR **338 → 340** exact on
v3 (mass 0.187%) and **472 → 474** on v4.7 and v5 (0.058%); Rosetta 1741/1741 in all three
families, the 250-document holdout 250/250, MultiPL-E 22/22; 219 tests pass.

## 16. The last under-count: a baseless mark and the letter after it are ONE word

**Measured 2026-08-10.** The whole cache under-counted by exactly one token in one text per family
when this campaign opened — `x ͣabc x` = 14 on v3 and `x ͣthe x` = 18 on v4.7, both the U+0363
shape §14.6 filed as undecidable. It is decidable. Both families now under-count **zero tokens in
zero texts** over 505,886 v3 and 1,009,746 v4.7 cached texts, and the same change removes 462 v3
and 4,581 v4.7 tokens of over-count.

### 16.1 Why the two candidate spellings both failed, and what the third one is

§14.6 tried the word's ⟨bow⟩ written (severed) and dropped (fused) and found each right where the
other was wrong. That is the signature of TWO errors, not one, and they were on opposite sides of
the same seam: the boundary was wrong, and the mark's own head price was wrong with it.

The word after an unattached mark run is not a next word. It is the rest of THAT word:

```
severed   ⟨bow⟩M            ⟨bow⟩abc⟨eow⟩
fused     ⟨bow⟩M abc⟨eow⟩                      one word, and the mark is its head
```

which is what a baseless Syriac vowel (§7's `_syriac_vowel`), the Telugu visarga and the Kannada
U+0CF3 (§15.2) were each measured to do already, one script at a time.

### 16.2 The frame that cancels the mark's own price

The two spellings differ by the word's ⟨bow⟩ and by nothing else, so the mark's price — whatever
it is, wrong or right — appears identically on both sides. Vary the right-hand word instead: the
severed prediction moves with `cost(⟨bow⟩W⟨eow⟩) − cost(W⟨eow⟩)`, which is a vocabulary accident
of W, and the fused prediction cannot move at all. **A spread across W refutes; a constant is
consistent, and the constant is the mark's own price.**

```
ours − oracle, `x ͣW x` and `!ͣW x`, v3 / v4.7

W            x       abc      the       ก       ꝛ       ся
severed     0/0     -1/0     0/-1     +1/+1   +1/+1   +1/+1
fused       0/0      0/0      0/0      0/0     0/0     0/0
```

22 marks — the combining Latin and Cyrillic letters (U+0363, U+036F, U+1ABF, U+1ACC, U+1DD3,
U+2DE0, U+2DED, U+A674, U+A69E), U+0345, the Hebrew points, the Arabic harakat, superscript alef
and small-high annotations, Samaritan, Thaana, Tibetan, Thai and Buginese — each on those six
words in two frames, both families, 528 oracle rows. **Every mark reads a spread under the severed
spelling and a constant under the fused one. Not one reads it the other way round.** `x ͣabc x`
and `x ͣthe x` are two cells of that table, and §14.6's `x ͣก x` `x ͣب x` over-counts are two more.

The 38 `<mark>ꝛ` rows §14.4 cited against dropping the letter's ⟨bow⟩ do not bear on this. Of the
2,435 cached `<mark>ꝛ` rows exactly 243 are stray-mark runs; the five marks §14.4 names — U+1BE6,
U+2CEF, U+302A, U+3099, U+A8E0 — became `SEPARATOR_ANNOTATIONS` in §15's fifth pass and are killer
runs now, and every astral mark is HARD and takes no word model at all. The evidence that once
refused this spelling had left the population before this campaign began.

### 16.3 The head price was the other half, and it was the floor

`stream_plan` forced the first mark of a stray run through the RAW byte floor — the byte-prefix
vocabulary with whole-character pieces deliberately left out — on the reading that "the same
codepoint is a piece inside a letter run, but here the pretokenizer's letter alternative cannot
claim it". With the word's ⟨bow⟩ wrongly written, every mark that owns a unit piece read one under,
and that floor cancelled it. Separate the two and the floor is a pure over-charge on exactly those
marks:

```
ours − oracle with the floor / without it, nine frames each
(`x Mabc x` `!Mabc x` `x Mthe x` `x M x` `x M` `!M` `x M5 x` `x Mꝛ x` `Mabc x`)

U+064F  U+0E38  U+05B0     +1 / 0  in all nine, both families
U+0F72  U+064B             +1 or +2 / 0  (the +2 frames are the ones with no letter after)
U+0363  U+05B1  U+2DE0  U+0670  U+0EB8      0 / 0  — unmoved either way
```

That closes §14.6's "three marks are over-priced at a stray run head, by a constant" without a
piece being mined: the piece was one the mark already had and the encoder was refusing it. The
forced-floor mechanism had no other caller, so `_FLOOR_G`, `stream_plan`'s second return value and
the floor branches of `engine.tile` and `witness` are gone with it. The later removal of the
superseded dotted-İ rule also removed the second byte floor it had kept alive.

### 16.4 A fused span takes no case marker

A case marker fires on a WHOLE span, and this span's head is the mark, which is neither an
uppercase letter (⟨shift⟩ asserts a lowered first letter) nor a case at all. Literal, then —
measured on 57 rows per family over three marks:

* **⟨shift⟩ kept reads +1**: `x ͣThe x` = 13/18, `x ͣJohn x` = 14/19, `x ͣHello x` = 14/18,
  `x ͣXyz x`, and `ͣThe x` `!ͣThe x` `x ͣThe` `x ͣͣThe x` at every other position.
* **⟨caps⟩ kept reads −2 to −5** where v3 has ⟨caps⟩ at all: `x ͣHELLO x` = 17, `x ͣЖЖЖЖ x` = 21,
  `x ͣЖЖЖЖЖ x` = 23, `x ͣHELLOX x` = 18.
* **Literal is exact on all 57 in both families**, including `x ͣABCD x` `x ͣPARIS x` `x ͣabcd x`
  `x ͣАбв x` where the spellings coincide and settle nothing, and the unfused controls
  `x The x` `x Abc x` are untouched.

It is the İ head rule of §15.3 generalized, and it arrives from the other direction: ⟨shift⟩ blocks
at the span head because the head cannot supply a lowered first letter, whoever the head is.

### 16.5 What it cost, over every text that could move

Only a text holding a BMP non-killer combining mark can change, which is 47,140 of the cached rows.
Priced both ways, before and after:

| | rows | exact | over | under |
|---|---:|---:|---:|---:|
| v3, before | 9,725 | 8,118 | 14,347 in 1,534 rows | 103 in 73 rows |
| v3, after | 9,725 | **8,504** | **13,885 in 1,221** | **0** |
| v4.7, before | 37,415 | 27,162 | 40,925 in 10,191 rows | 71 in 62 rows |
| v4.7, after | 37,415 | **30,065** | **36,344 in 7,350** | **0** |

**No row in either family got worse, and none that was exact stopped being exact.** Over-count
fell with under-count again — 462 tokens on v3 and 4,581 on v4.7 — which is the §14 signature of a
misplaced boundary rather than a missing piece, twice over: once for the ⟨bow⟩ and once for the
floor it was hiding behind. The under rows are larger than §15's residue of one because ~900 probes
bought during this campaign are in the denominator; every one of them was under-counting by the old
model too, which is the check that separates "a probe we had not bought" from "a row we broke".

The whole-cache scans, the numbers this campaign is judged on:

| | texts | under before | under after |
|---|---:|---:|---:|
| v3 | 505,886 | 1 token in 1 text | **0 in 0** |
| v4.7 | 1,009,746 | 1 token in 1 text | **0 in 0** |

The held-out gates, read once at the end: UDHR **346 exact on v3, unmoved** (mass 0.096%) and
**474 → 475 on v4.7 and v5** (0.058%); Rosetta 1741/1741 in both families, the 250-document
holdout 250/250, MultiPL-E 22/22; witness coverage 100% in both vocabularies with no piece added or
removed; 219 tests pass.

### 16.6 What this does not close

* **`x िी x` = 11 on v3** (§14.6) is untouched: two Devanagari vowel signs with no consonant, one
  OVER on v3 and always was.
* The over-count that remains in the affected population — 13,885 tokens on v3 and 36,344 on v4.7
  — is overwhelmingly ordinary vocabulary coverage in texts that merely contain a mark somewhere,
  not a boundary question. Nothing in it under-counts, which is the property that matters: the
  model no longer believes anything is cheaper than it is.

## 17. An astral run takes no border marker — and the last five UDHR documents were two things

**Measured 2026-08-10.** Five documents read over 1% in *both* families and nowhere else did:
Thai (+3.96% / +2.66%), Thai (2) (+4.33% / +2.38%), Burmese (+2.33% in both), Mon (+1.88% in
both) and Chakma (+1.54% in both). They are now **exact in both families**, and no document in
either is over 1% any more.

The identical-in-both-families half of that list was the tell, and the brief that opened this
campaign said so before any probe was bought: v3 carries 48,225 pieces and v4.7 15,147, so a
residual the two share to the token is not vocabulary. It was two structural facts and eleven
ordinary word pieces, and the two halves were found by different instruments.

### 17.1 The astral law, and the two branches that were missing it

`_marks_like_punct` and `_is_symbol_text` have excluded ASTRAL characters since the emoji work of
§15.4 — an emoji takes no border marker. The digit branch and the terminal-separator branch never
got the same clause, and each was writing markers the oracle does not write.

Two exhaustive sweeps, not samples, in both families:

```
30 astral terminal separators, EVERY one Unicode has
   x aK 5   5 Ka x   x aK x   5 K 5   x aKb x
     +1       +1        0       +2       0        Kharoshthi, Brahmi ×3, Kaithi, Chakma ×2,
                                                  Sharada, Khojki, Khudawadi, Grantha, Newa,
                                                  Tirhuta, Siddham, Modi, Takri, Ahom, Dogra,
                                                  Dives Akuru ×2, Nandinagari, Zanabazar ×2,
                                                  Soyombo, Bhaiksuki, Masaram ×2, Gunjala, Kawi ×2

72 astral border digits, one or two from each of the 56 astral number blocks
   x D 5    文 D 文    x D x    5 D 5
     +1       +2         0       +2
```

Not one character and not one family dissents, and the deviation is exactly the number of markers
the frame makes visible: `x aK x` and `x D x` read 0 because the seam deletes both against the
padding's words, which is why every earlier Latin-framed probe of these characters was silent.

**The BMP controls are what make it an astral rule rather than a change to killers or digits.**
`่` `်` `្` `्` `்` `́` `ٰ` `݀` read 0 in all thirteen killer frames in both families, and every
row of `_digit_eow`'s BMP grid is unmoved.

It is per BORDER CHARACTER, the same way every other rule in `normalize.py` is — a MIXED run keeps
the marker on the side whose own character is BMP:

```
x a𑄴่ 5   exact WITH the ⟨eow⟩ (NFC orders the astral first, the Thai mai ek last)
x 𑄶５ 5    exact WITH the ⟨eow⟩
5 𑄴่a x   one over — the ⟨bow⟩ sits on the astral side
x ５𑄶 5    one over — the ⟨eow⟩ sits on the astral side
```

One clause had to move with it, and the row that names it is `𑄴a`: the `has_own_bow` head test
counted a `_KILLER` first run as supplying the frame's ⟨bow⟩. A run that no longer writes one
cannot, and `𑄴a` `𑄴 a` `𑄴 5` and `𑄴` alone each read one UNDER until that was fixed —
the astral digit rows were already right, because `_digit_bow` had gone False for them in the same
change. `_takes_right_border` takes the same qualification, so the contraction seam still sees the
population it was measured on.

The re-scan is 1,007 probes per family — 30 astral killers and 8 BMP controls × 13 frames, plus 57
astral number blocks × 9 — and reads **0 wrong in both families**.

### 17.2 Chakma was ONLY that, and the sweep that established it

Chakma has no Goldfish config, no FineWeb-2 config, no Glot500 config and no open FLORES; the
`ccp-Latn` in GlotCC is the Latin orthography. So there was no corpus to mine and the question had
to be settled on the script's own material:

* **every letter × mark pair, 722 probes** (38 letters × 19 vowel signs and marks) — 0 wrong, so
  the oracle holds no Chakma bigram either;
* **181 single codepoints** of Thai, Myanmar and Chakma that neither vocabulary has, on the `char`
  template `a{}a` — **none reads cost 1** in either family, which is also what refuses `ฉ`, the
  single Thai letter the fitness enumerator scored on 62 rows;
* random 3-to-4-syllable words, conjuncts, digits, dandas and multi-word phrases — every failure
  reduced to a word-final `𑄴`/`𑄳` before a space and a run that opens no word, which is 17.1.

Chakma UDHR went +512 → 0 in both families on the astral law alone. **A script with no corpus is
not a script with no answer**, and the reverse of §9's lesson: there the missing corpus did not
matter because the defect was structural, and here it did not either.

### 17.3 Myanmar: one piece, on the template §7 predicted would find it

§7 left an open half: "the five killers with a fused `K⟨eow⟩` piece in the real vocabulary — Tamil,
Sinhala, Malayalam, Devanagari, Bengali nukta — now pay for a marker we cannot spell", and
predicted Thai, Khmer and Myanmar had none. Myanmar has one, and it is the asat:

```
digit_eow, `1{} a`, cost = raw - base + 1 - 3        v3      v4.7
  U+103A MYANMAR SIGN ASAT                            1        1     <- the piece
  U+1039 virama · U+1037 dot below                    2        2
  U+0E48 U+0E49 U+0E4C Thai · U+17D2 U+17CB Khmer     2        2
  U+1036 anusvara · U+0E4A U+0E4B · U+17C6 U+17C7     3        3
```

Thirteen same-template controls at cost 2 or 3, and `း⟨eow⟩` (U+1038 visarga), which both files
already ship, reads 1 beside it. The corpus court is `x {} x` around real words — the `raw`
template cannot reach the piece at all, because the message end is not a space and the encoder
writes no ⟨eow⟩ there:

```
600 distinct Burmese words (Goldfish mya_mymr)   600 repaired, 0 pushed below, 0 already exact
300 distinct Shan words    (Goldfish shn_mymr)   300 repaired, 0 pushed below, 0 already exact
```

in both families. With it, `mine_own2.py` proposes nothing at all on 2,500 Myanmar wordy runs in
either family: Myanmar words were one piece away from complete.

### 17.4 Thai was a cross-port, and both directions were already on disk

v3 and v4.7 each held Thai pieces the other lacked, and each family's missing set is exactly what
its own probe buys:

```
into v4.7   ัก  ัง  ัน  ับ  ือ                 mid,  .ヲXヲ. = 20, cost 1
into v3     ที⟨eow⟩ ั⟨eow⟩ ี⟨eow⟩ ื⟨eow⟩ ู⟨eow⟩  eow,  .ヲX.  = 13, cost 1
            ีย                                  mid,  .ヲXヲ. = 16, cost 1
```

Five of those `mid` pieces are five of §1's seven — the batch that removed 7,528 tokens of
over-charge and introduced 8,469 of under-count on 2026-08-07, and was discarded. **They are not
false pieces and never were.** What was false was the model they were applied to: the akshara,
border-marker, accent and boundary work of §§7, 14 and 15 has since moved thousands of tokens
under them. Judged one at a time against real Thai in a frame, each repairs dozens of distinct
words and pushes **none** below its recorded count:

```
ัน  189 words repaired / 0 below      ั⟨eow⟩  42 / 0      ี⟨eow⟩  68 / 0
ือ   47 / 0     ับ  31 / 0     ัง  23 / 0     ัก  12 / 0
ื⟨eow⟩  36 / 0   ู⟨eow⟩  46 / 0   ที⟨eow⟩  15 / 0   ีย  23 / 0
```

**That refusal is the whole difference between this campaign and §1's**, and it is why §1's
correction insisted on it: a batch hides its own failures, and the seven were judged as a batch.

The independent check is that a miner with no knowledge of the cross-port re-derives it.
`mine_own2.py` — propose every bounded span of an over-charging run's marked stream, decide it on
its own fixed template, then court it alone — was run over 2,500 wordy runs of Goldfish Thai plus
FineWeb-2 Thai and returned **exactly those five on v4.7 and exactly those six on v3**, closing
every host in one round and probing 400 candidates to do it. What it refused is the useful half:
`อ⟨eow⟩` `ือ⟨eow⟩` `คือ` `หรือ` `⟨bow⟩คือ⟨eow⟩` `่⟨eow⟩` `้⟨eow⟩` `ที` `นี` `ปี` `ฉ` `ฉัน` `คุณ`
all price at 2 to 4 tokens on their own templates. `อ⟨eow⟩` is the candidate §1 named and killed on
`กอ`; its own probe kills it too.

### 17.5 What it cost, measured before and after on everything

Row level, against recorded counts, on the corpora the campaign drew from and on two it did not
(Shan, and a FineWeb-2 Mon slice that is mostly legacy-encoded Burmese):

| | v3 exact | v3 over | v4.7 exact | v4.7 over |
|---|---|---:|---|---:|
| `tha_thai` 1,000 Goldfish rows | 523 → **1,000** | 919 → 0 | 472 → **1,000** | 781 → 0 |
| FineWeb-2 Thai, 1,000 rows | 347 → **994** | 4,453 → 7 | 426 → **999** | 2,382 → 2 |
| `mya_mymr` 1,000 rows | 512 → **998** | 1,733 → 2 | 512 → **998** | 1,733 → 2 |
| `shn_mymr` 1,000 rows | 471 → **998** | 973 → 2 | 473 → **999** | 971 → 1 |
| FineWeb-2 `mnw_Mymr`, 600 rows | 71 → **597** | 4,591 → 3 | 71 → **597** | 4,591 → 3 |

Under-count is 0 before and after on every one of those rows. The differential over the whole
measurement cache — every text holding a Thai or Myanmar character, an astral killer or an astral
number, tiled twice, once against the tree at HEAD and once against this one:

```
v4.7   79,919 texts   exact 61,674 -> 79,787   over 51,585 -> 210   under 0 -> 0
v3     35,369 texts   exact 29,927 -> 35,267   over 22,536 -> 144   under 0 -> 0
       rows broken 0        rows repaired 18,113 (v4.7) and 5,340 (v3)
```

**Over-count falls with under-count held at zero and not one row broken**, which is the §14
signature of a boundary in the wrong place plus the §13 signature of missing vocabulary, in the
same campaign.

The whole-cache under scan afterwards reads 71 tokens in 62 texts on v4.7 and 103 in 73 on v3 —
**every one of them under-counts identically on the tree at HEAD, and not one holds a character
this campaign touched.** They are `x ͣÉcole x`-shaped stray-mark probes bought into the shared
measurement cache by a concurrent campaign on §14.6's open boundary, not a regression here. That
check — re-price every under row against the OLD model — is §14.5's, and it is the only thing that
separates "a probe we had not bought" from "a row we broke" when two campaigns share one cache.

The held-out gates, read once at the end: UDHR **346 → 353** exact on v3 (mass 0.0959% →
0.0284%) and **474 → 481** on v4.7 and v5 (0.0577% → **0.0067%**), with the 1–5% band going
**5 → 0** in both families and no document under-counting in either; Rosetta 1741/1741, the
250-document holdout 250/250 and MultiPL-E 22/22 unmoved; 219 tests pass.

### 17.6 What is left, and one instrument note

The worst document in each family is now Tamil at +0.75%, in both — a script this campaign did not
touch and the largest remaining pool in the corpus. **Closed by §18**, on two pieces — and the
identical-in-both-families reasoning that opened *this* campaign does not carry over to that one:
18.1 says why it was no evidence at all there. On v3 nine Latin-script documents sit between
+0.4% and +0.92% (Oromo, Sango, Yanomamö, Catalan, Turkmen, North Saami, Sidamo, Azerbaijani),
which is ordinary v3 word vocabulary. Three Myanmar rows and seven Thai ones still over-charge by
a token; each holds Myanmar digits or Latin material glued to the script, the mixed-span shape
§13.7 records as needing a frame of its own.

The instrument note is about the fitness enumerator, and it is §1's warning arriving in a new
disguise. Asked for one-piece explanations of 138 over-charging Thai rows it returned 2,178
candidates and ranked `ัน` first at 83 rows — correct — and `ฉ`, a single Thai letter, second at
62. `ฉ` costs two tokens on the `char` template in both families. **A candidate's rank in a
fitness enumeration carries no evidence at all**; it decides only which probe gets bought next.

## 18. Tamil was two pieces, and the identical-in-both-families tell did not apply

**Measured 2026-08-11.** §17.6 left Tamil the worst document in both families — +0.751% and
+0.750%, **+79 tokens in each** — and the largest remaining pool. Both documents now reproduce
exactly, on two pieces: `்,⟨eow⟩` and `்.⟨eow⟩`, the Tamil virama fused to a comma or a full stop
at a word-closing border.

### 18.1 The tell that opened §17 does not transfer, and checking that was the first thing worth doing

§17's brief reasoned that a residual identical across vocabularies of 48,232 and 15,153 pieces
cannot be vocabulary, and it was right there. Repeated for Tamil it is **not an argument at all**,
and one query says why:

```
Tamil-bearing pieces      v3 113     v4.7 97     shared 97     v4.7-only 0
v3's extra 16 (அ இ உ எ ங சச டட நந னன பப மம யய ரர றற லல வவ) change no row of the 1,000
```

v4.7's Tamil vocabulary is a SUBSET of v3's and the difference is inert, so the two families were
always going to read the same on Tamil under either hypothesis. All 1,000 Goldfish `tam_taml` rows
carry an identical delta in the two families — which measures the vocabularies' overlap, not the
tokenizer. **A cross-family tell is only evidence where the two vocabularies actually differ on the
script in question**, and that is one cheap query to check before spending anything on it.

### 18.2 What did decide it: localize first, and Tamil is the extreme case

§0's method, run on the 484 over-charging Goldfish rows with every word of every hot row priced —
§13.2's correction, no word cap:

```
over-charge 1,461 tokens     12,225 distinct words priced alone     wrong words 0     explained 0%
```

Not one word of Tamil is mispriced. Catalan was 98% inside words and Lombard 21%; Tamil is **0%**.
So the answer to "vocabulary or structure" was neither of the two readings the brief offered: the
over-charge is entirely at the joins, and it is still vocabulary — a piece that spans a word
boundary and therefore cannot be found by any word miner.

### 18.3 The site, found in situ

`insitu_over.py` — delete a window from the real row, keep the half whose removal reduces the row's
over-count, never build a new string (§7's two instrument notes) — put nine of the ten worst rows on
a single character:

```
over 49  site '்'   …லை:நகரில[்], வடிகால…
over 32  site '்'   …து. ஆனால[்], அந்த வ…
over 28  site '்'   …ுதியாகும[்]. இந்த த…
```

The frame is one token over, and the seam is exactly the shape §1's 2026-08-08 correction named:

```
x ஆனால், அந்த x  +1      x ஆனால் அந்த x   0        x ஆனால் , அந்த x  0
x ஆனால். அந்த x  +1      x நகரில்,வடிகால் x 0      x ஆனால், 5 x     +1
x ஆனால்! அந்த x   0      x ஆனால்; அந்த x   0       x ஆனால்? அந்த x   0
x ஆனால்: அந்த x   0      x ஆனால்) அந்த x   0       x ஆனால்- அந்த x   0
```

The stream is `⟨bow⟩ஆனால⟨eow⟩்,⟨eow⟩⟨bow⟩அந⟨eow⟩…`: the killer run takes punctuation's borders
(§7), so the comma and the virama share one run. `்` and `,⟨eow⟩` are both pieces, so we spend two
tokens where the oracle spends one, and `witness._fitness_candidates` names `்,⟨eow⟩` as the one
candidate common to every comma probe.

### 18.4 The instrument: `digit_eow` reaches it, and the ヲ grid does not

§3 recorded that "no synthetic template can reach `்,⟨eow⟩`". That was true of the templates it
tried. The piece's position is `eow`, and its own `eow` template `.ヲ{}.` puts a Tamil virama on a
katakana base — §1's hazard — and in fact fails `witness.places` outright, because the message end
writes no ⟨eow⟩ for the piece to end on. **`digit_eow`, `1{} a`, places it exactly**, and the
reason it is not the ヲ hazard is checkable rather than argued: the stream span it prices,
`்,⟨eow⟩`, is character-for-character the span the corpus writes, because the killer run never
includes the letter before it. It is the template §7 predicted would find the fused killer pieces
and the one §17.3 bought the Myanmar asat on.

```
digit_eow, `1{} a`, cost = raw - base + 1 - 3           v3   v4.7
  ்,  ்.                                                 1     1     <- the two pieces
  ்;  ்!  ்?  ்:  ்)  ்-  ்”  ்/  ்%  ்…  ்|  ்'          2-3   2-3   twelve controls
```

The corpus court is `x W, V x` cut out of running FineWeb-2 Tamil — the word before the seam and
the word after it are the ones the text put there — one probe per DISTINCT left word:

```
்,⟨eow⟩   120 distinct words repaired / 0 already exact / 0 pushed below     both families
்.⟨eow⟩   120 / 0 / 0                                                        both families
்!  ்?  ்:  ்;  ்)      0 repaired / 40 already exact each                    v4.7
```

The control fires the right way round on both sides: the two pieces have something to explain on
every row, and the five refused candidates have nothing to explain on any.

### 18.5 It is Tamil's, not Brahmic

Twenty killers — Devanagari, Bengali nukta and virama, Gurmukhi, Gujarati, Oriya, Tamil, Telugu,
Kannada, Malayalam, Sinhala, Thai, Lao, Tibetan, Myanmar virama and asat, Khmer, Javanese,
Balinese, Tagalog — crossed with comma and full stop, on `digit_eow`, in both families:
**only Tamil's two read cost 1.** That independently reproduces §1's seam court, which swept the
same grid on own-script probes and kept nothing outside Tamil, and it is what makes this ordinary
missing vocabulary rather than a rule about killers.

### 18.6 What it cost, over every text that could move

A piece changes only a text whose STREAM holds its surface (§13.8), so the differential is that
set, tiled twice:

| | texts with the piece in their stream | exact | over | under |
|---|---:|---:|---:|---:|
| v3, before | 4,513 | 0 | 15,708 | 0 |
| v3, after | 4,513 | **4,511** | **3** | **0** |
| v4.7, before | 5,252 | 0 | 17,104 | 0 |
| v4.7, after | 5,252 | **5,251** | **2** | **0** |

**Not one row was broken and not one row under-counts**, and "before exact 0" is the control at
cache scale: of the 9,765 cached texts these pieces touch, not one already reproduced.

Row level on the two corpora, against recorded counts:

| | exact | over | under |
|---|---|---:|---:|
| `tam_taml` 1,000 Goldfish rows, v3 and v4.7 alike | 516 → **1,000** | 1,461 → **0** | 0 → 0 |
| FineWeb-2 Tamil, 8,391 rows (v3) | 4,984 → **8,389** | 9,010 → **3** | 0 → 0 |
| FineWeb-2 Tamil, 9,863 rows (v4.7) | 5,814 → **9,862** | 10,723 → **2** | 0 → 0 |

The whole-cache under scan afterwards reads **0 tokens in 0 texts** on both families, over 514,216
v3 and 1,010,303 v4.7 cached texts.

### 18.7 The residue is two rows, and neither is Tamil

Three tokens on v3 and two on v4.7 survive in the whole cache, in two documents:

* a Tamil/Arabic row whose Arabic is unnormalized Quranic harakat (`َضِيَ اللَّهُ عَنْ`), +2 in both
  families;
* a Tamil row with Latin glued to the script — `volleyயும்`, `அ.தூக்கத்தில்லேயே` — the
  mixed-script span §13.7 records as needing a frame of its own, +1 on v3.

Neither is the seam and neither is a Tamil word: every Tamil word in both rows prices exactly.

The held-out gates, read once at the end: UDHR **353 → 355** exact on v3 (mass 0.0284% →
0.0228%, speakers-weighted 0.0065%) and **481 → 484** on v4.7 and v5 (0.0067% → **0.0019%**,
speakers-weighted 0.0015%); **both Tamil documents go +79 → 0 in both families**; Rosetta
1741/1741, the 250-document holdout 250/250 and MultiPL-E 22/22 unmoved; no document in either
family under-counts and none is over 1%; 219 tests pass. The gate thresholds are unchanged and
their comment now carries the re-measured reading — v4.7's mean sits a factor of ten under its
bound, which is margin rather than a stale gate, and tightening it would fire on the next
campaign's ordinary churn rather than on a regression.

## 19. Sinhala and Khmer were a cross-port, and it is not transitive

**Measured 2026-08-11.** §18 left `sin_sinh` and `khm_khmr` the two largest non-Latin pools in the
v4.7 Goldfish sweep, and Sinhala the worst UDHR document in the family at +0.334%. **Four pieces
close both, and all four were already sitting in the other family's file.** The whole campaign is
one cross-port, and the interesting result is not the four kept but the nineteen refused.

The brief that opened this campaign priced the pools at 810 tokens over 1,400 rows, because that is
what the cache held when the ranking was taken; by the time the campaign started the background
buyer had finished both languages and the true pool over 2,000 rows was **1,172**. §13.1's lesson
holds without qualification — a ranking is a measurement with a date on it — and the correction
went the unusual way this time, upward.

### 19.1 The cross-family tell that §18 disarmed applies here, in its strong form

§18.1's rule is that a cross-family comparison is evidence only where the two vocabularies actually
differ on the script in question. Here they do, and the reading is not "identical, so structural"
but its opposite:

```
1,000 Goldfish rows each, against recorded counts, before anything
                v3                          v4.7
sin_sinh   1,000 exact   over    0     635 exact   over 703
khm_khmr   1,000 exact   over    0     686 exact   over 469
```

v3 reproduces every row of both languages and v4.7 does not, through the same `normalize` and
`engine` code — the families differ in their frame constants and a handful of flags, none of which
touches a Sinhala or Khmer codepoint. So a defect on one side and not the other is a vocabulary
question before a single probe is bought, and the place to look first is the vocabulary that is
already right. It is the mirror image of §17's tell rather than a contradiction of §18's warning:
a cross-family reading is evidence exactly when the two vocabularies differ on the script in hand,
and here the difference is the whole of it. As with Tamil, v4.7's script pieces are a strict
SUBSET of v3's (78 ⊂ 96 Sinhala, 76 ⊂ 81 Khmer, zero v4.7-only in either), which says which
direction the port can run.

### 19.2 Localize first, and both are Catalan-shaped

§0's method, no word cap — every distinct word of every over-charging row priced alone:

| | over-charge | hot rows | words priced | wrong words | inside words |
|---|---:|---:|---:|---:|---:|
| `sin_sinh` v4.7 | 703 | 365 | 9,399 | 311 | 699/703 (**99%**) |
| `khm_khmr` v4.7 | 469 | 314 | 4,369 | 244 | 469/469 (**100%**) |

Tamil was 0% and no word miner could reach it; these are Catalan-shaped and a word miner is exactly
the instrument. That one measurement, bought before anything else, is what said so.

### 19.3 A batch cross-port is a net disaster, and both instruments refuse the same nineteen

v3 holds 23 script-bearing pieces v4.7 lacks. Ported as a set, against the same corpus words:

```
18 Sinhala v3-only pieces, all at once     repaired 311 words   pushed 93 words BELOW the oracle
 5 Khmer   v3-only pieces, all at once     repaired 244 words   pushed 15 words BELOW
```

That is §1's 2026-08-07 shape in a new script — a batch that removes over-charge by manufacturing
under-count — and §4 says under-count is the direction nothing can undo. **Membership is per-family
and a piece that is real in a 48,234-piece vocabulary is not thereby real in a 15,159-piece one.**

Judged one at a time, the two instruments agree completely and neither was told about the other.
The v4.7 template probe first, `cost = raw − 12 + 1 − overhead`:

```
ාය       mid  .ヲ{}ヲ.  raw 20 -> cost 1      ករ       mid  .ヲ{}ヲ.  raw 20 -> cost 1
ික⟨eow⟩  eow  .ヲ{}.   raw 17 -> cost 1      ⟨bow⟩រប  bow  .{}ヲ.   raw 17 -> cost 1
the other nineteen                           cost 2 (seventeen of them), cost 3 (two)
```

Then the corpus court — one probe per DISTINCT word of the hot rows, each candidate alone, with
§18's control that the words must be WRONG without it:

| | repaired | pushed below |
|---|---:|---:|
| `ාය` | **179** | 0 |
| `ික⟨eow⟩` | **139** | 0 |
| `ករ` | **157** | 0 |
| `⟨bow⟩រប` | **88** | 0 |
| the other nineteen, worst case each | 0–2 | 0–27 |

`ඛ` repairs nothing and takes 27 words below; `⟨bow⟩ති⟨eow⟩` and `යය` 17 each; `මම` (Khmer) 12.
Not one of the nineteen repairs three distinct words. **The probe and the court partition the same
23 candidates the same way**, which is the reassuring part: had only the corpus been consulted, the
greedy cover would still have found the same four, and had only the template been consulted, the
same four survive.

### 19.4 The wider court, and why the four are the whole answer

The candidates were not taken from v3 alone. `witness._fitness_candidates` was run over every wrong
word — every single-piece addition that makes that word reproduce — which proposes 916 spans for
Sinhala and 2,865 for Khmer. Ranked by distinct wrong words explained and probed on their own
templates:

| | candidates probed | admissible on their own template | kept |
|---|---:|---:|---:|
| `sin_sinh` | 80 | 2 | 2 |
| `khm_khmr` | 120 | 2 | 2 |

The 196 refused read cost 2 or more, or the encoder does not place them in their own probe. This is
§13.6's wall again, and again it did all the work: **the net-word control never had to fire**, and
the four survivors are exactly the four v3 already ships. A greedy loop over the admissible set —
accept, re-baseline, repeat — takes both word pools to **zero over-charge in zero words** in two
rounds each and stops with nothing left to propose.

A separate 50-probe sibling grid is what says the `mid` template is not §1's ヲ hazard here rather
than merely asserting it: `ා`+18 Sinhala consonants, 5 consonants+`ා`, `ក`+20 Khmer consonants and
7 consonants+`រ`, all on `.ヲ{}ヲ.`, read **cost 1 three times out of fifty** — `ාය`, `ករ` and one
inert `ාන`. A frame that answered 1 for a Brahmic cluster because of its katakana base would answer
1 for all fifty. `ාන` explains no wrong word and was NOT taken: a candidate whose probes already
reproduce explains nothing (§1), and that applies to a candidate the template likes just as much as
to one the corpus likes.

### 19.5 What it cost, over every text that could move

A piece changes only a text whose STREAM holds its surface (§13.8), so the differential is that set,
tiled twice — v4.7 only, since v3 already ships all four:

| | texts with a piece in their stream | exact | over | under |
|---|---:|---:|---:|---:|
| v4.7, before | 2,401 | 484 | 2,813 | 0 |
| v4.7, after | 2,401 | **2,400** | **1** | **0** |

Not one row was broken and not one under-counts. Note that "before exact 484" is not zero here —
unlike §18's seam, these surfaces occur in plenty of texts that were already right, and every one of
them stays right.

Row level, against recorded counts:

| | v4.7 exact | v4.7 over | v3 (unchanged) |
|---|---:|---:|---|
| `sin_sinh` 1,000 Goldfish rows | 635 → **996** | 703 → **4** | 1,000 exact |
| `khm_khmr` 1,000 Goldfish rows | 686 → **1,000** | 469 → **0** | 1,000 exact |

The 67 Goldfish languages on disk read 56,452/58,000 exact and 2,363 tokens of over-charge, with
neither Sinhala nor Khmer in the top twelve any more. The whole-cache under scan afterwards reads
**0 tokens in 0 texts** on both families, over 547,182 v3 and 1,040,746 v4.7 cached texts.

### 19.6 The residue is four rows and none of them is Sinhala vocabulary

```
+1  '” ගොඩයගේ කුතුහලය වැඩියි.……”…””'
+1  '””'
+1  '” නෑ .. උගත්කම කියන්නෙ උපාධි –””'
+1  a 4,000-character row of running Sinhala
```

Every word of all four prices exactly. Three of them turn on `””` — U+201D twice, with no Sinhala
character between — and the second is that pair and nothing else, a **two-character message with no
Sinhala in it at all**. It is a punctuation-run question of the §7 kind and it belongs to whatever
campaign takes the quotation marks, not to this script. The fourth has no wrong word either and is
the joining residue §13.7 records for Assamese, at 1 token in 703 rather than 2 in 203.

The held-out gates, read once at the end: UDHR **484 → 486** exact on v4.7 and v5, error mass
**0.0019% → 0.0007%**. Exactly two documents move and they are the two this campaign is about —
Sinhala, the family's worst at **+33 (+0.334%) → 0**, and Central Khmer **+8 (+0.073%) → 0** — which
is the shape a real fix has on a corpus that chose nothing: it moves what it explains and nothing
else. v3 is untouched at 355/501 and 0.0228%. Rosetta 1,741/1,741, the 250-document holdout 250/250
and MultiPL-E 22/22 unmoved; no document in either family under-counts or is over 1%; the worst v4.7
document is now Shilluk at +0.10%; 219 tests pass.

## 20. Six Devanagari languages were one digit, and the localizer said so before any probe

**Measured 2026-08-11.** Six languages of the Goldfish sweep — Marathi, Newari, Maithili, Sanskrit,
Nepali and Konkani — each carried a small residue on v4.7 and a larger one on v3, and Hindi carried
almost none. Six independent languages sharing a script and each holding a tail is the shape of a
script-wide gap rather than six vocabulary tails, so the question asked first was *one cause or
six*, and the answer cost one measurement rather than six campaigns.

All seven languages now reproduce every cached row on v3 and all but two on v4.7.

### 20.1 Localize before spending, and read the shape of the answer

§18.2's method, no word cap, on v4.7: price every distinct word of every over-charging row alone.

```
            hot rows   over   words priced   wrong   explained
hin_deva          10     16            340       1          6%
mar_deva          99    160          5,089       0          0%
new_deva         104    124          3,549       2          2%
mai_deva          62     74          1,065       0          0%
san_deva          45     77          2,647       1          1%
nep_deva          50     70          2,153       1          3%
gom_deva          39     51          2,545       1          2%
```

17,388 words priced alone and seven of them wrong. That is Tamil-shaped, not Catalan-shaped — the
over-charge is at the joins, where no word miner can reach it — and, more to the point, it is
Tamil-shaped **identically in all six languages and in the Hindi control**. A single cause was the
only hypothesis that fit before a probe was bought.

### 20.2 The site, and the one cell of the grid

In-situ window deletion — delete a window from the real row and never build a new string — put
**41 of the 44 worst rows on DEVANAGARI DIGIT ZERO**. `⟨bow⟩१०⟨eow⟩` costs the oracle 2 where
`⟨bow⟩०१⟨eow⟩` costs 4: the difference is a zero closing the run.

The piece is `०⟨eow⟩`, reached by `digit_eow` (`1{} a`) — the template that bought §18's Tamil seam,
asked the same way. The grid that decides whether this is Devanagari's or a Brahmic law is ten
digits × eighteen digit scripts × both families, and it reads cost 1 in **exactly one cell**:

```
1० a  = 11 / 15  cost 1     MEMBER
1१ a  = 12 / 16  cost 2
1२ a  = 12 / 16  cost 2
1३ a  = 12 / 16  cost 2
1९ a  = 12 / 16  cost 2
```

It is Devanagari's own, and it is Devanagari's zero alone. The same instrument note as §18 applies:
the span priced is character-for-character the span the corpus writes, because a digit run never
includes the letter before it.

### 20.3 v3 carried a second shape, and it was §13.4's

v3's residue localized the other way: 220 hot rows, **100% explained inside words**, 201 of 10,166
priced words wrong — and every one of them either opens on `ि` or carries `़ि`, which is the same
site, since the nukta is a terminal separator. That is the shape §13.4 recorded for Bengali.

The piece is `⟨bow⟩ि`, **which v4.7 already shipped and v3 did not** — the mirror of §19's finding,
and the reason the two families read differently on the same rows. Fifteen word-initial Devanagari
signs asked on the `bow` template in both families: one cell at cost 1.

### 20.4 What it cost

```
              v4.7 exact          v3 exact
hin_deva      990 -> 1,000        936 -> 1,000
mar_deva      901 -> 1,000        871 -> 1,000
new_deva      896 -> 1,000        863 -> 1,000
mai_deva      938 -> 1,000        917 -> 1,000
san_deva      955 ->   998        931 -> 1,000
nep_deva      950 -> 1,000        934 -> 1,000
gom_deva      961 -> 1,000        947 -> 1,000
TOTAL       6,591 -> 6,998      6,399 -> 7,000
over          572 ->     2        826 ->     0
under           0 ->     0          0 ->     0
```

Five pieces: v4.7 takes `०⟨eow⟩ ाि ाा ―⟨eow⟩` and v3 those plus `⟨bow⟩ि`. Each was courted **alone**
at cache scale — a piece can only change a text whose *stream* holds its surface — with 0 rows
broken, 0 pushed below and 0 under-counts in either family. The control fires the right way round:
of the 1,200 v4.7 texts `०⟨eow⟩` touches, only 56 already reproduced, so the piece is explaining
something rather than decorating rows that were already right.

Across the 67 Goldfish languages on disk no language got worse in either family, and the five that
moved outside the pool all improved. Held out and read once at the end: UDHR v3 **355 → 358**, with
Bhojpuri, Hindi and Magahi going +1 → 0, and **all seven Devanagari UDHR documents now reproduce
exactly in both families**.

### 20.5 Refused

* **`――`** (two horizontal bars) reads cost 1 on its own probe in both families, but its only
  corpus evidence is five Japanese rows **plus two of the campaign's own probe strings**, and none
  at all on v3. Counting your own probes as corpus is circular, and it is not this pool's language:
  a lead, not a piece.
* **`⟨bow⟩િ`** — the Gujarati vowel sign, literally §20.3's defect one script over. It reads cost 1
  on v3's `bow` probe and v4.7 already ships it. There is no Gujarati corpus here to court it
  against, so it stays a recorded lead. It is the obvious next thing to buy.

### 20.6 Residue

Two tokens on v4.7, in two Sanskrit rows: one is PUA mojibake and one a `।““` punctuation run.
Neither is Devanagari vocabulary, and the second is the same quotation-mark question §19 left open.

## 21. The Latin/Cyrillic tail was superscript two, and only on v4.7 was it not vocabulary

**Measured 2026-08-11.** Seven Goldfish languages — Lombard, Serbian (Latin), Hill Mari, Sranan
Tongo, Romanian, Kabyle, Walloon — carried 1,307 tokens of over-charge on v4.7 and 1,785 on v3
across 7,000 rows. Lombard alone was 854 and 877, the largest single pool left in the sweep. The
brief that sent this campaign called it "ordinary missing word vocabulary, which the word miners are
built for". That was right for v3 and wrong for the v4.7 bulk, and §0's localize step is what said
so before anything was spent.

### 21.1 Localize first, and the two families disagree about what this pool IS

Every distinct word of every over-charging row, priced alone through the `raw` template — §13.2's
correction, no word cap. 6,967 distinct words on v4.7 and 13,435 on v3:

| | v4.7 over | inside words | v3 over | inside words |
|---|---:|---|---:|---|
| `lmo_latn` | 854 | **0%** | 877 | 3% |
| `srp_latn` | 101 | **0%** | 113 | 10% |
| `srn_latn` | 86 | **0%** | 89 | 3% |
| `kab_latn` | 43 | **0%** | 51 | 16% |
| `mrj_cyrl` | 104 | 6% | 113 | 13% |
| `wln_latn` | 52 | 92% | 61 | 92% |
| `ron_latn` | 67 | 100% | 481 | **100%** |

Catalan was 98% inside words and Tamil 0% (§18.2). **Lombard, Serbian, Sranan and Kabyle read 0% on
v4.7 too** — 1,084 of v4.7's 1,307 tokens sit at the joins, where no word miner reaches. v3 is the
opposite: 597 of its 1,785 are inside words, 537 of those in Romanian and Walloon alone, and the
rest is the same seam. **The same seven languages are two different campaigns in the two
families**, which is what the per-family probe rule already implies and what a shared candidate
list would have hidden.

### 21.2 The site is `²`, and the neighbouring superscripts refute the obvious generalization

Minimal failing substrings of 50 Lombard rows (trim from both ends while the row stays wrong) come
back as `'².'` and `'² '`, over and over. In situ:

```
x km² x   +1      x km²x   0      x km2 x  0      x cm³ x  0
```

`km²x` is exact and `km² x` is not, so the defect is the border and not the character: U+00B2 is
category `No`, a non-ASCII digit run, and such a run takes punctuation's border markers on both
sides (§7's 2026-08-09 correction). The stream is `⟨bow⟩km⟨eow⟩²⟨eow⟩` and we were spending `²` and
`⟨eow⟩` where the oracle spends one token.

`digit_eow` (`1{} a`) and `digit_mid` (`1{}1`) place all four spellings, in both families, with
twenty-three controls:

```
cost 1   ²⟨eow⟩   ².⟨eow⟩   ²,⟨eow⟩   ².                          v3 and v4.7 alike
cost 2-3 ²; ²: ²! ²? ²) ²] ²} ²" ²' ²% ²/ ²- ²), ²]. ²» ²”        the other borders
cost 2-3 ³. ³, ½. ½, ¹. °. °,                                     the other superscripts
cost 1   ° ⟨bow⟩° °⟨eow⟩                                          already shipped: the positive control
```

So it is **U+00B2 specifically**, not a rule about superscripts and not a rule about digit runs —
the same shape §18.5 established for the Tamil virama by sweeping twenty killers and keeping one.
`⟨bow⟩²⟨eow⟩`, `⟨bow⟩².⟨eow⟩`, `⟨bow⟩²,⟨eow⟩` and `⟨bow⟩²` all read cost 2 and are refused.

### 21.3 Three more seams, one per language, each with its own refutation

* **Kabyle** is `⟨bow⟩»,⟨eow⟩` on `digit_word` (`a », a`) — a closing guillemet and a comma,
  space-flanked, in a bibliography. `»,⟨eow⟩` was already a piece in both families; what was missing
  is the run that also owns its ⟨bow⟩, which is why the suffix piece could not reach it.
* **Hill Mari** is `―⟨eow⟩`, U+2015 HORIZONTAL BAR, its dash separator. `—` and `–` already carry
  the full bow/eow/word/mid set at cost 1 in both families; `‒` and `⸺` read 3–5. `⟨bow⟩―⟨eow⟩` and
  `⟨bow⟩―` read 2 and are refused, so it is the suffix and not the run.
* **Walloon** is `åd` on `mid` — 22 of the 22 words the localize step flagged contain it.

Romanian's are ordinary cased whole words on the `raw` template (`După`, `României`, `București`),
and Hill Mari's three are the same shape (`András`, `István`, `График`).

### 21.4 v3's other half is the word campaign the brief expected

`mine_lang.py` on the same seven languages, 8,276 independently priced words as the control set:
65 candidates passed their own probe and repaired 116 of the 154 standalone-wrong words with none
pushed below. The row court then **dropped five of them** — `⟨bow⟩oraș`, `⟨bow⟩èp`, `⟨bow⟩româ`,
`⟨bow⟩transil`, `eleb` — because once the pieces ranked above them were in, they repaired no row and
gained no token. That is the control doing the only job it has: a candidate whose probes already
reproduce explains nothing (§1's hazard 9).

The pieces are unremarkable and that is the point: Romanian `ău⟨eow⟩` `⟨bow⟩ști` `ârș` `⟨bow⟩bucure`
`⟨bow⟩orașul⟨eow⟩`, Lombard `ània⟨eow⟩` `ària⟨eow⟩` `⟨bow⟩època⟨eow⟩` — the same `-ància` shape the
2026-08-08 Catalan batch found — Kabyle `awaw` `riri` `čč`, Hill Mari `илил` `осос`.

### 21.5 What it cost, measured before and after on everything

A piece changes only a text whose STREAM holds its surface (§13.8), so the differential is that set,
tiled twice. Not one cached text in either family was broken or pushed below:

| | texts the pieces touch | exact before | exact after | over before | over after | under |
|---|---:|---:|---:|---:|---:|---:|
| v3, 70 pieces | 2,211 of 562,763 | 534 | **2,174** | 2,337 | **54** | 0 → **0** |
| v4.7, 13 pieces | 7,379 of 1,040,784 | 454 | **7,371** | 9,840 | **10** | 0 → **0** |

The pool itself, against recorded counts:

| | rows | exact | over | under |
|---|---:|---|---:|---:|
| v4.7, seven languages | 7,000 | 6,167 → **7,000** | 1,307 → **0** | 0 → 0 |
| v3, seven languages | 7,000 | 5,845 → **6,947** | 1,785 → **69** | 0 → 0 |

**v4.7 reproduces every one of the 7,000 rows**, including all 1,000 Lombard. v3's residue is 65
tokens of Romanian word vocabulary and four tokens elsewhere.

The whole-cache under scan afterwards reads **0 tokens in 0 texts** on both families, over 562,763
v3 and 1,040,784 v4.7 cached texts.

The held-out gates, read once at the end: UDHR **355 → 375** exact on v3 (mass 0.023% → 0.018%,
speakers-weighted 0.005%) and **484 → 486** on v4.7 and v5 (0.002%, speakers-weighted 0.002%);
Rosetta 1741/1741, the 250-document holdout 250/250 and MultiPL-E 22/22 unmoved; no document in
either family under-counts and none is over 1%; 222 tests pass. UDHR chose none of this — it is the
consequence §0 says a real fix shows up as.

### 21.6 An instrument note: a trial model is not a copy with one more piece in it

`TokenizerModel` derives a reverse trie, the cost-1 whole-character set and the byte floor from the
vocabulary once, at construction. After #15 a rig helper that cloned the model and edited `.vocab`
changed nothing the tiler reads, so **every candidate silently measured as explaining nothing** —
the failure mode looks exactly like an honest refusal and reports clean. The tell was a candidate
whose own probe reads cost 1 repairing zero rows it demonstrably fixes by hand. Anything that builds
a model with extra pieces has to rebuild the derived structures, and a trial model that cannot
change a row it should is worth one assertion before a campaign trusts it.

## 22. CJK, Greek and the Arabic-script tail: eleven languages, three sites and one recorded lead

**Measured 2026-08-11.** Eleven Goldfish languages carried 215 tokens of over-charge on v4.7 —
Kanuri 58, Chinese 39, Japanese 36, South Azerbaijani 19, Min Nan 15, Ancient Greek 13, Modern
Greek 9, Sindhi 9, Korean 8, Sorani 5, Uyghur 4. **All eleven now reproduce every cached row in
both families**, and the whole sweep moves 348,368 → 348,593 exact, 844 → 521 tokens of
over-charge, 226 → 259 languages clean.

Nineteen pieces on v4.7 and thirteen on v3. None of them is a word.

### 22.1 The instruments the brief warned about, and what each one actually said

The pool was chosen because the usual vocabulary does not apply to it: Han, Hangul and astral
characters take no border markers (§17), so there is no word-and-seam campaign to run in Chinese,
Japanese or Korean at all. What is left is the punctuation and the numerals *around* the ideographs,
and that is where every one of the CJK tokens turned out to be.

**The ヲ hazard (§1) reverses in this pool and does not bite.** In Japanese the anchor is the
language's own script, so "measuring a cluster against a base its script never writes" is not the
objection; the objection would be that ヲ *merges* with a kana candidate. Not one candidate here is
kana. The Arabic and Greek candidates were asked on the ヲ grid and independently in their own
script — `x َحل x` `x َيا x` against `x حل x` `x يا x`, and 21 real Greek `ββ` rows — and the two
frames agree on every one. Where a frame did lie it lied for a different reason, and §22.4 records
it.

**Localize first (§20) says: not here.** In Han and in unspaced text "word" is barely a notion —
`classify` puts every ideograph in the isolated HARD class, so the word localizer returns *nothing*
for a pure Chinese row and cannot speak. In-situ window deletion (§18.3, never building a new
string) is the instrument that can, and on the pool's 157 over-charging rows it returned a single
character, or a span ending exactly at one, in all but a dozen.

### 22.2 Three sites, and each one's refutation grid

**A word that opens on a baseless Arabic FATHA.** Kanuri, Sindhi and South Azerbaijani are one
cause: 23 of Kanuri's 45 bad rows localize onto a lone `َ`, and nine more onto the space in front of
one. §16 already fixed the *spelling* — a baseless mark and the letter after it are one word — so
this is the vocabulary the fused spelling then needs: `⟨bow⟩َ`. All 24 Arabic combining marks asked
on `bow` (`.{}ヲ.`) in both families:

```
cost 1   َ  U+064E                                    MEMBER, both families
cost 2   ً ُ ِ ّ ْ                                      the other five harakat
cost 3   ٌ ٍ ٓ ٔ ٕ ٰ ٖ ٗ ٘ ٙ ٚ ٛ ٜ ٝ ٞ ٟ                  everything else in the block
```

One cell of twenty-four, in both families, and the own-script grid agrees exactly: `x َحل x` and
`x َيا x` read one over while the eight rival marks read zero on the same two hosts. Kanuri's
residue after it was a *doubled* fatha (`إِلـََيْكَ`, `مَالاََئِكَ`), which is `ََ` on §6's `mark_mid`
frame — cost 1 in both families, and 186 cached rows repaired with none broken.

**A CJK punctuation PAIR, not a doubled punctuation rule.** Chinese localizes onto `）` in 30 of
its 36 bad rows, always as `），` closing a parenthetical before a fullwidth comma. Asked with its
neighbours on `digit_mid` (`1{}1`), both families:

```
cost 1   ），  ））  ““  ””  ――  ××  ››            and ― alone, already shipped: the positive control
cost 2   （（  ，，  、、  ､､  ）、  ）。  ）］  ），。  ），、  ），）
cost 4   ‹‹  ｡｡
```

`（（` and `，，` are the same shape as `））` and `，` and read 2, so it is these seven pairs and not a
rule about repeated ideographic punctuation. `‹‹` reading 4 against `››` reading 1 is the sharpest
of them.

**U+2460 and U+2461 want an ⟨eow⟩; U+2463 wants a character.** `_is_no_run`'s docstring has
recorded since 2026-08-09 that four *other numbers* dissent from the border-marker sweep — U+00B2,
U+2460, U+2461, U+2463 — and filed them as "a missing piece rather than a missing marker", open. §21
bought U+00B2. This pool is where the other three fire, in Chinese, Japanese, Korean and Min Nan:

```
x ① x  +1   x① x  +1   x ①x   0   x  ①  x   0     ①⟨eow⟩ is the missing token
x ④ x  +2   x④ x  +2   x ④x  +2   x  ④  x  +2     ④ is missing as a CHARACTER
x ③ x   0   x ½ x   0   x ⑩ x   0   文 ① 文  +1     the controls, and one own-script row
```

and the probes place all three exactly:

```
cost 1   ①⟨eow⟩  ②⟨eow⟩          on digit_eow          cost 1   ④           on char
cost 2   ③⟨eow⟩  ④⟨eow⟩  ⟨bow⟩①  ⟨bow⟩②  ⟨bow⟩③  ⟨bow⟩④
cost 3   ⑤ ⑥ ⑦ ⑧ ⑨ ⑩ ⑪ ⑬ ⒈ ⑴ ㈠      cost 4   ⑤⟨eow⟩  ⟨bow⟩⑤
```

Twelve neighbouring enclosed numerals refuse, so it is those two codepoints and that codepoint,
exactly as `_is_no_run` said. **v3 already shipped `④` and v4.7 did not** — the §19/§20.3 mirror
again, and the reason the two families read differently on the same Korean rows.

### 22.3 The five smaller ones

* **Greek is one digraph, `ββ`** — and it is *both* Greek languages. Σάββατο, σάββασιν, κρεββάτι,
  Ῥαββί, Βαραββᾶν: 8 of Ancient Greek's 11 rows and 7 of Modern Greek's 9 localize onto the second
  `β`. On `mid`, `ββ` reads 1 in both families where `σσ λλ μμ ρρ κκ γγ` read 2 and `ππ ττ νν` read
  1 and were already shipped (the positive control). The five widenings `ββα άββ ββά αββ ββι` all
  read 2, so the digraph is the span and not a syllable around it.
* **Min Nan is `⟨bow⟩－`**, a fullwidth hyphen opening a year range (`1961 nî －1971 nî`), on
  `digit_bow` — 11 of its 14 rows.
* **Japanese wants `､`, `［` and `］`** as characters — halfwidth ideographic comma and fullwidth
  brackets, all three cost 1 on `char` and all three already in v3 — while `｡ ｢ ｣` on the same
  frame read 2 and are refused. Three of its rows were §20.5's `――` lead, which this pool is the
  language of: 37 cached rows, 36 repaired.
* **Korean's last row is `⟨bow⟩□`** on `digit_bow`, against `□⟨eow⟩` and `⟨bow⟩□⟨eow⟩` at 2.
* **Sorani is one Kurdish word**, `ململانێ` "conflict": `ململ` on `mid` at cost 1, where `⟨bow⟩مل`,
  `⟨bow⟩ململ`, `لململ` and `ملم` all read 2. `مل` was already a piece, which is why the localizer
  pointed at the second `م` rather than the first.

### 22.4 Refused, and one frame that lied

* **`““` and `””` are v4.7 pieces and NOT v3 pieces, and their v3 probes say otherwise.** `1““1`
  reads cost 1 on v3 — because v3 folds curly quotes to ASCII before anything else, so the probe
  measures `""`, which has been a piece all along. The tell was the corpus: over the entire v3
  cache the candidate touched **zero** rows, since no v3 stream can contain the surface. A template
  that normalizes its own argument away is §6's third lesson in a new costume — the wrong frames
  fail silently and return numbers.
* **`⟨bow⟩－⟨eow⟩`** passes its own `digit_word` probe at cost 1 in both families and is refused:
  once `⟨bow⟩－` is in, it repairs 0 corpus rows and gains 0 tokens, and the only row it ever fixed
  was the probe string this campaign itself bought. §1's hazard 9, caught by the control.
* **`⑤ ⑥ ⑦ ⑧ ⑨ ⑩ ⑪ ⑬ ⒈ ⑴ ㈠`, `｡ ｢ ｣`, the 23 non-fatha Arabic marks, `‹‹ （（ ，， 、、 ､､ ）、 ）。
  ）］ ），。 ），、 ），）`, `σσ λλ μμ ρρ κκ γγ`, `ββα άββ ββά αββ ββι`, `⟨bow⟩مل ⟨bow⟩ململ لململ ملم`,
  `□⟨eow⟩ ⟨bow⟩□⟨eow⟩`, `③⟨eow⟩ ④⟨eow⟩ ⑤⟨eow⟩ ⟨bow⟩① ⟨bow⟩② ⟨bow⟩③ ⟨bow⟩④ ⟨bow⟩⑤`** — 60
  candidates, every one refused by its own probe.
* **Three languages were not vocabulary and are reported as such.** South Azerbaijani's worst row
  (+13 of its 19 tokens) is PDF-extraction mojibake — literal `u202b`/`u202c` text, harakat scattered
  off their letters; it repairs because the fatha piece happens to cover the debris, not because
  anyone modelled it. Nine Chinese rows carry runs of U+0005–U+0008 and U+0016 control characters
  from the same kind of scrape. Ancient Greek is a critical-apparatus edition whose editorial
  brackets `⸂⸃⸋⸌⸉⸊⸆` are byte-floored and *already priced correctly* — they are the most conspicuous
  thing in every failing row and none of the failures is theirs.

### 22.5 What it cost, over every text that could move

A piece changes only a text whose normalized stream holds its surface, so the exact reading is the
differential one:

| | cached texts | touched | exact | over | under | broke | worse |
|---|---:|---:|---:|---:|---:|---:|---:|
| v4.7 | 1,046,725 | 4,394 | 3,241 → **4,393** | 1,415 → **1** | 0 → **0** | **0** | **0** |
| v3 | 684,009 | 1,771 | 1,535 → **1,760** | 311 → **12** | 0 → **0** | **0** | **0** |

Per language on the fixed 349,000-row sweep, v4.7, over-charge before → after:

```
knc_arab 58 → 0    zho_hans 39 → 0    jpn_jpan 36 → 0    aze_arab 19 → 0
nan_latn 15 → 0    grc_grek 13 → 0    ell_grek  9 → 0    snd_arab  9 → 0
kor_hang  8 → 0    ckb_arab  5 → 0    uig_arab  4 → 0
```

215 of the 323 tokens the sweep lost are the pool's and 108 are elsewhere, because these pieces are
not this pool's property: Tatar went 37 → 2 on `××`, Estonian 13 → 0, Hebrew 7 → 0, Georgian 5 → 0
and Sinhala 4 → 0, mostly on `››` and `““`, and Danish, Neapolitan, Finnish and Avar each lost a
token or three. **Not one language of the 350 got worse**, and the whole-cache under scan afterwards
reads **0 tokens in 0 texts** on both families, over 695,812 v3 and 1,046,725 v4.7 cached texts.

The held-out gates, read once at the end: UDHR **378/501 on v3** (mass 0.018%, speakers-weighted
0.005%) and **488/501 on v4.7 and v5** (0.001%), both unmoved; Rosetta 1741/1741, the 250-document
holdout 250/250 and MultiPL-E 22/22 unmoved; witness coverage 100% in both files; 222 tests pass.
UDHR carries Chinese, Japanese, Greek and Arabic documents and every one of them was already exact,
so this campaign is invisible there — which is the honest outcome when a pool's defects live in
scraped web punctuation and OCR'd harakat rather than in the language.

### 22.6 Residue

None in this pool: all eleven languages reproduce every cached row on v4.7. The v3 reading rests on
the 1,390 sweep rows this campaign bought counts for — v3's Goldfish coverage is otherwise too thin
in these scripts to score — and every candidate was judged on real corpus rows in *both* families
rather than on its own probe strings, which is what §20.5 asked for and what caught the two quote
pieces.

The one Arabic-script language of the sweep still over-charging is South Azerbaijani's OTHER config,
`azb_arab`, at two tokens in one row — `اینگیلیسجه: János Bolyai no یانو (اینگیلیسجه: Patrick
Modianod ۰`, a scrape that has run two truncated parentheticals together across three scripts. It
localizes onto `: ` and it is §13.7's mixed-script span, which the templates refuse on purpose. Not
vocabulary, and not worth a piece.

## 23. The European tail was three seams and a proper-noun list, and one row of `×`

**Measured 2026-08-11.** Ten large, well-resourced Goldfish languages — Bulgarian, Hungarian, Tatar,
Danish, Swedish, Neapolitan, Polish, Ukrainian, Catalan, Estonian — carried **331** tokens of
over-charge on v4.7 and **805** on v3 over 10,000 rows. That is eight hundredths of a token per row
on v4.7's worst of them, and the brief that sent this campaign said outright that vocabulary this
well-resourced is the most likely to be already complete, so "this residue is not vocabulary" was a
live answer rather than a failure. It was the right answer for three of the ten and the wrong one
for seven, and §0's localize step separated them before anything was spent.

All ten now reproduce every row on v3, and nine of ten on v4.7.

### 23.1 Localize first, and the split is 7–3

Every distinct word of every over-charging row, priced alone through the `raw` template, no word cap
(§13.2 / §18.2). 5,897 distinct words on v4.7 and 12,119 on v3:

| | v4.7 over | hot rows | inside words | v3 over | inside words |
|---|---:|---:|---|---:|---|
| `bul_cyrl` | 86 | 53 | **100%** | 91 | 100% |
| `hun_latn` | 64 | 25 | **100%** | 58 | 100% |
| `tat_cyrl` | 37 | **3** | **0%** | 45 | 22% |
| `dan_latn` | 27 | 26 | 96% | 44 | 100% |
| `swe_latn` | 26 | 22 | **100%** | 38 | 100% |
| `nap_latn` | 23 | 23 | **0%** | 26 | 15% |
| `pol_latn` | 18 | 18 | **100%** | 7 | 100% |
| `ukr_cyrl` | 17 | 16 | **100%** | 20 | 95% |
| `cat_latn` | 20 | 9 | **100%** | 475 | 100% |
| `ekk_latn` | 13 | 13 | **0%** | 1 | 100% |

Seven are Catalan-shaped and a word miner is the instrument; **Tatar, Neapolitan and Estonian read
0%** and no word miner can reach them. Unlike §21, the two families agree about which is which — the
disagreement here is about SIZE, and it runs the other way for Catalan (20 on v4.7, 475 on v3) and
for Polish (18 on v4.7, 7 on v3).

### 23.2 Read the failing rows before mining, because three languages are one row or one glyph

The 0% languages resolve by looking at the rows, and each is a single site:

* **Tatar's 37 tokens live in THREE rows, and 35 of them in one.** That row is a Tatar nightclub
  flyer whose section dividers are `××××××××××××××` — five runs of fourteen U+00D7, which we spend
  fourteen tokens on and the oracle spends seven. `××` on `digit_mid` reads cost 1 in both families
  and `×××` and `××××` read 2, so it is the PAIR and not a rule about runs — the same shape §20.2's
  Devanagari zero and §18.5's Tamil virama have. `×` alone was already a piece.
* **Neapolitan's 23 tokens are 23 rows of a birth-and-death list**, each ending `(† 1721)`.
  `⟨bow⟩(†⟨eow⟩` on `digit_word` reads cost 1 in both families; `(†` alone reads 2. `†⟨eow⟩` was
  already a piece in both, so what was missing is the bordered run that also owns its ⟨bow⟩ —
  exactly §21.3's Kabyle `⟨bow⟩»,⟨eow⟩`.
* **Estonian's 13 tokens are 13 rows of a Gospel translation** that closes a quotation inside a
  quotation, `…suust.““`. `““` reads cost 1 on v4.7.

### 23.3 The quote pair is v4.7's alone, and the family difference is not vocabulary

`““` also reads cost 1 on v3 — and it is not a v3 piece, because **v3 folds quotes and v4.7 does
not**. On v3 the probe `1““1` streams to `1""1`, so it measures `""`, which v3 already ships;
`witness.verify`'s placement check says so in as many words ("the encoder no longer writes this
piece into that probe") and is what refused it. Every quote-pair reading on v3 is that same
artefact. This is §19's non-transitivity with a mechanism attached: the cross-family probe agreed
and the cross-family piece still did not exist.

On v4.7, where the probe means what it says, the grid discriminates sharply:

```
cost 1   ““   ””   ««                    MEMBERS
cost 2   “”   ”“   ”””   ’’   »»         the mixed and the tripled
cost 4   ‘‘
```

`””` was found by re-reading the residue after the first batch: two rows, one Danish (`Du skriver:
””`) and one Neapolitan, in two unrelated languages. Across the whole v4.7 cache it touches 36 texts
and makes all 36 exact. **`««` is refused** — cost 1 on its own probe, no corpus evidence anywhere in
this pool, and §20.5's rule is that a piece with no corpus behind it is a recorded lead, not a piece.

### 23.4 The seven word languages are proper nouns and one suffix each

Nothing exotic, which is the point. v4.7 took 15 word pieces for 15,000 rows of the seven:
`⟨shift⟩⟨bow⟩софия⟨eow⟩` `⟨shift⟩⟨bow⟩през⟨eow⟩` (Bulgarian — `София` alone is 54 of Bulgarian's
86), `⟨shift⟩⟨bow⟩józsef⟨eow⟩` `⟨shift⟩⟨bow⟩jános⟨eow⟩` `⟨shift⟩⟨bow⟩györgy⟨eow⟩`
`⟨shift⟩⟨bow⟩lászló⟨eow⟩` (Hungarian given names, the whole of its residue), `⟨bow⟩kø` (Danish —
*køn*, *køre*, *køkken*, *Køge*, one prefix for eleven words), `ården⟨eow⟩` `⟨bow⟩käll` (Swedish),
`⟨bow⟩król` `⟨bow⟩język⟨eow⟩` (Polish), `ває⟨eow⟩` `⟨bow⟩події⟨eow⟩` (Ukrainian),
`⟨shift⟩⟨bow⟩valència⟨eow⟩` (Catalan — 20 of 20). v3 took 87 of the same shape, 60 of them Catalan.

**An instrument correction the campaign needed.** `mine_stream.probe_of` refuses CASED candidates on
purpose, because the `cased_*` templates ask a different question (`MController` prices `M` as a
word-interior prefix). But the plain `.X.` grid handles a cased key perfectly well —
`witness.surface` re-applies the capital and `witness.position` reads the boundary markers past the
case marker — and that is how §21.3's `⟨shift⟩⟨bow⟩bucureşti⟨eow⟩` already ships. Without that the
miner stalled with seven wrong words and no candidate it could ask about; with it, `.György.` on the
`word` template settles them. `verify` still has to agree the encoder writes the piece into the
probe, so the placement question is answered rather than assumed.

### 23.5 The court, and what it dropped

Every candidate was scored **alone** first — a piece changes only a text whose stream holds its
surface (§13.8), and the stream does not depend on the vocabulary, so each candidate's rows are
known before any of them is accepted. Then all together, then leave-one-out: a piece whose removal
does not move the pool repairs no row the others do not already repair, which is §21.4's test.

```
                  v4.7                          v3
candidates        18                            91
refused           0 (none pushed a row below)   0
dropped as idle   0                             2   ⟨bow⟩імпер, ⟨bow⟩valència⟨eow⟩
kept              18 (+ ”” after)               89
pool 10,000 rows  9,785 -> 9,998 exact          9,449 -> 9,987 exact
                    331 ->     2 over             805 ->     7 over
under                 0 ->     0                    0 ->     0
```

`⟨bow⟩valència⟨eow⟩` is instructive: it is a real token by its own probe, and every Catalan row that
holds it holds the capitalized form, which the cased piece already covers. It gains nothing and it
is dropped.

### 23.6 What it cost, measured on everything cached

The differential is the texts whose stream holds a piece's surface, tiled twice — one model with the
pieces and one without, both with their derived structures rebuilt (§21.6):

| | texts touched | exact before | exact after | over before | over after | pushed below |
|---|---:|---:|---:|---:|---:|---:|
| v4.7, 18 pieces | 782 of 1,046,224 | 263 | **780** | 680 | **2** | 0 |
| v4.7, `””` | 36 of 1,046,725 | 8 | **36** | 31 | **0** | 0 |
| v3, 89 pieces | 4,362 of 705,121 | 2,520 | **4,337** | 2,467 | **46** | 0 |

Not one cached text in either family was broken or made worse. The whole-cache under scan afterwards
reads **0 tokens in 0 texts** on both families, over 1,046,725 v4.7 and 724,427 v3 cached texts.

The Goldfish sweep, all 349,000 rows on disk, scored against the cache:

```
v4.7   348,368 -> 348,660 exact     over 844 -> 409     under 0     262 of 350 languages perfect
```

**No language in the sweep got worse and 51 improved** — 41 of them outside this pool, because the
seams are not this pool's property: Norwegian took `⟨bow⟩kø`, Hebrew and Georgian took the quote
pairs, and Silesian, Avar, Mari, Bosnian (Cyrillic) and Sinhala each lost a token or more to pieces
they never nominated. v3's sweep reading is not comparable yet — the background buyer has bought 54%
of the corpus for that family — but on the 188,542 rows it can score, all ten pool languages read
exactly as the table above.

Held out and read once at the end: UDHR v3 **378 → 393** exact (error mass 0.018% → 0.015%,
speakers-weighted 0.005%), v4.7 and v5 **488 → 490** (0.001% → 0.000%). Rosetta 1,741/1,741, the
250-document holdout 250/250, MultiPL-E 22/22, witness coverage 100% in both files, 222 tests pass.
No UDHR document under-counts and none is over 1%. UDHR chose none of this.

### 23.7 Refused, and the residue

* **`:)` `;)` `⟨bow⟩;)` `:):)` `;);)` `):)` `);)` `:):):)`** — Tatar's other two rows are emoticon
  runs, `китте:):):)тавышымны` and `бар ;););)`, and **every span of them refuses its own probe** in
  both families. `1:):):)1` prices at exactly what we already charge, so the missing token is at the
  seam between the run and the words around it, not in the run. Two tokens in two rows, and not
  vocabulary. `:(` reads cost 1 on v3 and has no corpus behind it here: a lead.
* **`««`** — cost 1 on v4.7, no corpus evidence. A lead (§20.5's `⟨bow⟩િ` again).
* **`×××` `××××` `“”` `”“` `”””` `‘‘` `’’` `»»`** — refused by their own probes, and they are what
  makes `××`, `““`, `””` claims about specific pairs rather than about runs of symbols.
* v3's residue is **7 tokens**: six in five Catalan rows around `esdeveniments`, and one Ukrainian
  row. Catalan's control set was capped at 4,000 of its 5,729 hot words, so those are ordinary word
  vocabulary the miner did not get to rather than anything structural.

## 24. Tibetan is one two-mark cluster on v3, and the probe that would land it is unbought

**Measured 2026-08-11, entirely against measurements already on disk** — the session that ran this
had no API access, so nothing below cost a probe and nothing below could buy one. It names v3's
largest remaining defect precisely, and stops where the evidence stops.

On the 35,774-line Goldfish sample (190 languages, every line counted in both families):

```
v3     35,540 exact   over 310   under 1     bod_Tibt 679/794 exact, over 180   dzo_Tibt 413/420, over 8
v4.7   35,749 exact   over  26   under 0     bod_Tibt 794/794             dzo_Tibt 420/420
```

**Tibetan is 58% of everything v3 gets wrong here and v4.7 gets it right**, through identical code.
§18.1's query — is the cross-family difference real vocabulary, or an artefact of one family's set
being a subset of the other's? — comes out the other way from Tamil:

```
Tibetan-bearing pieces   v3 36   v4.7 35   shared 34
v4.7-only   ློ     U+0FB3 TIBETAN SUBJOINED LETTER LA + U+0F7C TIBETAN VOWEL SIGN O
v3-only     གག  པ
```

One piece, and it is the whole residue. `ློ` is a two-mark cluster in the middle of ordinary
words — `སློབ` *slob*, "study", and its compounds — where v3 spends a token on each mark and the
oracle spends one on the pair.

### 24.1 The corpus says so before any candidate is proposed

All 115 over-charging Tibetan rows contain `ློ`; **not one of the 679 exact rows does**. Dzongkha
repeats it independently: 7 of 7 over-charging rows hold it, 0 of 413 exact rows do. Every one of
the 60 mispriced Tibetan words priced alone from the cache holds it too.

Added to v3 and courted alone, at cache scale — a piece can only change a text whose *stream* holds
its surface (§13.8):

```
220 cached texts hold it     before  exact   0   over 457   under 0     <- not one already reproduced
                             after   exact 220   over   0   under 0
                             repaired 220   broken 0   pushed below 0

Goldfish rows, v3           bod_Tibt 679 -> 794 exact, 180 -> 0 over
                            dzo_Tibt 413 -> 420 exact,   8 -> 0 over
                            corpus total 35,540 -> 35,662 exact, over 310 -> 122, under 1 -> 1
```

No other language of the 190 moves by a token. Held out and read once at the end, as a consequence
and never a reason: UDHR v3 would go **393 -> 395** exact, with the Tibetan document +15 -> 0 and
the Dzongkha document +6 -> 0.

The control runs in the other family as well, and that is the cleanest form of it: **739 cached
v4.7 texts hold the same surface and every one of them already reproduces**, because v4.7 ships the
piece. One surface, one encoder — 220 of 220 wrong in the family that lacks it, 739 of 739 right in
the family that has it.

### 24.2 Why the piece is not in this file

Because a corpus delta has never been allowed to admit a piece here, and `ློ` has no v3 probe:

```
v3    mark_mid  '.ᛒློᛒ.'   accepts at raw 18      never bought
      char      'aློa'     accepts at raw 10      never bought
      mid       '.ヲློヲ.'   accepts at raw 16      never bought
v4.7  mid       '.ヲློヲ.'   = 20 -> cost 1         bought, and it is why v4.7 is exact here
```

All three templates place the piece bare in a word interior, and the span each prices is
character-for-character the span the corpus writes — the check §18.4 uses against §1's hazard,
which matters because Tibetan is squarely in the script family where unconstrained fragment mining
manufactures pieces. v3's Tibetan grid was bought one mark at a time — `.ヲླヲ.` = 16 is how `ླ`
itself became a piece — and the pair was never asked about.

Two shortcuts were available and both are wrong:

* **v4.7's witness does not transfer.** Its raw 20 read through v3's BASE is cost 5, which records
  the piece as refuted, not accepted. A spelling and a reading are per-family (meta-rule 1).
* **The bare message is not a template for this piece.** `'ློ'` alone is cached at 10, which is
  consistent with the cluster costing one token inside its two border markers — but a piece that
  OPENS ON A MARK is exactly the case where the frame edge is charged (§17.1), and the routing
  refuses the `raw` template for it. Corroboration, recorded as corroboration.

**One probe in one family closes this**, and until it is bought v3 over-charges Tibetan and
Dzongkha text by roughly one token per `ློ`.
