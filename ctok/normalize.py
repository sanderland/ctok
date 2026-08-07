"""Text → the marked stream: everything that happens before the tiling.

    NFC + quote fold  ->  class split  ->  case marking  ->  boundary markers written in

``stream()`` is the output: a single string with word boundaries, case and absorbed spaces written
in as markers, which ``engine.py`` then tiles. Every rule here is either a designed rewrite of the
text or a measured fact about the oracle. No costs live in this module.
"""

from __future__ import annotations

import unicodedata

from .constants import (
    BOW_G, CAPS_G, CHARGING_MARK, CONTRACTION_SUFFIXES, DIGIT, EOW_G, EXTRA_KILLERS, FUNNY_SPACE,
    HARD, PUNCT, PUNCT_SYMS, QUOTE_FOLD, SEAM_RE, SHIFT_G, SPACE, STRIP_CONTROL, STRIP_PRIVATE,
    SURROGATE, SYMBOL_LETTERS, VARIATION_SELECTORS, WORDY,
)


def nfc(text: str, *, fold_quotes: bool = True) -> str:
    """Normalize as Claude does before tokenizing: NFC, strip the zero-cost control and private-use
    characters, optionally fold the curly quotes, then fold space-separator variants (and NUL) to
    U+0020.

    ``fold_quotes`` is a per-family flag: v3 folds, v4.7 measured not to.
    """
    text = SURROGATE.sub("�", text)
    text = STRIP_CONTROL.sub("", unicodedata.normalize("NFC", text)).replace("\x00", " ")
    text = STRIP_PRIVATE.sub("", text)
    if fold_quotes:
        text = text.translate(QUOTE_FOLD)
    return FUNNY_SPACE.sub(" ", text)


def is_hard_cp(o: int) -> bool:
    """Han / Hangul syllables / astral — the isolated, character-based letter scripts."""
    return (
        o >= 0x10000                  # all astral (CJK ext, astral scripts, emoji)
        or 0x4E00 <= o <= 0x9FFF      # CJK Unified
        or 0x3400 <= o <= 0x4DBF      # CJK Ext A
        or 0xF900 <= o <= 0xFAFF      # CJK Compatibility
        or 0xAC00 <= o <= 0xD7A3      # Hangul syllables
        # The ideographic ITERATION and CLOSING marks. Both are letters by category (Lm, Lo), so the
        # wordy branch below claimed them and opened a WORD on them: `日々` streams
        # `⟨bow⟩日⟨bow⟩々⟨eow⟩` and costs two tokens more than the oracle pays. They continue the Han
        # run they follow. Measured on opus-4-7: `日々` `人々` `様々` `々` `日〆` all read BASE+2 where
        # we charged BASE+4. The katakana prolonged sound mark `ー` and small `ヶ` do NOT behave this
        # way — they were probed in the same sweep and are exact as wordy — so this is the two marks
        # and not the CJK punctuation block.
        or o in (0x3005, 0x3006)      # 々 〆
    )


def classify(c: str) -> str:
    """The class of a single character."""
    o = ord(c)
    cat = unicodedata.category(c)
    if cat[0] == "Z" or c in "\t\n\r\f\v":
        return SPACE
    if any(lo <= o <= hi for lo, hi in SYMBOL_LETTERS):
        return WORDY
    if cat == "Nd" and (o < 0x80 or 0x0660 <= o <= 0x0669 or 0x06F0 <= o <= 0x06F9):
        return DIGIT
    if o < 0x80 and cat[0] in ("P", "S"):
        # ASCII punctuation and ASCII symbols both tile over the merged punct vocabulary, so
        # operators (`==`, `=>`, `});`) form one PUNCT run instead of exploding into HARD chars.
        return PUNCT
    if c in PUNCT_SYMS:
        return PUNCT
    if VARIATION_SELECTORS[0] <= o <= VARIATION_SELECTORS[1]:
        return HARD                   # gc=Mn, but they take no word model at all
    if cat[0] in ("L", "M") and not is_hard_cp(o):
        # Brahmic scripts are subsumed into WORDY: they tile over the same marked-fragment
        # vocabulary plus the per-codepoint byte floor as any other letter script.
        return WORDY
    return HARD


def mark_case(span: str, allcaps_min: int | None = 4) -> str:
    """Cased span → the marked form the tiler consumes.

    A case marker fires only on a WHOLE span: a pure all-caps span of length >= ``allcaps_min``
    becomes ⟨caps⟩ + lowercase, a pure title-case span becomes ⟨shift⟩ + lowercase. Everything
    else — internal, final or mixed capitals, and short all-caps runs — stays literal, so
    ``GaN``/``WiFi``/``QQ`` keep their bytes. ``allcaps_min=None`` disables ⟨caps⟩ (v4.7).
    """
    if "İ" in span or "ẞ" in span:
        # Capitals with irregular case pairs are served literally through cased pieces: İ has no
        # clean lowercase byte form (it lowercases to i + U+0307), and ẞ measured literal in every
        # position. Both over-charge on the marker paths.
        return span
    if allcaps_min is not None and span.isupper() and len(span) >= allcaps_min:
        return CAPS_G + span.lower()
    if span[:1].isupper() and not any(c.isupper() for c in span[1:]):
        return SHIFT_G + span.lower()
    return span


# ---- the marked stream --------------------------------------------------------------------------


def _seam_sub(match) -> str:
    """The seam law, minus the two places a real space is NOT absorbable.

    A terminal mark is its own unmarked run (see :func:`_runs`), so it cannot occur immediately
    before this seam: the preceding word has already closed on the other side of the mark. A
    combining mark that remains inside a word is the one measured exception here.
    """
    ch, case_markers = match.group(1), match.group(2)
    if CHARGING_MARK.fullmatch(ch):
        return match.group(0)
    return ch + EOW_G + case_markers + BOW_G


def _is_punct_text(body: str) -> bool:
    """Unicode punctuation, regardless of which internal class it lands in — the Devanagari danda,
    the ideographic full stop, the Arabic and Ethiopic stops are all category Po but classify HARD,
    and they take the same markers as ASCII punctuation."""
    return bool(body) and all(unicodedata.category(c).startswith("P") for c in body)


def _is_symbol_text(body: str) -> bool:
    """Unicode symbols (category S*), which take the same whitespace markers as punctuation.

    Measured 2026-07-31 (`hard_boundary` grids): with digit anchors, `1c1` is exact for every such
    character — the intrinsic cost was never wrong — while `1 c1` and `1c 1` each cost one more than
    we charged and `1 c 1` two more, which is a ⟨bow⟩ and an ⟨eow⟩ at the space borders. `1c  1` is
    exact, so run-kills-marker applies here too.

    Confirmed on 44 characters the rule was not derived from. Three of them — `±`, `©`, `®` — first
    looked like exceptions, showing no gap on the right; they are not. Each has a single-token
    `X⟨eow⟩` piece, so the oracle charges 1 for character-plus-marker where `←` pays 2, and the gap
    reads 0 while the marker is written all the same. The rule is uniform; only the vocabulary
    differs. `›` disagrees in the other direction and is recorded as open in
    `data_v4_7/hard_boundary.json`.

    ASTRAL symbols are excluded, and that is measured on the same grid: `🐫` `😀` `🚀` read `1c1`
    exact but `1 c1` and `1c 1` one MORE than we charge and `1 c 1` two more — a boundary written
    where the oracle writes none, the exact mirror of what the BMP characters do. `文 🐫` = 6 is
    the row it costs on real text.
    """
    return bool(body) and all(unicodedata.category(c).startswith("S") and ord(c) < 0x10000
                              for c in body)


def _opens_word(runs: list[tuple[str, str]], i: int) -> bool:
    """Is run ``i`` a lone ``'`` that opens the word after it — ``a 'b``, ``'First``, ``x 'REXX``?

    The boundary before such an apostrophe is NOT absorbed into it. Measured on the whole
    ``a 'X b`` / ``a 'X'b`` / ``a 'X', b`` letter sweep (every letter except the ``'s``/``'t``
    contractions costs one more than an absorbed boundary allows), on the message-start ladder
    (``'d`` ``'m`` ``'F`` ``'First`` = 3, where a piece-swallowed boundary reads 2) and on
    the head-seam probe ``" 'a"`` = 3. The ``⟨bow⟩'`` piece is real — ``'`` alone, ``'.``,
    ``', '`` all price 1 for the pair — it is simply not what the oracle uses in front of a word.

    Only a punct run that is EXACTLY ``'`` qualifies: in ``('`` or ``'''`` the boundary lands on a
    different character and those rows are exact as they stand (``a ('b`` = 4, ``a '''a`` = 4).
    """
    return runs[i][1] == "'" and i + 1 < len(runs) and runs[i + 1][0] == WORDY


def _contraction_seam(runs: list[tuple[str, str]], i: int) -> bool:
    """Does a lone apostrophe immediately left of wordy run ``i`` supply that word's ⟨bow⟩?

    `it's` is one word boundary, not two: the apostrophe IS the boundary, exactly as the seam space
    is. So the word after it is written bare — `x'll` = ⟨bow⟩x⟨eow⟩ + ' + ll⟨eow⟩ = 3, where paying
    for the boundary reads 4. It is the vocabulary that then decides whether a piece swallows the
    pair (`'s⟨eow⟩` does, at 1; `'ll⟨eow⟩` in this family does not, at 2).

    Two conditions, both measured. The suffix must be in ``CONTRACTION_SUFFIXES``, whole-word and
    lowercase. And the apostrophe must be a punct run of its OWN: one that follows other punctuation
    belongs to that run and reaches the word with nothing — `}'s` = 3, `.'s.` = 4, `.'ve.` = 5,
    `a)'s b` = 5, `.'ll.` = 5 are each one more than the seam allows. A letter, a digit, a space run
    or the message edge on the left all let it through: `f's` = 2, `1'll` = 4, `a  'll b` = 5.
    """
    if runs[i][1] not in CONTRACTION_SUFFIXES or i == 0:
        return False
    prev_cls, prev_body = runs[i - 1]
    # A punct run is maximal, so a run that IS the apostrophe cannot have punctuation to its left.
    return prev_cls == PUNCT and prev_body == "'"


def _is_nd_run(body: str) -> bool:
    """A run of decimal digits (Nd), in either the DIGIT or the Nd-HARD class."""
    return all(unicodedata.category(c) == "Nd" for c in body)


def _is_no_run(body: str) -> bool:
    """A run of Unicode *other* numbers (No): vulgar fractions, super/subscripts, circled and
    parenthesized digits, and the script-specific fraction and numeral signs.

    These classify HARD — they are neither Nd nor letters — so before this they took no markers at
    all, and a single space hid it: the seam absorbs the ⟨bow⟩, so `a ½ b` is exact either way. Two
    spaces do not absorb, and there `a  ½  b` reads one MORE than a marker-free ½ allows. Swept over
    every assigned No codepoint below U+3000: 228 of 232 take the ⟨bow⟩ on the double-space probe
    and are exact on the single-space one, with no split by script or by block. The four that differ
    — U+00B2, U+2460, U+2461, U+2463 — disagree on the SINGLE-space probe too, which is a missing
    piece rather than a missing marker, and they are recorded as open rather than excepted here.
    """
    return bool(body) and all(unicodedata.category(c) == "No" for c in body)


def _nonascii_digits(body: str) -> bool:
    """The digit runs measured to take a boundary ⟨bow⟩ at any space border: every non-ASCII Nd run,
    and every No run. Letter scripts measured not to; ASCII Nd runs only strand one against a
    non-ASCII digit neighbour."""
    return (_is_nd_run(body) and not body.isascii()) or _is_no_run(body)


def is_killer(c: str) -> bool:
    """A mark that terminates the orthographic syllable, and so separates word runs.

    Two populations, and the split between them is the honest part. **Viramas** — the Brahmic sign
    that suppresses a consonant's inherent vowel so it can join the next one — are all canonical
    combining class 9, so those 65 characters are DEFINED, not listed. Everything else is
    ENUMERATED in ``EXTRA_KILLERS``: Thai and Lao tone marks, Myanmar dot-below, nukta, the Khmer
    consonant shifters, Tai Tham's tone signs. Those are not a combining class and no numeric rule
    picks them out — a Lao tone mark (ccc 122) splits and the Lao vowel sign beside it (ccc 118)
    does not. What they share is orthographic: a Thai tone mark is written after the whole syllable
    exactly as a virama is written after the whole cluster, and the vowel signs that do not split
    are written inside it.
    """
    return unicodedata.combining(c) == 9 or c in EXTRA_KILLERS


def is_terminal_separator(c: str) -> bool:
    """A killer that stands outside the word rather than closing it from inside.

    Generic combining accents do satisfy the older factorization test: they end the run after the
    mark.  They are not terminal orthographic signs, though, and moving them outside the run makes
    decomposed Latin text systematically too expensive.  FineWeb-2's accent-heavy Latin slices
    distinguish the spellings directly.  The U+0300 block therefore keeps the measured after-mark
    boundary; the Brahmic/SEA terminal population uses the separator spelling.
    """
    return is_killer(c) and not 0x0300 <= ord(c) <= 0x036F


_KILLER = "killer"


def _runs(norm: str) -> list[tuple[str, str]]:
    """The text split into maximal same-class runs, with terminal marks as unmarked separators.

    A killer does not close a word *after itself*. It stands outside the word: the preceding WORDY
    run closes before the mark and a following WORDY run opens after it. Thus ``C killer X`` is
    written ``⟨bow⟩C⟨eow⟩ killer ⟨bow⟩X⟨eow⟩``. This is the same factorization measured by the old
    akshara law, but it also explains word-final and standalone marks without ``killer⟨eow⟩``
    pieces or a stacked-killer exception.

    ``_KILLER`` is deliberately a stream class rather than ``HARD``. The output is unmarked in both
    cases, but keeping the class distinct prevents a neighbouring punctuation or symbol run from
    inheriting the mark and losing its own boundary treatment.
    """
    if not norm:
        return []
    def run_class(ch: str) -> str:
        return _KILLER if is_terminal_separator(ch) else classify(ch)

    out, cur, cur_cls = [], norm[0], run_class(norm[0])
    for ch in norm[1:]:
        c = run_class(ch)
        legacy_killer = is_killer(cur[-1]) and not is_terminal_separator(cur[-1])
        if c == cur_cls and not legacy_killer:
            cur += ch
        else:
            out.append((cur_cls, cur))
            cur, cur_cls = ch, c
    out.append((cur_cls, cur))
    return out


def stream(text: str, model) -> str:
    """Text → the marked stream, in the internal glyph form ``pieces.json`` keys parse to.

    A WORDY run is bracketed ⟨bow⟩…⟨eow⟩ and case-normalized. A single space between two such runs
    is dropped — the ⟨eow⟩⟨bow⟩ seam is what encodes it. Every other space stays literal. Nothing
    else is marked here: whether punctuation wants a marker is for the tiling to reveal.
    """
    return stream_norm(nfc(text, fold_quotes=model.fold_quotes), model)


def stream_norm(norm: str, model) -> str:
    """:func:`stream` over already-normalized text. Split out so a document is NFC-folded once and
    the caller can read the content-final newline run — which ``rstrip`` below drops — off the same
    string it streams (see ``engine.frame_tail``)."""
    # The frame's tail, for a family whose frame HAS one: `engine.tile` reads the run off the same
    # string before dropping it here. A "free" family is stripped on the raw text instead (see
    # `tile`), so there is nothing left to take off here and taking it would eat a folded NBSP.
    if model.frame_tail == "ladder":
        norm = norm.rstrip(model.frame_strip)
    # A single leading space is dropped: the frame ends in ⟨bow⟩ and that ⟨bow⟩ IS the space
    # (' a' = 1). Two or more are a whitespace-run token and stay ('  a' = 2).
    # Where the frame does NOT end in a ⟨bow⟩ (v5), there is no space to stand in for: the leading
    # space is a character like any other, and ' a' costs one more than 'a' rather than the same.
    if model.frame_bow and norm[:1] == " " and norm[1:2] != " ":
        norm = norm[1:]
    runs = _runs(norm)
    if not runs:
        return ""
    caps = model.allcaps_min
    n_runs = len(runs)

    def borders_space(i: int, side: int) -> bool:
        """Does this side of run ``i`` touch a space? Only a space counts — the marker represents an
        absorbed space, so nothing else can stand in for one.

        Message start counts (the frame ends in ⟨bow⟩, which IS a space); message end does not (the
        trailing frame is not a space). A whitespace run is not homogeneous, so what matters is the
        character adjacent to this side: the neighbour's last char looking left, its first looking
        right.
        """
        j = i + side
        if j < 0:
            return model.frame_bow
        if j >= n_runs:
            return False
        if runs[j][0] != SPACE:
            return False
        if side < 0:
            return runs[j][1][-1:] == " "
        # Run-kills-marker (measured 2026-07-30, `punct_ws` grids): a punct right-marker is
        # written for the SEAM space only. Before a run of two or more spaces there is no
        # charge — uniform over run lengths 2/3/4/17 — while tab and newline neighbours keep
        # their (differently priced) boundaries.
        return runs[j][1][:1] == " " and runs[j][1][:2] != "  "

    # The frame ends in ⟨bow⟩, always. A wordy or punct first run writes its own, as does a leading
    # non-ASCII digit run (it borders a space at the message edge); a leading whitespace run absorbs
    # it only if it starts with a real space, since a TAB or NEWLINE cannot. Anything else supplies
    # none, so the frame's ⟨bow⟩ is written here and tiles as itself.
    # A word-opening `'` supplies no ⟨bow⟩ either (see `_opens_word`), and what the frame hands it
    # is a space, so at message start that space is written as the character it is.
    first = runs[0]
    head_quote = _opens_word(runs, 0)
    has_own_bow = not head_quote and (
                   first[0] in (WORDY, PUNCT) or _is_punct_text(first[1])
                   or _is_symbol_text(first[1])
                   or (first[0] in (DIGIT, HARD) and _nonascii_digits(first[1]))
                   or (first[0] == SPACE and first[1][:1] == " "))
    # Nothing to hand out where the frame ends in no ⟨bow⟩: a digit or an ideograph opening the
    # message pays for no marker, which is exactly where v5 counts one token under v4.7.
    out = [] if has_own_bow or not model.frame_bow else [" " if head_quote else BOW_G]
    for i, (cls, body) in enumerate(runs):
        if cls == WORDY:
            # A wordy span is flanked on both sides, always — except where a contraction apostrophe
            # is already its opening boundary (see `_contraction_seam`).
            n = mark_case(body, caps)
            pre = ""
            while n[:1] in (SHIFT_G, CAPS_G):     # case markers precede ⟨bow⟩ in the file's spelling
                pre, n = pre + n[0], n[1:]
            bow = "" if _contraction_seam(runs, i) else BOW_G
            out.append(pre + bow + n + EOW_G)
        elif cls == PUNCT or _is_punct_text(body) or _is_symbol_text(body):
            # A punct span is marked only on the side that borders whitespace: `a! b` gets `!⟨eow⟩`,
            # `a!b` gets a bare `!`. The marker is written unconditionally; the vocabulary decides
            # whether a piece swallows it.
            takes_bow = borders_space(i, -1) and not _opens_word(runs, i)
            out.append((BOW_G if takes_bow else "") + body
                       + (EOW_G if borders_space(i, +1) else ""))
        elif (_is_nd_run(body) or _is_no_run(body)) and cls in (DIGIT, HARD):
            # A digit run takes a leading ⟨bow⟩ when it borders a space — the same rule punct has.
            # The population is measured: every non-ASCII Nd run at any space border, every No run
            # (see `_is_no_run`), plus an ASCII run only against a non-ASCII digit neighbour across
            # the space. No ⟨eow⟩ is ever written, since the message end is not a space.
            takes_bow = _nonascii_digits(body) or (
                i >= 2 and _nonascii_digits(runs[i - 2][1]) and runs[i - 2][0] in (DIGIT, HARD))
            out.append((BOW_G if takes_bow and borders_space(i, -1) else "") + body)
        else:
            out.append(body)                      # HARD letter scripts and whitespace: no markers
    return SEAM_RE.sub(_seam_sub, "".join(out))
