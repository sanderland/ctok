"""The marker notation and the measured character tables.

The tables were measured against ``count_tokens``. Tables marked as enumerated must stay
enumerated: no Unicode-category rule reproduces them.
"""

import re

# ---- marker notation ----------------------------------------------------------------------------

# The engine computes over marked strings in which each structural marker is one codepoint.
BOW_G, EOW_G, PAD_G = "\ufdd0", "\ufdd1", "\ufdd2"
SHIFT_G, CAPS_G = "\ufdd3", "\ufdd4"

MARKER_GLYPHS = frozenset({BOW_G, EOW_G, SHIFT_G, CAPS_G})

# The public form: named atoms in mathematical angle brackets, practically absent from real text.
# Literal brackets in text are byte-escaped at render time, so a rendered token always parses back
# unambiguously.
L, R = "⟨", "⟩"
BOW, EOW, SHIFT, CAPS = f"{L}bow{R}", f"{L}eow{R}", f"{L}shift{R}", f"{L}caps{R}"
PAD = f"{L}pad{R}"

GLYPH_TO_ATOM = {BOW_G: BOW, EOW_G: EOW, PAD_G: PAD, SHIFT_G: SHIFT, CAPS_G: CAPS}
ATOM_TO_GLYPH = {BOW: BOW_G, EOW: EOW_G, SHIFT: SHIFT_G, CAPS: CAPS_G}

# Scraped text can contain the noncharacters used above. NFC strips BMP private-use input, so these
# five private-use codepoints are safe internal escapes inserted after NFC. The byte floor and
# renderer map them back to the original noncharacters.
LITERAL_MARKER_ESCAPES = {glyph: chr(0xE000 + i) for i, glyph in enumerate(GLYPH_TO_ATOM)}
ESCAPED_MARKER_LITERALS = {escape: glyph for glyph, escape in LITERAL_MARKER_ESCAPES.items()}
LITERAL_MARKER_ESCAPE_TABLE = str.maketrans(LITERAL_MARKER_ESCAPES)

# ---- character classes --------------------------------------------------------------------------

WORDY, HARD, DIGIT, PUNCT, SPACE = "wordy", "hard", "digit", "punct", "space"

# Non-ASCII symbols/punctuation that tile over the punct vocabulary rather than standing alone.
# Enumerated: the behaviour splits per codepoint with no categorical rule (`（` is punct but `）`
# is hard). Anything unlisted stays HARD.
PUNCT_SYMS = frozenset("—»«•°„–−£§€…√→（№†└│།·─═█")

# The category-So members of CJK Symbols and Punctuation, which `_marks_like_punct` reaches by
# category P and so left marked. Each measured markerless on six frames in both families.
IDEOGRAPHIC_SYMBOLS = frozenset("〄〒〓〠〶〷〾〿")


# Symbol-letters measured to take the full word model (⟨bow⟩ and ⟨eow⟩ flanks, seam absorption, case
# markers) exactly like Latin letters. Enumerated blocks: category Nl/So/Lu splits both ways, and
# the Hangzhou numerals (also Nl) measured markerless, so it is the block that predicts, not the
# category.
SYMBOL_LETTERS = (
    (0x16EE, 0x16F0),   # Runic golden numbers (Nl, caseless)
    (0x2160, 0x2188),   # Roman numerals (Nl/Lu/Ll, cased pairs)
    (0x24B6, 0x24E9),   # circled letters (So, cased)
    (0xA6E6, 0xA6EF),   # Bamum number-letters (Nl, caseless)
)

# Variation selectors are gc=Mn but take no word model: each costs one more than its base
# character, where ⟨bow⟩ and ⟨eow⟩ flanks would read three more. The supplementary selectors
# (U+E0100 to U+E01EF) are astral and already HARD.
VARIATION_SELECTORS = (0xFE00, 0xFE0F)

# ---- normalization ------------------------------------------------------------------------------

# C0/C1 controls the API strips before tokenizing (cost 0), i.e. every gc=Cc except TAB, LF and NUL.
STRIP_CONTROL = re.compile("[\x01-\x08\x0B-\x1F\x7F\x80-\x9F]")

# BMP private use is stripped the same way, and its two neighbours join into one word. Unassigned
# codepoints survive and pay their bytes; the supplementary private-use planes are unprobed and
# deliberately left out.
STRIP_PRIVATE = re.compile("[-]")

# Lone surrogates are valid in a str but not UTF-8-encodable, so they would crash the byte floor.
# They can never be genuine tokenizer input; fold each to U+FFFD, which prices as an ordinary
# 3-byte HARD character. This is what keeps token_count total on any str.
SURROGATE = re.compile(r"[\ud800-\udfff]")

# Space separators the tokenizer treats identically to U+0020: all Zs except U+3000 (ideographic
# space), plus Zl/Zp. NB U+3000, TAB and LF each have their own cost. NUL is not stripped but
# tokenizes exactly like a space, so it is folded here too.
FUNNY_SPACE = re.compile("[\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F]")

# The four standard curly quotes fold to their ASCII forms (v3 only; NFC does not do this). The
# low-9 mark U+201E is a different token and is deliberately not folded.
QUOTE_FOLD = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201C": '"', "\u201D": '"'})

# The suffixes an apostrophe binds into the word ahead of it, deleting that word's ⟨bow⟩. This is the
# standard English contraction set, lowercase and whole-word only. Measured per member; other
# suffixes pay a full boundary even when their own piece exists, so no piece-based rule reproduces
# this. Case-sensitive and whole-word (`x'S`, `x'LL`, `x'llo`, `x'lls` all pay).
CONTRACTION_SUFFIXES = frozenset({"s", "t", "d", "m", "ll", "re", "ve"})

# ---- the seam law -------------------------------------------------------------------------------

# ⟨eow⟩ ' ' [case markers] ⟨bow⟩ -> ⟨eow⟩ [case markers] ⟨bow⟩: a single space between two marked
# spans is the seam and is not written as a character.
SEAM_RE = re.compile("(.)" + EOW_G + " " + "([" + SHIFT_G + CAPS_G + "]*)" + BOW_G)
