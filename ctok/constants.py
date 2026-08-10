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
# The U+0300 combining block used to be here, nine members of it, on the strength of the byte-floor
# host test below. It is a RANGE and it is all of it: see :data:`SEPARATOR_MARKS`, whose instrument
# is a host whose whole word is ONE token and which can therefore tell the two spellings apart.
# MEASURED, one character at a time, and the population MUST stay enumerated — the rule is
# orthographic, not numeric, and the neighbouring codepoint is usually a vowel sign that does NOT
# split. Test: `cost(H M H) == cost(H M) + cost(H)` at three cuts on three byte-floor CONSONANT hosts
# per script (evidence and the full no-split list: `data_v4_7/mark_split.json`). Consonant hosts are
# not a detail — measured against a script's independent vowels the same test called all 21 Gujarati
# marks splitters, and the corpus refuted it at once.
EXTRA_KILLERS = frozenset((
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
# spans IS the seam and is not written as a character.
SEAM_RE = re.compile("(.)" + EOW_G + " " + "([" + SHIFT_G + CAPS_G + "]*)" + BOW_G)

# ---- marks that stand outside the word -----------------------------------------------------------

# Combining marks that close the word BEFORE themselves, exactly as a virama does; `normalize.
# is_killer` folds this range into that population.
#
# Two ORACLE frames per mark decide it, and neither consults our own count:
#
#     m   = `x qM x` - `x q x` - 1     the mark's own cost — both spellings charge m + 1 here
#     gap = `x qM5 x` - `x q5 x`       m if the word closes before the mark, m + 1 if it does not
#
# The host must be one whose whole word is a single token (`x q x` = 10 on v3), because that is the
# only place the two spellings differ at all: on a byte-floored host `⟨bow⟩H⟨eow⟩` and
# `⟨bow⟩H` + `⟨eow⟩` cost the same and both frames collapse. That collapse is why this block was
# previously read as nine splitting marks under a host-dependent predicate — the earlier test ran on
# byte-floor consonant hosts, where every mark reads "splits" and no mark can read anything else.
#
# Swept over every codepoint of U+0300–U+036F on 21 one-token hosts spanning Latin, Greek, Cyrillic,
# Armenian, Hebrew, Arabic, Devanagari, Bengali, Tamil, Telugu, Thai, Myanmar and Hiragana, both
# families: U+0300–U+033F, U+0342 and U+0346–U+0362 read "closes before" on every host in both
# families, with no host and no family dissenting on any mark, while U+0345 YPOGEGRAMMENI and the
# combining Latin letters U+0363–U+036F read "inside the word" just as uniformly and so pin both
# ends of the range from outside it. U+0340 0341 0343 0344 cannot be measured — NFC folds them to
# 0300 0301 0313 0308+0301 — and are inside the range for that reason alone.
#
# `q́z` = `⟨bow⟩q⟨eow⟩` + the mark + `⟨bow⟩z⟨eow⟩`, so a word is TWO words either side of an
# accent. This range is also exactly the population the retired `_charging_border` enumerated from
# its digit-frame/letter-frame differential: that differential was the same fact read one step too
# late, as an extra ⟨eow⟩ the word writes at a space border rather than as the word ending early.
SEPARATOR_MARKS = re.compile("[\u0300-\u0344\u0346-\u0362]")

# The same question asked of every other combining block of the BMP, on the same two frames and on
# in-script one-token hosts where the script has any (Cyrillic бвдзйэя, Hebrew אי, Arabic دسم,
# Devanagari कतनम) as well as on `q`. 418 marks swept, both families, no host and no family
# dissenting on any one of them, and the answer is orthographic rather than numeric — the same
# distinction `is_killer` already draws for Thai:
#
#   OUTSIDE the word   accents, tone marks, cantillation and annotation — Cyrillic titlo and its
#                      relatives, the Hebrew te'amim, Vedic tone, Ethiopic gemination, the Arabic
#                      tone marks and empty-centre stops, and the four cross-script combining
#                      supplements (U+1AB0, U+1DC0, U+20D0, U+FE20)
#   INSIDE the word    vowel points and combining LETTERS — Hebrew niqqud, Arabic harakat, the
#                      Syriac vowels and superscript alaph, Thaana, Samaritan vowels, and every
#                      block of combining Latin/Cyrillic letters (U+0363, U+1ABF, U+1ACC, U+1DD3,
#                      U+2DE0, U+A674)
#
# Most of these ranges are pinned on BOTH sides by an inside-the-word neighbour in the same block,
# which is the strongest form this evidence takes: 0658 between 064B–0657 and 0659–065F, 06DF–06E0
# between 06D6–06DC and 06E1–06E8, 08EA–08EF between 08E3–08E9 and 08F0–08FF, 0818–0819 and 082D
# among the Samaritan vowels, 1AB0–1ABE / 1AC1–1ACB around 1ABF–1AC0, 1DC0–1DD2 and 1DF5–1DFF
# around 1DD3–1DF4, A66F–A672 and A67C–A67D around A674–A67B, and the Hebrew accents 0591–05AF
# against the niqqud 05B0–05C7. Where a range abuts unassigned codepoints or non-marks instead
# (0483–0489, 135D–135F, 20D0–20F0, FE20–FE2F, the Vedic tones) the block edge is all there is,
# and the range is written to the assigned marks that were actually probed.
#
# A second pass took the blocks the first one missed, found by scanning every cached probe that
# still under-counted after it: the N'Ko tone marks U+07EB–U+07F3 and dantayalan U+07FD, the three
# Mandaic marks U+0859–U+085B, and the Arabic Extended-B annotations U+0898–U+089F, U+08CA–U+08D3
# and U+08E0–U+08E1. The N'Ko and Mandaic ones read "closes before" on `q` and `б` only — neither
# script has a letter whose whole word is one token, so they have no in-script confirmation. The
# Arabic ones do, on `د`, and U+08CA–U+08D3 / U+08E0–U+08E1 are pinned on both sides by U+08D4–
# U+08DF, twelve Quranic word-abbreviations in the middle of the same block that read "inside the
# word" on all three hosts.
#
# A fourth pass, steered the same way, added the four Mongolian free variation selectors
# U+180B–U+180D and U+180F and the three Limbu SIGNs U+1939–U+193B. Limbu is the cleanest split in
# the whole sweep: its six VOWEL SIGNs and its anusvara read "inside the word" and its three tone
# and annotation signs read "closes before", on `q`, `б` and the in-script `ᠠ`, in both families.
SEPARATOR_ANNOTATIONS = re.compile(
    "[\u0483-\u0489\u0591-\u05af\u0658\u06df-\u06e0\u06ea-\u06ec"
    "\u07eb-\u07f3\u07fd\u0859-\u085b\u0898-\u089f\u08ca-\u08d3\u08e0-\u08e1"
    "\u0818-\u0819\u082d\u08ea-\u08ef\u135d-\u135f"
    "\u180b-\u180d\u180f\u1939-\u193b"
    "\u1ab0-\u1abe\u1ac1-\u1acb\u1cd0-\u1ce8\u1ced\u1cf4\u1cf8-\u1cf9"
    "\u1dc0-\u1dd2\u1df5-\u1dff\u20d0-\u20f0\ua66f-\ua672\ua67c-\ua67d"
    "\ufe20-\ufe2f]")
