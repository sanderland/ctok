# Limits

`ctok` is an empirical reconstruction. It reproduces recorded counts, but it is not Anthropic's
tokenizer and has no access to an official token stream.

## Scope

- Counts are the target. `tokenize()` returns one minimum-cost tiling when several may fit the same
  count. Treat its boundaries as explanatory.
- The frame covers one user message. System prompts, tools, images, documents, and multi-turn
  requests add structure that this package does not model.
- v3 and v4.7 have measured vocabularies. v5 has a measured frame and borrows v4.7's vocabulary.
- Whitespace-only messages cannot be measured because the API rejects them.

## Known risks

- Mixed-script words such as `volleyயும்`, `DMামেক`, and `IRGCৰ` cross a boundary that the current
  membership templates cannot isolate. Their components can be exact while the full word is one
  token high.
- Unicode classification comes from the running Python version, with a few measured corrections.
  Recently assigned characters can therefore behave differently across Python Unicode tables.
- The BMP private-use area is measured as stripped. Supplementary private-use planes 15 and 16 were
  not probed and are treated as ordinary astral characters.
- The synthetic v3 string containing two adjacent Devanagari vowel signs with no consonant is one
  token high. v4.7 is exact on the same shape.
- A few emoticon runs at word seams are one token high even though each run prices exactly alone.
  The unexplained part is the join.
- Some scripts have no suitable mining corpus. Membership-positive candidates remain unpublished
  when no natural text can test their effect.
- Mojibake, OCR debris, bidi controls, and long control-character runs occur in scraped corpora, but
  passing those rows does not establish broad coverage of malformed text.

## What the evidence proves

Every published piece has a fixed membership witness or is structural. A witness establishes that
the piece costs one token in its recorded configuration. It does not establish that the encoder
always writes that piece, or that a document with a fully witnessed vocabulary must be exact.

Corpora have different roles:

- Goldfish and both Rosetta Code samples may identify work and select candidates.
- UDHR and MultiPL-E are held out. They only evaluate completed changes.
- Candidates are accepted by membership probes, not by a corpus improvement.

The current stores contain no under-counts across 1,664,940 v3 texts and 1,722,961 v4.7 texts. That
claim is rechecked as the stores grow. It is strong evidence about those texts, not a theorem about
all Unicode input.

A balanced corpus can compare languages; a convenience sample cannot. Synthetic grids propose
rules, while parallel natural text decides between rival rules. The private development repository
keeps the probe transcripts, rejected hypotheses, and campaign history.
