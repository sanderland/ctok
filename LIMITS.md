# What this reconstruction does not do

README.md says how accurate the model is. This says where to distrust it: what is out of scope by
construction, which inputs could still be counted wrong, and what the accuracy numbers do and do not
prove.

Everything here is current state. Nothing here is a guess about what the tokenizer "probably" does —
where a limit is a measured fact, the measurement is given; where it is an open question, it says so.

## Out of scope by construction

* **Counts, not boundaries.** The model reproduces what `count_tokens` returns. `tokenize()` returns
  a list whose *length* is that number, but the individual tokens are one min-cost tiling among
  possibly several, and the real tokenizer's segmentation is not observable through a count. Treat
  the boundaries as illustrative and the length as the prediction.

* **One user message.** The frame modelled is a single user turn: `⟨pad⟩` stands for the whole
  request prefix, the role marker and the assistant prompt that follows. System prompts, tool
  definitions, multi-turn requests, images and documents are not modelled, and a request containing
  any of them will not add up from these counts.

* **Three families, and v5 borrows.** `3.0`–`4.6` reconstruct one generation, `4.7`–`4.9` another,
  `5.0`+ a third. v5 has its own measured message frame but reads **v4.7's vocabulary**: no piece has
  been mined against opus-5, and nothing measured says one differs. If v5's vocabulary did change in
  a way these corpora do not exercise, this model would not know.

* **Unofficial.** Everything here was derived by probing `count_tokens`. There is no reference
  implementation to check against, so "correct" here means "reproduces every recorded count we have".

## Where the remaining error is

The residual is **over-count**: places where the vocabulary is missing a piece and the model spends
two tokens where the tokenizer spends one. That direction is the benign one — it is bounded, it is
findable, and it is what README.md's accuracy tables measure.

**Nothing under-counts.** Across every text ever measured against either family — the corpora,
the held-out gates, and the synthetic probe grids, a few million texts — no text is priced below its
recorded count in either family. This matters more than the exact rate: an under-count means the
model believes some span is cheaper than it is, which is the failure that cannot be bounded by
"missing vocabulary somewhere".

By family: **v4.7 is the stronger reconstruction** (498 of 501 UDHR documents exact, error mass
0.000%). v3's vocabulary is three times the size and correspondingly harder to complete, so v3
carries more ordinary word-vocabulary residue — 437 of 501, and its worst documents sit under +0.5%.
No document in either family is more than 1% off.

## Inputs that could still be counted wrong

* **Mixed-script spans.** A word with Latin glued directly to another script — `volleyயும்`,
  `DMামেক`, `IRGCৰ` — is the one shape the probe templates refuse on purpose: the case-carrying
  scaffolds ask a different question, and no shipped template owns a span that crosses a script
  boundary mid-word. Every *component* of such spans prices exactly; the whole can be a token off.
  This is a known gap with no instrument, not an unmined pool. The same shape covers Latin or
  Myanmar digits glued into Thai and Burmese running text.

* **Characters newer than Unicode 14.0.** Classification is derived from Python's `unicodedata`
  tables. A codepoint assigned after 14.0 reads as unassigned and falls through to the class that
  takes no word model at all, which was wrong for the Kannada sign U+0CF3 (now special-cased) and may
  be wrong for other recent assignments. Text in very recently encoded scripts is the risk case.

* **The supplementary private-use planes.** The BMP private-use area is measured to be *stripped* —
  the character costs nothing and its neighbours join into one word. Planes 15 and 16 were never
  probed and are deliberately left out of that class, so they price as ordinary astral characters.

* **Two adjacent Devanagari vowel signs with no consonant.** `x िी x` reads one token over on v3 and
  exactly on v4.7. It is not a shape natural text contains, and it has never been attributed.

* **Emoticon runs at a word seam.** `китте:):):)тавышымны`, `бар ;););)` — every span of the run
  prices exactly on its own probe, so the missing token is at the join between the run and the words
  around it rather than in the run. Two tokens in two known rows, and not vocabulary.

* **Scraped and mis-decoded text.** Mojibake (CP1251 read as Latin-1, PDF extraction debris,
  bidi-control literals), runs of C0 control characters and OCR'd Arabic diacritics all occur in the
  corpora and are counted like any other text — sometimes exactly, by accident of what the vocabulary
  happens to cover. Accuracy on such input is not something these corpora measure.

* **Scripts with no reachable corpus.** Several candidate pieces are recorded as *leads*: their own
  probe prices them at one token, but there is no corpus here to court them against, so they were not
  taken. The Gujarati word-initial vowel sign `⟨bow⟩િ` is the clearest — it is the exact shape that
  was bought for Devanagari one script over. Where a script has no corpus in these fixtures, the
  vocabulary for it is probably incomplete rather than known complete.

* **Whitespace-only messages.** The API refuses a message that is only whitespace, so the frame's
  behaviour there is unmeasurable and unasserted. A message whose content strips to nothing
  otherwise — private-use or control characters alone — is measured and costs the frame plus one.

## What the accuracy numbers do and do not prove

* **Witness coverage certifies the vocabulary, not the encoder.** Every piece in
  `data/pieces_*.json` carries the probe that priced it at one token, and coverage is 100% of both
  files. That says each piece is a real token. It says nothing about whether the *stream* handed to
  the tiler is the string the tokenizer segmented — and where the two disagree, a fully witnessed
  vocabulary can still produce a wrong count. The corollary is tempting and wrong: "every piece is
  witnessed, so a document we over-charge must be missing a piece" holds only if the structure is
  right.

* **A piece is accepted on a membership probe, never on a corpus delta.** The corpora only ever
  decide which candidate gets asked. So the accuracy figures are not fitted in the usual sense — but
  they are also not out-of-sample for the corpora that did the asking.

* **Which corpora are held out is not symmetric.** UDHR and MultiPL-E select, accept and reject
  nothing; they are read at the end to find out whether a change worked. The 1,741-document Rosetta
  sample is a *mining* corpus — every campaign bisects against it — so its rate is in-sample; the
  250-document holdout is drawn from blocks that sample never touched. Read the four numbers with
  that in mind.

* **"Nothing under-counts" is a statement about the texts it was read over.** It is re-derived by
  re-scanning every stored measurement rather than quoted from a previous run, and it has been wrong
  before precisely because the store grew: populations that were not in the smaller cache turned up
  the moment the scan was run against the larger one. It is a strong claim about a large and varied
  set of texts, not a theorem.

* **A corpus chosen for convenience cannot rank the languages.** Where the vocabulary is thin was
  measured by scoring 350,000 rows across the 350 languages of Goldfish, and that measurement moved
  the target twice: the error was not mainly Brahmic, and the largest single defect was Syriac. Any
  statement of the form "this model is weak at X" that is not backed by a balanced sweep is a
  statement about which corpus happened to be on disk.

* **A parallel corpus arbitrates; a synthetic grid proposes.** Agreement among synthetic probes is
  not evidence about real text — twenty-two templates once agreed unanimously on a mark spelling
  that more than doubled UDHR error the moment it was run over the corpora. Rules here are settled
  on real parallel text and only proposed on grids.

## Where the working record lives

This file is the current state. The campaign-by-campaign record — what each residue turned out to be,
which rival explanations were refuted, and the instrument traps that cost a campaign each — lives in
the private development repo as `PITFALLS.md`, organized by the trap rather than by the campaign. The
probe evidence itself is the measurement store there; the narrative history of this file is in its
git log.
