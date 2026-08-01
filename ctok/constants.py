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
