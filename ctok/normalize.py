"""Text → the marked stream: everything that happens before the tiling.

    NFC + quote fold  ->  class split  ->  case marking  ->  boundary markers written in

``stream()`` is the output: a single string with word boundaries, case and absorbed spaces written
in as markers, which ``engine.py`` then tiles. Every rule here is either a designed rewrite of the
text or a measured fact about the oracle. No costs live in this module.
"""

from __future__ import annotations

import unicodedata

from .constants import (
    BOW_G, CAPS_G, CHARGING_MARK, DIGIT, EOW_G, FUNNY_SPACE, HARD, PUNCT, PUNCT_SYMS, QUOTE_FOLD,
    SEAM_RE, SHIFT_G, SPACE, STRIP_CONTROL, SURROGATE, SYMBOL_LETTERS, WORDY,
)


def nfc(text: str, *, fold_quotes: bool = True) -> str:
    """Normalize as Claude does before tokenizing: NFC, strip the zero-cost control characters,
    optionally fold the curly quotes, then fold space-separator variants (and NUL) to U+0020.

    ``fold_quotes`` is a per-family flag: v3 folds, v4.7 measured not to.
    """
    text = SURROGATE.sub("�", text)
    text = STRIP_CONTROL.sub("", unicodedata.normalize("NFC", text)).replace("\x00", " ")
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
    ch, case_markers = match.group(1), match.group(2)
    if CHARGING_MARK.fullmatch(ch):
        return match.group(0)
    return ch + EOW_G + case_markers + BOW_G


def _is_punct_text(body: str) -> bool:
    """Unicode punctuation, regardless of which internal class it lands in — the Devanagari danda,
    the ideographic full stop, the Arabic and Ethiopic stops are all category Po but classify HARD,
    and they take the same markers as ASCII punctuation."""
    return bool(body) and all(unicodedata.category(c).startswith("P") for c in body)


def _is_nd_run(body: str) -> bool:
    """A run of decimal digits (Nd), in either the DIGIT or the Nd-HARD class."""
    return all(unicodedata.category(c) == "Nd" for c in body)


def _nonascii_digits(body: str) -> bool:
    """The digit runs measured to take a boundary ⟨bow⟩ at any space border: every non-ASCII Nd run.
    Letter scripts measured not to; ASCII runs only strand one against a non-ASCII digit
    neighbour."""
    return _is_nd_run(body) and not body.isascii()


def _runs(norm: str) -> list[tuple[str, str]]:
    """The text split into maximal same-class runs."""
    if not norm:
        return []
    out, cur, cur_cls = [], norm[0], classify(norm[0])
    for ch in norm[1:]:
        c = classify(ch)
        if c == cur_cls:
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
    norm = nfc(text, fold_quotes=model.fold_quotes).rstrip("\n")
    # A single leading space is dropped: the frame ends in ⟨bow⟩ and that ⟨bow⟩ IS the space
    # (' a' = 1). Two or more are a whitespace-run token and stay ('  a' = 2).
    if norm[:1] == " " and norm[1:2] != " ":
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
            return True
        if j >= n_runs:
            return False
        if runs[j][0] != SPACE:
            return False
        adjacent = runs[j][1][-1:] if side < 0 else runs[j][1][:1]
        return adjacent == " "

    # The frame ends in ⟨bow⟩, always. A wordy or punct first run writes its own, as does a leading
    # non-ASCII digit run (it borders a space at the message edge); a leading whitespace run absorbs
    # it only if it starts with a real space, since a TAB or NEWLINE cannot. Anything else supplies
    # none, so the frame's ⟨bow⟩ is written here and tiles as itself.
    first = runs[0]
    has_own_bow = (first[0] in (WORDY, PUNCT) or _is_punct_text(first[1])
                   or (first[0] in (DIGIT, HARD) and _nonascii_digits(first[1]))
                   or (first[0] == SPACE and first[1][:1] == " "))
    out = [] if has_own_bow else [BOW_G]
    for i, (cls, body) in enumerate(runs):
        if cls == WORDY:
            # A wordy span is flanked on both sides, always.
            n = mark_case(body, caps)
            pre = ""
            while n[:1] in (SHIFT_G, CAPS_G):     # case markers precede ⟨bow⟩ in the file's spelling
                pre, n = pre + n[0], n[1:]
            out.append(pre + BOW_G + n + EOW_G)
        elif cls == PUNCT or _is_punct_text(body):
            # A punct span is marked only on the side that borders whitespace: `a! b` gets `!⟨eow⟩`,
            # `a!b` gets a bare `!`. The marker is written unconditionally; the vocabulary decides
            # whether a piece swallows it.
            out.append((BOW_G if borders_space(i, -1) else "") + body
                       + (EOW_G if borders_space(i, +1) else ""))
        elif _is_nd_run(body) and cls in (DIGIT, HARD):
            # A digit run takes a leading ⟨bow⟩ when it borders a space — the same rule punct has.
            # The population is measured: every non-ASCII Nd run at any space border, plus an ASCII
            # run only against a non-ASCII digit neighbour across the space. No ⟨eow⟩ is ever
            # written, since the message end is not a space.
            takes_bow = _nonascii_digits(body) or (
                i >= 2 and _nonascii_digits(runs[i - 2][1]) and runs[i - 2][0] in (DIGIT, HARD))
            out.append((BOW_G if takes_bow and borders_space(i, -1) else "") + body)
        else:
            out.append(body)                      # HARD letter scripts and whitespace: no markers
    return SEAM_RE.sub(_seam_sub, "".join(out))
