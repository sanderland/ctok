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
`is_killer(U+200B)` is False — and it reaches `classify` with no branch of its own, so
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

The five word-context mark pieces (U+0302 0303 0304 0327 0331) are tile-contextual
(`engine._mark_host_tile`): the piece prices 1 after a single-letter tile of at most two UTF-8
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

The dotted capital İ is the same shape (`engine._dotted_host_blocked`): its unit piece pays its
two bytes where İ is word-final or followed by an ASCII lowercase letter AND the tile before it
carries a marker and ends in an uppercase ASCII letter (`Bİ Dİ Kİ Lİ Rİ Sİ Tİ` = 15, `Dİs` = 15,
`x Dİl x` = 17; controls `AİD` `BİR` `RPİ` `aİ` `x İİ x` `x DİREKTOR x` `xalqlarınİ` exact).
One row stays UNEXPLAINED:

```
x novunİ x       17   İ prices 1 after the tile (un)
x Hüseynovunİ x  22   İ pays bytes after the same tile (un) — one under for us
```

The two words share their entire tail; only `⟨bow⟩H` + `ü` differ, five tiles before the İ. No
rule over the preceding tile can separate them; a piece we lack (`⟨bow⟩Hüseynovun`-shaped, which
would put a marker-carrying multi-letter tile before the İ) would, and is not attributed without a
probe that could refute it.

## 12. The last eight under-counts, 2026-08-09

**SUPERSEDED 2026-08-10 — §14.** All four populations below reproduce now, and none of them was
about what its heading says: 12.1–12.4 are one rule about unattached mark runs (§14.4), and the
`_charging_border` half of the two rules that opened this section was the U+0300 block's word
boundary read one character late (§14.1). The self-consistency check in the last paragraph — our
digit frame agreeing with our letter frame in 30 rows — is why it went in wrong; both frames were
ours.

Two rules landed this day and took the under-count over Goldfish, Glot500 and the FineWeb/Stack
slices from 18 to 8. Both were the same shape — **a border marker that is invisible wherever a
⟨bow⟩ follows the space**, because the seam then deletes the marker along with the space, so only a
right neighbour that writes no ⟨bow⟩ of its own can see it:

* a non-ASCII digit run takes ⟨eow⟩ as well as ⟨bow⟩, per border CHARACTER, and a HARD run splits
  at the number boundary (`normalize._digit_eow`, `_hard_kind`) — Japanese 4 → 0;
* a word ending in a charging mark takes the same right-hand ⟨eow⟩, which is what the seam block
  in `_seam_sub` was standing in for (`normalize._charging_border`) — Yoruba 5 → 0, and the last
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
it for particular pairs, exactly as `±`/`©`/`®` swallow the symbol ⟨eow⟩ in `_is_symbol_text`.
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
away from the İ, which `engine._dotted_host_blocked` cannot express and which nothing else in the
model needs, so it is not written on this evidence.

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
than 79%. The Latin-glued words are a mixed-script, case-carrying span, which `mine_stream.probe_of`
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
mark. Grid B of the reconnaissance that opened this campaign — the mark's increment over the bare
host word, `x H M z x` minus `x H z x` — has the same defect for the same reason, and it is what
made the split look host-dependent: `q` and `б` read +2 where `ก` and `ب` read +3 because
`x q x` = 10 and `x ก x` = 11, not because the mark behaves differently.

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

That is exactly the range the retired `_charging_border` enumerated. Its population was right and
its reading was one step late: the extra ⟨eow⟩ it wrote at a word-final space border is the ⟨eow⟩
the word already had, one character earlier.

Asked of the other 418 combining marks of the BMP, on in-script one-token hosts as well as `q`, the
answer is orthographic and not numeric — the same distinction `is_killer` already draws for Thai:
accents, tone marks, cantillation and annotation stand outside the word; vowel points and combining
LETTERS stay inside it. `гдⷭ҇и` carries both in one word: U+0487 pokrytie separates, and the
combining Cyrillic letter U+2DED beside it does not.

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
* **§12.1–12.4 are gone.** 52 of their 53 rows are exact on v3 and 53 of 53 on v4.7, controls
  included, and the closing rule was not about marks at all (14.4).

### 14.4 An unattached mark run is a word

A stray-mark pretoken already owned a ⟨bow⟩. It owns an ⟨eow⟩ too, against everything except a
letter — which it fuses with, so the word after it is written bare and the mark run's ⟨bow⟩ is that
word's. That single rule closes §12.1's junction population, §12.2's dotted İ, §12.3's message-end
run and §12.4's Igbo word, which is the argument that it is a law and not a patch: none of the four
was about the thing its section named it after.

### 14.5 What it cost, measured before and after on everything

| | v3 exact | over | under | | v4.7 exact | over | under |
|---|---:|---:|---:|---|---:|---:|---:|
| Goldfish + Glot500 + FineWeb/Stack/github-code, before | 280,262 | 49,283 | 6 | | 288,392 | 40,598 | 8 |
| after | 280,271 | 49,262 | **5** | | 289,105 | 38,399 | **1** |

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

### 14.6 What is still open

* **Three marks are over-priced at a stray run head, by a constant.** U+05B0 and the Lao U+0EB9 by
  one, U+064B by two, in all five frames `x M x` / `x M5 x` / `M` / `x M` / `x Mx x`. A constant
  across frames is a head PRICE, not a marker — our raw byte floor charges two bytes where the
  oracle reaches them in fewer tokens. Twelve other marks in the same grid are exact in all five.
  §12.3 predicted this: "a marker rule cannot split two stray marks that way; a piece can."
* **A Syriac dot with a rider is one under.** `x ݀ͅ x` = 16 / 20. U+0740–U+074A start an unmarked
  run that a following non-vowel mark joins (§0), and that joined run writes no boundary where a
  stray run now would. One row, one shape, not attributed.
* **`x िी x` = 11 on v3 and 15 on v4.7.** §12.1 listed it as an exact control; it is exact on v4.7
  and one OVER on v3, and always was. Two adjacent Devanagari vowel signs with no consonant, which
  is not a shape the corpora contain.
