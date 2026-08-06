"""The marker vocabulary and the measured tables — data, not logic.

Everything here is either the notation the rest of the package shares, or a table of which codepoints
behave which way. The tables were measured against ``count_tokens``; where a comment says a table
must stay enumerated, that is load-bearing.
"""

import re

# ---- marker notation ----------------------------------------------------------------------------

# The engine computes over marked strings in which each structural marker is ONE codepoint, so the
# tiling DP can do per-position arithmetic. All are permanent Unicode noncharacters, which can never
# appear in interchanged text, so a literal `^` or `↑` in the input is never mistaken for a marker.
BOW_G, EOW_G, PAD_G = "\ufdd0", "\ufdd1", "\ufdd2"
SHIFT_G, CAPS_G = "\ufdd3", "\ufdd4"

MARKER_GLYPHS = frozenset({BOW_G, EOW_G, SHIFT_G, CAPS_G})

# The public form: named atoms in mathematical angle brackets, practically absent from real text.
# Literal brackets in text are byte-escaped at render time, so a rendered token always parses back
# unambiguously. Changing the bracket pair is a two-constant edit here.
L, R = "⟨", "⟩"
BOW, EOW, SHIFT, CAPS = f"{L}bow{R}", f"{L}eow{R}", f"{L}shift{R}", f"{L}caps{R}"
PAD = f"{L}pad{R}"

GLYPH_TO_ATOM = {BOW_G: BOW, EOW_G: EOW, PAD_G: PAD, SHIFT_G: SHIFT, CAPS_G: CAPS}
ATOM_TO_GLYPH = {BOW: BOW_G, EOW: EOW_G, SHIFT: SHIFT_G, CAPS: CAPS_G}

# ---- character classes --------------------------------------------------------------------------

WORDY, HARD, DIGIT, PUNCT, SPACE = "wordy", "hard", "digit", "punct", "space"

# Non-ASCII symbols/punctuation that tile over the punct vocabulary rather than standing alone.
# This must stay an enumerated measured set, never a Unicode-category test: the behaviour splits
# per codepoint with no categorical rule (`（` is punct but `）` is hard; `•` punct but `‧` hard).
# Anything unlisted stays HARD, so adding a member only ever moves a confirmed character.
PUNCT_SYMS = frozenset("—»«•°„–−£§€…√→（№†└│།·─═█")

# Symbol-letters measured to take the full word model — ⟨bow⟩…⟨eow⟩ flanks, seam absorption and the
# case markers — exactly like Latin letters, with their cost supplied by the byte floor. Enumerated
# blocks, not a category test: CJK Nl, circled digits, parenthesized letters and astral Lu all
# measured plain, so category Nl/So/Lu splits both ways.
SYMBOL_LETTERS = (
    (0x16EE, 0x16F0),   # Runic golden numbers (Nl, caseless)
    (0x2160, 0x2188),   # Roman numerals (Nl/Lu/Ll, cased pairs)
    (0x24B6, 0x24E9),   # circled letters (So, cased)
)

# Variation selectors are gc=Mn, which would put them in the WORDY class and give them the whole
# word model. They do not take it: `️` alone costs 2 where ⟨bow⟩…⟨eow⟩ flanks read 3, and `⚖️` `⚖︎`
# `✔️` each cost exactly one more than the base character, where the flanks read three more.
# Probed on U+FE00, U+FE0E and U+FE0F — both ends of the block and the middle. The supplementary
# selectors (U+E0100–U+E01EF) are astral and already HARD for that reason.
VARIATION_SELECTORS = (0xFE00, 0xFE0F)

# Marks that separate word runs the way a virama does, but that Unicode does not give combining
# class 9.
# NOT only Brahmic: the U+0300 Latin combining block is here too, measured the same way on
# byte-floor bases (ọ ẹ ṣ ị ǫ) — 41 of 45 cells split, and the four that do not are hosts where a
# precomposed piece hides the boundary. That is 45 UDHR documents and was a third of the residual.
# MEASURED, one character at a time, and the population MUST stay enumerated — the rule is
# orthographic, not numeric, and the neighbouring codepoint is usually a vowel sign that does NOT
# split. Test: `cost(H M H) == cost(H M) + cost(H)` at three cuts on three byte-floor CONSONANT hosts
# per script (evidence and the full no-split list: `data_v4_7/mark_split.json`). Consonant hosts are
# not a detail — measured against a script's independent vowels the same test called all 21 Gujarati
# marks splitters, and the corpus refuted it at once.
EXTRA_KILLERS = frozenset((
    "\u0300",  # COMBINING GRAVE ACCENT
    "\u0301",  # COMBINING ACUTE ACCENT
    "\u0302",  # COMBINING CIRCUMFLEX ACCENT
    "\u0303",  # COMBINING TILDE
    "\u0304",  # COMBINING MACRON
    "\u0308",  # COMBINING DIAERESIS
    "\u030c",  # COMBINING CARON
    "\u0327",  # COMBINING CEDILLA
    "\u0331",  # COMBINING MACRON BELOW
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
    "\u0c03",  # TELUGU SIGN VISARGA
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

# The BMP private-use area is stripped the same way — the character costs nothing AND its two
# neighbours join into one word: `a` + U+F0B7 + `b` prices exactly as `ab` (v4.7 and v3), and the
# HyperTalk `put "` + U+F8FF + `pple" into x` ladder is exact at all four recorded prefixes only
# with the character gone. Seven rows, two codepoints, both families, no row against.
#
# It is private use that is stripped, not "anything unusual": an UNASSIGNED codepoint survives and
# pays its bytes (`a` + U+90095 + `a` costs 6, our byte-floor number, where stripping would read 1).
# The two supplementary private-use planes are unprobed and deliberately left out of the class.
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

# The suffixes an apostrophe binds into the word ahead of it, deleting that word's ⟨bow⟩ — the
# standard English contraction set, lowercase and whole-word only. Measured per member against
# `⟨bow⟩W⟨eow⟩` in the same position: `ll` absorbs (`x'll` = 3 where a paid boundary reads 4) and so
# do `s` `t` `re` `ve` (each 1, via their own token); `d` and `m` price the same either way and are
# carried as the class. Everything else pays: `ji` `ka` `ne` `ye` `ing` `lo` `tion` `zz` `abc` all
# read `'` + a full boundary, and they are not a special population — `ji⟨eow⟩` `ka⟨eow⟩` `ne⟨eow⟩`
# `ye⟨eow⟩` `ing⟨eow⟩` are pieces exactly as `ll⟨eow⟩` is, so a "bow-less piece exists" rule would
# have absorbed them too. Case-sensitive: `x'S` = 3 and `x'LL` = 4 both pay. Whole-word: `x'llo`
# = 4 and `x'lls` = 4 pay.
CONTRACTION_SUFFIXES = frozenset({"s", "t", "d", "m", "ll", "re", "ve"})

# ---- the seam law -------------------------------------------------------------------------------

# ⟨eow⟩ ' ' [case markers] ⟨bow⟩ -> ⟨eow⟩ [case markers] ⟨bow⟩: a single space between two marked
# spans IS the seam and is not written as a character. Exception: a word ending in a combining mark
# from the measured range U+0300-U+0362 (minus U+0345 iota) does not let the seam absorb the space,
# so the space stays a literal token.
SEAM_RE = re.compile("(.)" + EOW_G + " " + "([" + SHIFT_G + CAPS_G + "]*)" + BOW_G)
CHARGING_MARK = re.compile("[\u0300-\u0344\u0346-\u0362]")
