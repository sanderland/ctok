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

# The one canonical-combining-class-9 character that does not separate word runs: measured over
# as a separator on its own script's consonants and under wherever no letter precedes it. See
# :func:`normalize.is_separator` for the grid.
NON_SEPARATORS = frozenset("ฺ")   # THAI CHARACTER PHINTHU

# Marks that separate word runs the way a virama does, but without combining class 9. Measured
# one character at a time on byte-floor consonant hosts; enumerated, because the rule is
# orthographic (the neighbouring codepoint is usually a vowel sign that does not split). The
# U+0300 block is handled as a range instead. See :data:`SEPARATOR_MARKS`.
SEPARATOR_SIGNS = frozenset((
    "\u0740",  # SYRIAC FEMININE DOT
    "\u0741",  # SYRIAC QUSHSHAYA
    "\u0742",  # SYRIAC RUKKAKHA
    "\u0743",  # SYRIAC TWO VERTICAL DOTS ABOVE
    "\u0744",  # SYRIAC TWO VERTICAL DOTS BELOW
    "\u0745",  # SYRIAC THREE DOTS ABOVE
    "\u0746",  # SYRIAC THREE DOTS BELOW
    "\u0747",  # SYRIAC OBLIQUE LINE ABOVE
    "\u0748",  # SYRIAC OBLIQUE LINE BELOW
    "\u0749",  # SYRIAC MUSIC
    "\u074a",  # SYRIAC BARREKH
    "\u093c",  # DEVANAGARI SIGN NUKTA
    "\u0951",  # DEVANAGARI STRESS SIGN UDATTA
    "\u0952",  # DEVANAGARI STRESS SIGN ANUDATTA
    "\u0953",  # DEVANAGARI GRAVE ACCENT
    "\u0954",  # DEVANAGARI ACUTE ACCENT
    "\u09bc",  # BENGALI SIGN NUKTA
    "\u09fe",  # BENGALI SANDHI MARK
    "\u0a3c",  # GURMUKHI SIGN NUKTA
    "\u0abc",  # GUJARATI SIGN NUKTA
    "\u0afd",  # GUJARATI SIGN THREE-DOT NUKTA ABOVE
    "\u0afe",  # GUJARATI SIGN CIRCLE NUKTA ABOVE
    "\u0aff",  # GUJARATI SIGN TWO-CIRCLE NUKTA ABOVE
    "\u0b3c",  # ORIYA SIGN NUKTA
    "\u0b55",  # ORIYA SIGN OVERLINE
    # U+0C03 TELUGU SIGN VISARGA is deliberately not here: it is a spacing mark (Mc, ccc 0) that
    # measures as plain word material, closing a word with a `ః⟨eow⟩` piece rather than splitting it.
    "\u0c3c",  # TELUGU SIGN NUKTA
    "\u0cbc",  # KANNADA SIGN NUKTA
    "\u0e47",  # THAI CHARACTER MAITAIKHU
    "\u0e48",  # THAI CHARACTER MAI EK
    "\u0e49",  # THAI CHARACTER MAI THO
    "\u0e4a",  # THAI CHARACTER MAI TRI
    "\u0e4b",  # THAI CHARACTER MAI CHATTAWA
    "\u0e4c",  # THAI CHARACTER THANTHAKHAT
    "\u0e4e",  # THAI CHARACTER YAMAKKAN
    "\u0ec8",  # LAO TONE MAI EK
    "\u0ec9",  # LAO TONE MAI THO
    "\u0eca",  # LAO TONE MAI TI
    "\u0ecb",  # LAO TONE MAI CATAWA
    "\u0ecc",  # LAO CANCELLATION MARK
    "\u0ece",  # LAO YAMAKKAN
    "\u0f18",  # TIBETAN ASTROLOGICAL SIGN -KHYUD PA
    "\u0f19",  # TIBETAN ASTROLOGICAL SIGN SDONG TSHUGS
    "\u0f35",  # TIBETAN MARK NGAS BZUNG NYI ZLA
    "\u0f37",  # TIBETAN MARK NGAS BZUNG SGOR RTAGS
    "\u0f39",  # TIBETAN MARK TSA -PHRU
    "\u0f3e",  # TIBETAN SIGN YAR TSHES
    "\u0f3f",  # TIBETAN SIGN MAR TSHES
    "\u0f86",  # TIBETAN SIGN LCI RTAGS
    "\u0f87",  # TIBETAN SIGN YANG RTAGS
    "\u0fc6",  # TIBETAN SYMBOL PADMA GDAN
    "\u1037",  # MYANMAR SIGN DOT BELOW
    "\u17b4",  # KHMER VOWEL INHERENT AQ
    "\u17b5",  # KHMER VOWEL INHERENT AA
    "\u17c9",  # KHMER SIGN MUUSIKATOAN
    "\u17ca",  # KHMER SIGN TRIISAP
    "\u17cb",  # KHMER SIGN BANTOC
    "\u17cc",  # KHMER SIGN ROBAT
    "\u17cd",  # KHMER SIGN TOANDAKHIAT
    "\u17ce",  # KHMER SIGN KAKABAT
    "\u17cf",  # KHMER SIGN AHSDA
    "\u17d0",  # KHMER SIGN SAMYOK SANNYA
    "\u17d1",  # KHMER SIGN VIRIAM
    "\u17d3",  # KHMER SIGN BATHAMASAT
    "\u17dd",  # KHMER SIGN ATTHACAN
    "\u1a75",  # TAI THAM SIGN TONE-1
    "\u1a76",  # TAI THAM SIGN TONE-2
    "\u1a77",  # TAI THAM SIGN KHUEN TONE-3
    "\u1a78",  # TAI THAM SIGN KHUEN TONE-4
    "\u1a79",  # TAI THAM SIGN KHUEN TONE-5
    "\u1a7a",  # TAI THAM SIGN RA HAAM
    "\u1a7b",  # TAI THAM SIGN MAI SAM
    "\u1a7c",  # TAI THAM SIGN KHUEN-LUE KARAN
    "\u1a7f",  # TAI THAM COMBINING CRYPTOGRAMMIC DOT
    "\u1b34",  # BALINESE SIGN REREKAN
    "\u1b6b",  # BALINESE MUSICAL SYMBOL COMBINING TEGEH
    "\u1b6c",  # BALINESE MUSICAL SYMBOL COMBINING ENDEP
    "\u1b6d",  # BALINESE MUSICAL SYMBOL COMBINING KEMPUL
    "\u1b6e",  # BALINESE MUSICAL SYMBOL COMBINING KEMPLI
    "\u1b6f",  # BALINESE MUSICAL SYMBOL COMBINING JEGOGAN
    "\u1b70",  # BALINESE MUSICAL SYMBOL COMBINING KEMPUL WITH JEGOGAN
    "\u1b71",  # BALINESE MUSICAL SYMBOL COMBINING KEMPLI WITH JEGOGAN
    "\u1b72",  # BALINESE MUSICAL SYMBOL COMBINING BENDE
    "\u1b73",  # BALINESE MUSICAL SYMBOL COMBINING GONG
    "\ua9b3",  # JAVANESE SIGN CECAK TELU
))

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

# ---- marks that stand outside the word -----------------------------------------------------------

# Combining marks that close the word before themselves, exactly as a virama does
# (`normalize.is_separator` folds this range in): `q́z` = `⟨bow⟩q⟨eow⟩` + mark + `⟨bow⟩z⟨eow⟩`, so an
# accent makes two words out of one. Two oracle frames on one-token hosts distinguish the
# spellings. A sweep covered U+0300 to U+036F on 21 hosts across 13 scripts and both families, with
# no dissent. U+0345 and the combining Latin letters U+0363 to U+036F pin both ends of the range
# from outside by reading "inside the word". U+0340, U+0341, U+0343, and U+0344 are NFC-folded away
# and inside the range for that reason alone.
SEPARATOR_MARKS = re.compile("[\u0300-\u0344\u0346-\u0362]")

# The same question asked of every other combining block of the BMP: 418 marks swept on the same
# two frames, both families, no dissent. The split is orthographic, as for Thai:
#
#   OUTSIDE the word   accents, tone marks, cantillation and annotation
#   INSIDE the word    vowel points and combining letters (niqqud, harakat, the Syriac vowels,
#                      Thaana, Samaritan, the combining Latin/Cyrillic letter blocks)
#
# Most ranges are pinned on both sides by an inside-the-word neighbour in the same block; where a
# range abuts unassigned codepoints, it is written to the marks actually probed. The N'Ko and
# Mandaic marks have no in-script one-token host and rest on `q` and `б` alone.
SEPARATOR_ANNOTATIONS = re.compile(
    "[\u0483-\u0489\u0591-\u05af\u0658\u06df-\u06e0\u06ea-\u06ec"
    "\u07eb-\u07f3\u07fd\u0859-\u085b\u0898-\u089f\u08ca-\u08d3\u08e0-\u08e1"
    "\u0818-\u0819\u082d\u08ea-\u08ef\u135d-\u135f"
    "\u180b-\u180d\u180f\u1939-\u193b"
    "\u1ab0-\u1abe\u1ac1-\u1acb\u1cd0-\u1ce8\u1ced\u1cf4\u1cf8-\u1cf9"
    "\u1be6\u1c37\u1cf7"
    "\u1dc0-\u1dd2\u1df5-\u1dff\u20d0-\u20f0\ua66f-\ua672\ua67c-\ua67d"
    "\u2cef-\u2cf1\u302a-\u302f\u3099-\u309a"
    "\ua6f0-\ua6f1\ua8e0-\ua8f1\ua92b-\ua92d\uaabf\uaac1\uabec"
    "\ufe20-\ufe2f]")
