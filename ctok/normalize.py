"""Text → the marked stream: everything that happens before the tiling.

    NFC + quote fold  ->  class split  ->  case marking  ->  boundary markers written in

``stream()`` is the output: a single string with word boundaries, case and absorbed spaces written
in as markers, which ``engine.py`` then tiles. Every rule here is either a designed rewrite of the
text or a measured fact about the oracle. No costs live in this module.
"""

from __future__ import annotations

from functools import cache
import unicodedata

from .constants import (
    BOW_G, CAPS_G, CONTRACTION_SUFFIXES, DIGIT, EOW_G,
    ESCAPED_MARKER_LITERALS,
    EXTRA_KILLERS, FUNNY_SPACE,
    LITERAL_MARKER_ESCAPE_TABLE,
    NON_KILLERS,
    HARD, PUNCT, PUNCT_SYMS, QUOTE_FOLD, SEAM_RE, SEPARATOR_ANNOTATIONS,
    SEPARATOR_MARKS, SHIFT_G, SPACE,
    STRIP_CONTROL, STRIP_PRIVATE,
    SURROGATE, SYMBOL_LETTERS, VARIATION_SELECTORS, WORDY,
)

_KILLER = "killer"
_STRAY_MARK = "stray_mark"

# Python 3.13 ships Unicode 15.1 data; the source models know these Unicode 16.0 case pairs.
_NEW_CASE_PAIRS = {"\u1c89": "\u1c8a", "\ua7cb": "\u0264"}
_NEW_CASED = frozenset(_NEW_CASE_PAIRS) | frozenset(_NEW_CASE_PAIRS.values())


def _lower(text: str) -> str:
    return "".join(_NEW_CASE_PAIRS.get(c, c.lower()) for c in text)


def _is_upper(c: str) -> bool:
    return c in _NEW_CASE_PAIRS or c.isupper()


def _is_lower(c: str) -> bool:
    return c in _NEW_CASE_PAIRS.values() or c.islower()


def _span_is_upper(text: str) -> bool:
    cased = [c for c in text if _is_upper(c) or _is_lower(c)]
    return bool(cased) and all(_is_upper(c) for c in cased)


def nfc(text: str, *, fold_quotes: bool = True) -> str:
    """Apply the measured text normalization. v3 alone folds curly quotes."""
    text = SURROGATE.sub("�", text)
    text = STRIP_CONTROL.sub("", unicodedata.normalize("NFC", text)).replace("\x00", " ")
    # Claude composes decomposed Thai SARA AM, whose compatibility decomposition NFC leaves alone.
    # Lao SARA AM and unrelated compatibility characters do not fold.
    text = text.replace("\u0E4D\u0E32", "\u0E33")
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
        # The ideographic iteration and closing marks are letters by category (Lm, Lo) but continue
        # the Han run they follow; the wordy reading costs two tokens more than the oracle pays.
        # The katakana prolonged sound mark `ー` and small `ヶ` measured exact as wordy.
        or o in (0x3005, 0x3006)      # 々 〆
        # Quranic annotation signs (Mn members that would otherwise reach the letter class):
        # measured as unattached marks, with the boundaries pinned on both sides of both ranges.
        # Combining class does not predict the split.
        or 0x06DD <= o <= 0x06E0      # ۝ ۞ and the two small high zeros
        or 0x06E9 <= o <= 0x06EC      # ۩ and the empty-centre stops
    )


@cache
def classify(c: str) -> str:
    """The stream class of one codepoint, derived from Unicode data and measured tables."""
    if is_killer(c):
        return _KILLER
    if c in _NEW_CASED:
        return WORDY
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
    if o == 0x0CF3:
        # KANNADA SIGN COMBINING ANUSVARA ABOVE RIGHT, assigned in Unicode 15.0: `unicodedata`
        # with older tables reports Cn, which would drop it to HARD. Measured as plain word
        # material (Mc, ccc 0), so pin it WORDY.
        return WORDY
    if cat[0] in ("L", "M") and not is_hard_cp(o):
        # Brahmic scripts are subsumed into WORDY: they tile over the same marked-fragment
        # vocabulary plus the per-codepoint byte floor as any other letter script.
        return WORDY
    return HARD


def mark_case(span: str, allcaps_min: int | None = 4, *, head_mark: bool = False) -> str:
    """Cased span → the marked form the tiler consumes.

    A case marker fires only on a whole span: a pure all-caps span of length >= ``allcaps_min``
    becomes ⟨caps⟩ + lowercase, a pure title-case span becomes ⟨shift⟩ + lowercase. Everything
    else — internal, final or mixed capitals, and short all-caps runs — stays literal, so
    ``GaN``/``WiFi``/``QQ`` keep their bytes. ``allcaps_min=None`` disables ⟨caps⟩ (v4.7).

    Measured blocks, each leaving the span literal:

    * A caseless letter or mark anywhere in the span blocks ⟨caps⟩ (``str.isupper`` is vacuously
      True for ``ヲBUTTヲ`` or ``းUNDPA``, but the oracle spells them literally). ⟨shift⟩ is not
      blocked: a title-case head with a caseless tail keeps its marker.
    * A character with no lowered form blocks either marker (``'ℳ'.lower()`` is ``'ℳ'``, so a
      marker in front of an unchanged body over-counts). İ is the one exception: transparent to
      the title-case test and literal in the lowered body, blocking only at the span head; ẞ
      blocks everywhere.
    * ``head_mark`` — the span is the tail of a word an unattached mark run opened, so its head is
      that mark and neither marker can assert its lowered first letter.
    """
    if head_mark:
        return span
    if "ẞ" in span:
        return span
    if "İ" in span:
        tail = span[1:]
        if _is_upper(span[:1]) and span[:1] != "İ" and \
                not any(_is_upper(c) for c in tail if c != "İ"):
            return SHIFT_G + _lower(span[0]) + "".join(c if c == "İ" else _lower(c)
                                                       for c in tail)
        return span
    unlowerable = any((c in _NEW_CASED or unicodedata.category(c)[0] in ("L", "M"))
                      and not _is_lower(c) and (not _is_upper(c) or _lower(c) == c) for c in span)
    if allcaps_min is not None and _span_is_upper(span) and len(span) >= allcaps_min \
            and not unlowerable:
        # str.lower() applies Unicode's Final_Sigma rule; the oracle's ⟨caps⟩ body does not — it
        # lowers Σ to σ everywhere. An isupper() span contains no ς of its own, so the replace
        # only touches what lower() just produced.
        return CAPS_G + _lower(span).replace("ς", "σ")
    if _lower(span[:1]) == span[:1]:
        return span
    if _is_upper(span[:1]) and not any(_is_upper(c) for c in span[1:]):
        return SHIFT_G + _lower(span)
    return span


# ---- the marked stream --------------------------------------------------------------------------


def _is_selector(ch: str) -> bool:
    return VARIATION_SELECTORS[0] <= ord(ch) <= VARIATION_SELECTORS[1]


def _hard_bow(body: str) -> bool:
    """Whether the first character of a hard run takes a left border marker."""
    return bool(body) and (_is_selector(body[0]) or _marks_like_punct(body[0]))


def _hard_eow(body: str) -> bool:
    """Whether the last character of a hard run takes a right border marker."""
    return bool(body) and (_is_selector(body[-1]) or _marks_like_punct(body[-1]))


def _opens_word(runs: list[tuple[str, str]], i: int) -> bool:
    """Is run ``i`` a lone ``'`` that opens the word after it — ``a 'b``, ``'First``, ``x 'REXX``?

    The boundary before such an apostrophe is not absorbed into it (measured on the letter sweep,
    the message-start ladder, and the head-seam probe). Only a punct run that is exactly ``'``
    qualifies: in ``('`` or ``'''`` the boundary lands on a different character.
    """
    return (runs[i][1] == "'" and i + 1 < len(runs)
            and runs[i + 1][0] in (WORDY, _STRAY_MARK))


def _takes_right_border(cls: str, body: str) -> bool:
    """Does this run write a boundary marker of its own on its right edge?

    Three populations do: punctuation/symbols/format characters, a terminal separator run, and a
    digit run whose last character is a border digit — the runs the pretokenizer's catch-all
    alternative owns. An unattached mark run is not one of them: it writes an ⟨eow⟩, but as a word
    (the ``_STRAY_MARK`` branch of :func:`stream_norm`), and a word lets the contraction seam
    through.
    """
    return (cls == PUNCT
            or (cls == _KILLER and _borders(body[-1]))
            or _hard_eow(body)
            or (cls in (DIGIT, HARD) and _digit_run(body) and _digit_eow(body)))


def _contraction_seam(runs: list[tuple[str, str]], i: int) -> bool:
    """Does a lone apostrophe immediately left of wordy run ``i`` supply that word's ⟨bow⟩?

    `it's` is one word boundary, not two: the apostrophe is the boundary, exactly as the seam
    space is, so the word after it is written bare. The vocabulary then decides whether a piece
    swallows the pair (`'s⟨eow⟩` does; `'ll⟨eow⟩` does not).

    Three conditions, all measured: the suffix is in ``CONTRACTION_SUFFIXES``, whole-word and
    lowercase; the apostrophe is a punct run of its own (one that follows other punctuation
    belongs to that run and reaches the word with nothing); and the run on the far side of the
    apostrophe writes no right-hand border marker of its own (:func:`_takes_right_border`).
    A letter, an ASCII digit, an ideograph, a space run or the message edge on the left all let
    it through.
    """
    if runs[i][1] not in CONTRACTION_SUFFIXES or i == 0:
        return False
    prev_cls, prev_body = runs[i - 1]
    # A punct run is maximal, so a run that is the apostrophe cannot have punctuation to its left.
    if prev_cls != PUNCT or prev_body != "'":
        return False
    return i < 2 or not _takes_right_border(*runs[i - 2])


def _is_nd_run(body: str) -> bool:
    """A run of decimal digits (Nd), in either the DIGIT or the Nd-HARD class."""
    return all(unicodedata.category(c) == "Nd" for c in body)


def _is_no_run(body: str) -> bool:
    """A run of Unicode *other* numbers (No): vulgar fractions, super/subscripts, circled and
    parenthesized digits, and the script-specific fraction and numeral signs.

    These classify HARD but take border markers: swept over every assigned No codepoint below
    U+3000, 228 of 232 take the ⟨bow⟩, with no split by script or block (the four that differ are
    pieces in their own right).
    """
    return bool(body) and all(unicodedata.category(c) == "No" for c in body)


def _borders(ch: str) -> bool:
    """Is this character one that can carry a border marker at all?

    An astral character cannot — the same exclusion :func:`_marks_like_punct` carries for
    punctuation, symbols and emoji, shared by the digit and terminal-separator branches. Swept
    exhaustively: all 30 astral terminal separators and 72 astral border digits read exact with no
    marker written, with BMP controls unmoved. Per border character, as everywhere in this module:
    a mixed run keeps the marker on the side whose own character is BMP.
    """
    return ord(ch) < 0x10000


def _digit_border(ch: str) -> bool:
    """Is this the kind of digit for which the border markers are written — a non-ASCII decimal
    digit, or any of the Unicode *other* numbers?

    The split is ASCII vs not, uniform across scripts: ASCII digits take no border marker of
    their own, everything else does. Astral digits take none either (:func:`_borders`).
    """
    cat = unicodedata.category(ch)
    return (cat == "No" or (cat == "Nd" and not ch.isascii())) and _borders(ch)


def _digit_run(body: str) -> bool:
    """A run the digit-border branch owns: all decimal digits, or all *other* numbers."""
    return _is_nd_run(body) or _is_no_run(body)


def _digit_bow(body: str) -> bool:
    """Does a digit run write ⟨bow⟩ where it borders a space on the left? The run's first
    character decides, not the run as a whole (measured on mixed ASCII/Arabic-Indic runs, the
    only runs where the two readings differ).
    """
    return _digit_run(body) and _digit_border(body[0])


def _digit_eow(body: str) -> bool:
    """Does a digit run write ⟨eow⟩ where it borders a single space on the right? The run's last
    character decides, the mirror of :func:`_digit_bow`.

    The seam hides this marker almost everywhere; it shows only before a run that writes no ⟨bow⟩
    of its own — a CJK or Hangul letter, or ideographic punctuation — where it costs one token.
    """
    return _digit_run(body) and _digit_border(body[-1])


def is_killer(c: str) -> bool:
    """A mark that terminates the orthographic syllable, and so separates word runs.

    Three populations: viramas (defined by canonical combining class 9, not listed), the measured
    ranges of the combining blocks (:data:`SEPARATOR_MARKS`, :data:`SEPARATOR_ANNOTATIONS`), and
    the enumerated ``EXTRA_KILLERS`` — Thai and Lao tone marks, nukta, the Khmer consonant
    shifters and their kin, which no combining-class rule picks out. What they share is
    orthographic: written after the syllable, like a virama, where the vowel signs that do not
    split are written inside it.

    Every killer stands outside the word: `⟨bow⟩C⟨eow⟩ killer ⟨bow⟩X⟨eow⟩`. One ccc-9 character
    dissents (:data:`NON_KILLERS`, U+0E3A THAI PHINTHU): measured over as a killer on its own
    script's consonants and under wherever no letter precedes it, so it is an ordinary mark.
    """
    return (unicodedata.combining(c) == 9 and c not in NON_KILLERS
            or c in EXTRA_KILLERS
            or bool(SEPARATOR_MARKS.fullmatch(c))
            or bool(SEPARATOR_ANNOTATIONS.fullmatch(c)))


def _stray_mark(c: str) -> bool:
    r"""A combining mark, asked at a position where nothing before it can be its base.

    The letter alternative in a pretokenizer regex is conventionally ``\p{L}\p{M}*`` — a letter
    and the marks that hang off it — not ``\p{L}+``. Read literally, that alternative cannot match
    a mark with no letter in front of it, so such a mark is left to the catch-all class along with
    the punctuation and symbols. This fires only where a mark's base is not a letter: after a
    symbol, a digit, punctuation, an ideograph, an emoji, or at the start of the text. Measured
    against the alternatives on the corpora, this distinction is the only one they support (marks
    are letters when they follow one; treating them as punctuation shatters every accented word).

    Only a BMP mark reaches this branch: an astral one is HARD and takes no word model at all
    (:func:`is_hard_cp`), and a separator is a killer.
    """
    if _syriac_vowel(c):
        return False                   # a baseless Syriac vowel is a word-forming letter instead
    return unicodedata.combining(c) != 0 and not is_killer(c)


def _syriac_vowel(c: str) -> bool:
    """A Syriac vowel point (or superscript alaph) — a mark that acts as a word-forming letter
    wherever no base can hold it, rather than as a stray mark or a killer-run rider: it takes the
    full word model riding a killer or standing baseless, and fuses into a following letter's
    word. A based vowel stays an ordinary in-word mark.
    """
    o = ord(c)
    return o == 0x0711 or 0x0730 <= o <= 0x073F


def _runs(norm: str, model) -> list[tuple[str, str]]:
    """The text split into maximal same-class runs, with terminal marks as unmarked separators.

    A killer does not close a word *after itself*. It stands outside the word: the preceding WORDY
    run closes before the mark and a following WORDY run opens after it. Thus ``C killer X`` is
    written ``⟨bow⟩C⟨eow⟩ killer ⟨bow⟩X⟨eow⟩``. This factorization explains word-final and
    standalone marks without ``killer⟨eow⟩`` pieces or a stacked-killer exception.

    ``_KILLER`` is deliberately a stream class rather than ``HARD``. The output is unmarked in both
    cases, but keeping the class distinct prevents a neighbouring punctuation or symbol run from
    inheriting the mark and losing its own boundary treatment.
    """
    if not norm:
        return []
    out, cur, cur_cls = [], norm[0], classify(norm[0])
    if cur_cls == WORDY and _stray_mark(norm[0]):
        cur_cls = _STRAY_MARK          # nothing in front of it, so no letter can be its base
    for ch in norm[1:]:
        c = classify(ch)
        # A combining mark riding a killer run opens a stray word like any other: an accent
        # after a Syriac dot is a killer in its own right and joins the run, and every other
        # rider measured one token under if made to ride.
        if cur_cls == _STRAY_MARK and c == WORDY and _stray_mark(ch):
            cur += ch                  # consecutive unattached marks are one regex-style run
        elif c == cur_cls:
            cur += ch
        elif c == WORDY and _stray_mark(ch) and cur_cls != WORDY:
            out.append((cur_cls, cur))
            cur, cur_cls = ch, _STRAY_MARK
        else:
            out.append((cur_cls, cur))
            cur, cur_cls = ch, c
    out.append((cur_cls, cur))

    # A HARD run is not homogeneous, so it is split where the character kind changes and the
    # predicates below then apply per sub-run (`文？` is one run by class, but `？` takes the same
    # border markers as in a run of its own). A variation selector never opens a sub-run: it rides
    # its base's sub-run, or a symbol like `⚖️` would sever at the selector and lose its ⟨eow⟩.
    split = []
    for cls, body in out:
        if cls != HARD or len(body) == 1:
            split.append((cls, body))
            continue
        cur = body[0]
        cur_kind = _hard_kind(cur)
        for ch in body[1:]:
            if _is_selector(ch) or _hard_kind(ch) == cur_kind:
                cur += ch
            else:
                split.append((cls, cur))
                cur = ch
                cur_kind = _hard_kind(ch)
        split.append((cls, cur))
    return split


def _ideographic_punct(ch: str) -> bool:
    """Punctuation of the CJK Symbols and Punctuation block, which takes no border marker.

    Measured over every P-category character of U+3001–U+303F. The block predicts this, not the
    category, the width, or sentence-terminal function (fullwidth `？！～`, halfwidth `｡｢｣･` and
    `・` U+30FB all take markers; `。` does not).
    """
    return 0x3001 <= ord(ch) <= 0x303F and unicodedata.category(ch).startswith("P")


def _hard_kind(ch: str) -> str:
    """Which pretoken alternative a character of a HARD run belongs to.

    A HARD run is a run of our own class, not a pretoken: the conventional pretokenizer regex
    alternates letters | numbers | catch-all, so a number and the ideograph beside it are
    different pretokens however our classifier grouped them, and each sub-run takes its own
    border markers. U+3007 is Nl, outside the measured Nd/No border population, and stays with
    its ideographs.
    """
    if _marks_like_punct(ch):
        return "punct"
    if _digit_border(ch):
        return "number"
    return "letter"


def _marks_like_punct(ch: str) -> bool:
    """Is this character one the border-marker branch can claim — punctuation, symbol or format?

    Ideographic punctuation is excluded, so it stays in the ideograph run it sits in and takes no
    markers. That is per border character rather than per run: `1。？ 1` and `1 ？。1` are exact
    because the marker sits on the `？` side, while `1？。 1` and `1 。？1` are one over if the run
    is judged as a whole.

    Astral characters are excluded too: an emoji takes no border marker, so it must not be the
    punct kind either — a format character in front of one would otherwise be glued into a single
    markerless sub-run and lose the ⟨bow⟩ it is entitled to.
    """
    ch = ESCAPED_MARKER_LITERALS.get(ch, ch)
    if ord(ch) >= 0x10000:
        return False
    cat = unicodedata.category(ch)
    return (cat[0] in ("P", "S") or cat in ("Cf", "Cn")) and not _ideographic_punct(ch)


def stream(text: str, model) -> str:
    """Text → the marked stream, in the internal glyph form ``pieces.json`` keys parse to.

    A WORDY run is bracketed ⟨bow⟩…⟨eow⟩ and case-normalized. A single space between two such runs
    is dropped — the ⟨eow⟩⟨bow⟩ seam is what encodes it. Every other space stays literal.
    Punctuation-like, digit, killer, and stray-mark runs receive their measured boundary markers.
    """
    return stream_norm(nfc(text, fold_quotes=model.fold_quotes), model,
                       raw_head_space=raw_head_space(text))


def raw_head_space(text: str) -> bool:
    """Is the message's leading space one the raw text supplies — the only one the frame absorbs?

    Anything else standing between the frame and the text was read by the oracle before the space
    was, and the oracle does not absorb across it — whether :func:`nfc` then strips that character
    or folds it into a space makes no difference to what the oracle saw. So a space a fold
    produced or exposed is not absorbed.
    """
    return text.startswith(" ")


def stream_norm(norm: str, model, *, raw_head_space: bool = True) -> str:
    """The marked stream over already-normalized text.

    This is :func:`stream` over text the caller has already folded. It is split out so a document
    is NFC-folded once and the caller can read the content-final newline run — which ``rstrip``
    below drops — off the same string it streams (see ``engine.frame_tail``).
    """
    # Protect literal occurrences of the codepoints used as internal markers. PUA input was removed
    # by NFC, so the private-use escape values cannot collide with text.
    norm = norm.translate(LITERAL_MARKER_ESCAPE_TABLE)

    # The frame's tail, for a family whose frame has one: `engine.tile` reads the run off the same
    # string before dropping it here. A "free" family is stripped on the raw text instead (see
    # `tile`), so there is nothing left to take off here and taking it would eat a folded NBSP.
    if model.frame_tail == "ladder":
        norm = norm.rstrip(model.frame_strip)
    # A single leading space is dropped: the frame ends in ⟨bow⟩ and that ⟨bow⟩ is the space
    # (' a' = 1). Two or more are a whitespace-run token and stay ('  a' = 2).
    # Where the frame does not end in a ⟨bow⟩ (v5), there is no space to stand in for: the leading
    # space is a character like any other, and ' a' costs one more than 'a' rather than the same.
    # A space that normalization exposed or manufactured is not the raw head and is not absorbed
    # either — the oracle read `[stripped or folded char][space][text]` (see
    # :func:`raw_head_space`).
    if model.frame_bow and raw_head_space and norm[:1] == " " and norm[1:2] != " ":
        norm = norm[1:]
    runs = _runs(norm, model)
    if not runs:
        # Content that normalizes away entirely still pays for the frame's ⟨bow⟩ — the same
        # ⟨bow⟩ the `out` list below writes when the first run supplies none; with nothing to
        # attach to it, it tiles as itself.
        return BOW_G if model.frame_bow else ""
    caps = model.allcaps_min
    n_runs = len(runs)

    def borders_space(i: int, side: int) -> bool:
        """Does this side of run ``i`` touch a space? Only a space counts — the marker represents an
        absorbed space, so nothing else can stand in for one.

        Message start counts (the frame ends in ⟨bow⟩, which is a space); message end does not (the
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
        # Run-kills-marker: a right-hand marker is written for the seam space only, never before
        # a run of two or more spaces.
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
                   first[0] in (WORDY, PUNCT, _STRAY_MARK)
                   or (first[0] == _KILLER and _borders(first[1][0]))
                   or _hard_bow(first[1])
                   or (first[0] in (DIGIT, HARD) and _digit_bow(first[1]))
                   or (first[0] == SPACE and first[1][:1] == " "))
    # Nothing to hand out where the frame ends in no ⟨bow⟩: a digit or an ideograph opening the
    # message pays for no marker, which is exactly where v5 counts one token under v4.7.
    out = [] if has_own_bow or not model.frame_bow else [" " if head_quote else BOW_G]
    for i, (cls, body) in enumerate(runs):
        if cls == WORDY:
            # A wordy span is flanked on both sides, except where a contraction apostrophe is
            # already its opening boundary (`_contraction_seam`) or an unattached mark run already
            # opened this word (the `_STRAY_MARK` branch below); in that second case the span's
            # head is the mark, so the case markers go with it (`mark_case(head_mark=...)`).
            fused = bool(i) and runs[i - 1][0] == _STRAY_MARK
            n = mark_case(body, caps, head_mark=fused)
            pre = ""
            while n[:1] in (SHIFT_G, CAPS_G):     # case markers precede ⟨bow⟩ in the file's spelling
                pre, n = pre + n[0], n[1:]
            bow = "" if (fused or _contraction_seam(runs, i)) else BOW_G
            out.append(pre + bow + n + EOW_G)
        elif cls == _STRAY_MARK:
            # A stray-mark pretoken is a word: ⟨bow⟩ on the left even when it is adjacent to a
            # symbol, digit or punctuation run, and ⟨eow⟩ on the right against everything except
            # a letter, which is the rest of the same word — the mark run writes no ⟨eow⟩ and the
            # letter writes no ⟨bow⟩ of its own: `⟨bow⟩M abc⟨eow⟩`, one word, exactly as
            # `_syriac_vowel` and U+0CF3 fuse. Measured over 22 marks on frames that cancel the
            # mark's own price: only the fused spelling's error is constant across right-hand
            # words. The run head does not byte-price — the mark reaches its own unit piece.
            letter_follows = i + 1 < n_runs and runs[i + 1][0] == WORDY
            out.append(BOW_G + body + ("" if letter_follows else EOW_G))
        elif cls == _KILLER:
            # A terminal separator run takes the same border markers punctuation does
            # (measured on Lao, Khmer, Myanmar, Thai and Bengali marks, with a non-terminal
            # script-mate as control). An astral separator writes neither (:func:`_borders`),
            # per border character as the digit branch is.
            out.append((BOW_G if borders_space(i, -1) and _borders(body[0]) else "") + body
                       + (EOW_G if borders_space(i, +1) and _borders(body[-1]) else ""))
        elif cls == PUNCT or _hard_bow(body) or _hard_eow(body):
            # A punct span is marked only on the side that borders whitespace: `a! b` gets `!⟨eow⟩`,
            # `a!b` gets a bare `!`. The marker is written unconditionally; the vocabulary decides
            # whether a piece swallows it.
            takes_bow = (borders_space(i, -1) and not _opens_word(runs, i)
                         and (cls == PUNCT or _hard_bow(body)))
            out.append((BOW_G if takes_bow else "") + body
                       + (EOW_G if borders_space(i, +1)
                          and (cls == PUNCT or _hard_eow(body)) else ""))
        elif _digit_run(body) and cls in (DIGIT, HARD):
            # A digit run takes the same border markers punctuation does, on both sides, decided
            # by the border character (`_digit_bow`, `_digit_eow`). Deliberately no lookback
            # across the space: a space run kills a border marker but not a seamless ⟨bow⟩, which
            # separates the two readings, and the lookback reads one over.
            out.append((BOW_G if _digit_bow(body) and borders_space(i, -1) else "") + body
                       + (EOW_G if _digit_eow(body) and borders_space(i, +1) else ""))
        else:
            out.append(body)                      # HARD letter scripts and whitespace: no markers
    return SEAM_RE.sub(r"\1" + EOW_G + r"\2" + BOW_G, "".join(out))
