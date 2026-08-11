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
    EXTRA_KILLERS, FUNNY_SPACE,
    NON_KILLERS,
    HARD, PUNCT, PUNCT_SYMS, QUOTE_FOLD, SEAM_RE, SEPARATOR_ANNOTATIONS,
    SEPARATOR_MARKS, SHIFT_G, SPACE,
    STRIP_CONTROL, STRIP_PRIVATE,
    SURROGATE, SYMBOL_LETTERS, VARIATION_SELECTORS, WORDY,
)

_KILLER = "killer"
_STRAY_MARK = "stray_mark"


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
        # Quranic ANNOTATION signs — ayah ends, rub-el-hizb, the zeros, sajdah, the stop marks.
        # Two contiguous ranges, and each already contains members Unicode types as Cf or So which
        # were never in the letter class; the ones that leak through are the Mn members, because
        # `classify` admits category M. Measured 2026-08-08 in `ف_ى`, delta against the unmarked
        # baseline: U+06D6–06DC read +2, U+06DD–06E0 read +4, U+06E1–06E8 read +2, U+06E9–06EC
        # read +4, U+06ED reads +2 — so the boundaries are pinned on both sides of both ranges.
        # +4 is the unattached-mark spelling: its own ⟨bow⟩, the mark at the byte floor, and the
        # following letters restarting a word. Combining class does not predict the split (06DB at
        # ccc 230 reads +2 and 06DF at ccc 230 reads +4; 06E3 at ccc 220 reads +2 and 06EA at
        # ccc 220 reads +4), and neither does byte length. These are annotation, not pronunciation.
        or 0x06DD <= o <= 0x06E0      # ۝ ۞ and the two small high zeros
        or 0x06E9 <= o <= 0x06EC      # ۩ and the empty-centre stops
    )


@cache
def classify(c: str) -> str:
    """The stream class of one codepoint, derived from Unicode data and measured tables."""
    if is_killer(c):
        return _KILLER
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
        # KANNADA SIGN COMBINING ANUSVARA ABOVE RIGHT, assigned in Unicode 15.0. Our tables are
        # 14.0, so `unicodedata` reports Cn and the character fell through to HARD — no markers,
        # no word model. The oracle knows it as the spacing mark it is (Mc, ccc 0), and every
        # cached row prices as plain word material: word-forming when baseless (`◌ೳ` = 14/18,
        # `x◌ೳ◌ೳx` = 24, `文ೳ` = 17, each one to three tokens more than the HARD reading pays),
        # in-word after a letter (`aೳa` `aೳ` `ꝛೳ`), and FUSED into a following letter's word
        # (`ೳꝛ` = 18 on v4.7, one less than a severed spelling). 27 cached rows plus eight bought
        # in-script predictions (`x ೞೳ x` `ೞೳೞ` `ೞೳ` `x ೞೳ 5` `ೳೳ` `ೳೳz`), all exact in both
        # families. Its Mc-ness never reaches `_stray_mark` (ccc 0), so WORDY alone is the fix.
        return WORDY
    if cat[0] in ("L", "M") and not is_hard_cp(o):
        # Brahmic scripts are subsumed into WORDY: they tile over the same marked-fragment
        # vocabulary plus the per-codepoint byte floor as any other letter script.
        return WORDY
    return HARD


def mark_case(span: str, allcaps_min: int | None = 4, *, head_mark: bool = False) -> str:
    """Cased span → the marked form the tiler consumes.

    A case marker fires only on a WHOLE span: a pure all-caps span of length >= ``allcaps_min``
    becomes ⟨caps⟩ + lowercase, a pure title-case span becomes ⟨shift⟩ + lowercase. Everything
    else — internal, final or mixed capitals, and short all-caps runs — stays literal, so
    ``GaN``/``WiFi``/``QQ`` keep their bytes. ``allcaps_min=None`` disables ⟨caps⟩ (v4.7).

    **A caseless letter anywhere in the span blocks ⟨caps⟩ — and only ⟨caps⟩.** ``str.isupper``
    is True for ``ヲBUTTヲ`` — katakana has no case, so "all cased letters are upper" holds — and
    the ⟨caps⟩ the old test wrote there is one to three tokens cheaper than the literal spelling
    the oracle uses. Measured 2026-08-10 on `.ヲBUTTヲ.` = 19 and its six grid mates, and on the
    corpus rows that led there (`அறிவியலNATIONAL`, `ロデオFUCK`, `BODYの`, `परिएाजनाÓ` — 36 texts
    across Tamil, Japanese and Hindi documents); confirmed against bought predictions in both
    families (`x ロデオFUCK x` `x BODYの x` `x アBUTT x` `x BUTTア x` `x அறிவியலNATIONAL x`
    literal, `x BUTT x` exact as control). ⟨shift⟩ is NOT blocked, and extending the block to it
    was tried and caught by the full-cache re-scan before it shipped: a title-case head with a
    caseless tail keeps its marker — `.Collectionヲ.` `.Ghostヲ.` and eighteen more `bow`-template
    witnesses read ±1 both ways as literal, and the Assamese corpus spans `Gৰ` and `Gলৈকে`
    (one Latin capital opening a Bengali word) read −2.

    **A caseless MARK blocks it too**, and reading the block as per-LETTER was the last
    under-counting text in the corpus. A wordy span holds letters and marks and nothing else, so
    "all its cased letters are upper" is as vacuously true of `းUNDPA` as it is of `ヲBUTTヲ`: the
    span is a Myanmar sign glued to Latin capitals, and ⟨caps⟩ + a lowered body prices it one
    token below the literal spelling the oracle uses. Measured 2026-08-11 over every text in the
    measurement store that holds an uppercase letter and a mark (v3, 35,796 texts). Five spans in
    the whole store put a caseless mark inside an all-caps run, three of them discriminate, and
    the widened block is exact on all three — in BOTH directions, which is what makes it a
    spelling rather than a fitted constant:

        ၵၢၼ်ဢုပ်ႇဢူဝ်းUNDPA   ⟨caps⟩ reads 1 UNDER    literal exact
        ပႃႊတီႊသိူဝ်ၽိူၵ်ႇSNDP  ⟨caps⟩ reads 1 OVER     literal exact
        တႆးလွတ်ႈလႅဝ်းKIA       ⟨caps⟩ reads 1 OVER     literal exact
        ၸုမ်းRCSS · ၸုမ်းNGO   both spellings agree — coincidence cells, no evidence either way

    Nothing else in either family moves: 5 texts move, all 5 to exact, 35,791 are untouched.

    **The block is position-free, and that half was bought rather than assumed.** All five corpus
    spans put the mark at the head, so they cannot tell "a mark anywhere" from "a mark at the
    head". A grid of 41 probes per family settles it on the membership reading — a span takes
    ⟨caps⟩ iff it costs exactly one more than its own lowered body — over five marks of combining
    class 0 from four scripts, each at the head, in the interior and at the tail of `BUTT`, the
    body the caseless-LETTER block was measured on:

        x BUTT x  / x butt x        5 / 4   step 1   <- control: ⟨caps⟩ fires
        x းBUTT x / x းbutt x       7 / 5   step 2   literal
        x BUးTT x / x buးtt x       7 / 5   step 2   literal
        x BUTTး x / x buttး x       7 / 4   step 3   literal

    U+1038, U+1036, U+0E31, U+0901 and U+0981 read the same three steps, 15 cells with not one
    dissenting: **the position of the mark does not matter and the ⟨caps⟩ spelling is refused
    everywhere**, exactly as the caseless letter is at the head (`அறிவியலNATIONAL`) and at the tail
    (`x BUTTア x`, `BODYの`). The corpus spans read as membership too: `x းUNDPA x` = 7 against
    `x းundpa x` = 5, and `x ႇSNDP x` = `x ႇsndp x` = 8 — a ⟨caps⟩ spelling can never cost the
    same as its lowered body, let alone two more. The pre-block rule is wrong on 18 of the 41 v3
    rows and the shipped one on none; v4.7 has no ⟨caps⟩ and reads 0 wrong either way, which is
    the null control.

    ⟨shift⟩ is untouched: the block suppresses ⟨caps⟩ and falls through, and returning the span
    literal instead ALSO drops ⟨shift⟩ and reads two Indic rows carrying one Latin capital
    (`Vಗಳನ್ನು`, `4G`) one under.

    **A marker asserts a LOWERED body, so a character that cannot supply one blocks it** (§27,
    measured 2026-08-12). ``ℳ`` is `isupper()` and ``'ℳ'.lower()`` is ``'ℳ'`` — there is no
    lowercase letterlike M — so ⟨shift⟩ + ``span.lower()`` writes a marker in front of a body it
    did not change, and the oracle spends one token less. That is the same sentence the İ head
    clause below already rests on, one Unicode property wider, so "caseless" becomes "cannot
    supply a lowered form": every titlecase and caseless character the narrower predicate held is
    still held, and the uppercase letters with no lowercase mapping join them. 19 BMP heads
    (``ϒ ℋ ℌ ℍ ℐ ℒ ℕ ℙ ℚ ℛ ℜ ℝ ℤ ℨ ℬ ℭ ℰ ℱ ℳ``) read `x {C}iji x` = `x {c}iji x` with **step 0** in
    both families where we wrote a ⟨shift⟩, against 21 heads that DO lower (Latin, Cyrillic,
    Cherokee, ``Æ Ø Đ Ŋ``) at step +1 and exact; ⟨caps⟩ carries the same defect on v3
    (`x ℳℳℳℳ x` = `x ℒℒℒℒ x` = 12 against our 13) and the widened predicate closes it. Astral
    heads (``𝕊``, ``𝐀``) were already exact — §17's astral rule writes no marker there — and stay
    so. Every reachable cached text moves to exact and none is broken: 28 of 68 on v3, 81 of 136
    on v4.7.

    **İ is transparent to the title-case test and literal in its lowered body** (§12.2, closed
    2026-08-10). `Hnovunİ` IS a title-case span to the oracle: it takes ⟨shift⟩, and the İ — which
    has no clean lowercase byte form (it lowers to i + U+0307) — simply stays İ. That single
    reading closes all thirteen §12.2 rows and was confirmed on their lowercase counterparts:
    `x Hnİ x` = 14 = 1 + `x hnİ x`, `x Hnovunİİ x` = 15 = 1 + `x hnovunİİ x`, `x Hüseynovunİ x` =
    18 = 1 + `x hüseynovunİ x`, and the never-measured shapes `x Hnİvo x` = 14 and `x Hİk x` = 13
    step off their lowercase rows by exactly the ⟨shift⟩, in both families. The old reading — a
    rule over a tile five tiles before the İ — was the literal tiling's coincidences: `HHnovunİ`,
    `HNovunİ` and `hnovunİ` are not title-case, so the piece never budged there. İ at the span
    HEAD still blocks (⟨shift⟩ asserts a lowered first letter, which İ cannot supply), and ẞ
    measured literal in every position and stays an unconditional block.

    **``head_mark`` — the span is the tail of a word an unattached mark run opened, so its head is
    that mark and NEITHER marker can assert what it asserts.** The span is spelled literally.
    Measured 2026-08-10 over 57 rows per family, on three marks (U+0363, U+05B1, U+2DE0):
    ⟨shift⟩ kept reads +1 on `x ͣThe x` = 13/18, `x ͣJohn x` = 14/19, `x ͣHello x` = 14/18,
    `x ͣXyz x`, `ͣThe x`, `!ͣThe x`, `x ͣThe`, `x ͣͣThe x`; ⟨caps⟩ kept reads −2 on
    `x ͣHELLO x` = 17, −4 on `x ͣЖЖЖЖ x` = 21 and −5 on `x ͣЖЖЖЖЖ x` = 23 (v3, where ⟨caps⟩
    exists at all). Literal is exact on all 57 in both families, including the rows where the
    spellings coincide and settle nothing — `x ͣABCD x` `x ͣPARIS x` `x ͣabcd x` `x ͣАбв x` —
    and the unfused controls `x The x` `x Abc x` are untouched.
    """
    if head_mark:
        return span
    if "ẞ" in span:
        return span
    if "İ" in span:
        tail = span[1:]
        if span[:1].isupper() and span[:1] != "İ" and \
                not any(c.isupper() for c in tail if c != "İ"):
            return SHIFT_G + span[0].lower() + "".join(c if c == "İ" else c.lower()
                                                       for c in tail)
        return span
    unlowerable = any(unicodedata.category(c)[0] in ("L", "M") and not c.islower()
                      and (not c.isupper() or c.lower() == c) for c in span)
    if allcaps_min is not None and span.isupper() and len(span) >= allcaps_min \
            and not unlowerable:
        # Python's str.lower() applies Unicode's Final_Sigma context rule — 'ΣΚΙΕΣ'.lower() is
        # 'σκιες' — and the oracle's ⟨caps⟩ body does not: it lowers Σ to σ everywhere. Measured
        # 2026-08-10 on the two Greek documents the residue scan left: `x ΣΚΙΕΣ x` = 16 is the
        # σκιεσ spelling (σκιες reads 14, literal 21), `x ΕΠΙΤΡΟΠΗΣ x` = 17 = `x επιτροπησ x` + 1,
        # `x ΔΙΑΦΘΟΡΑΣ x` and `x ΣΣΣΣ x` step the same way, and every caps word WITHOUT a final
        # sigma — `x ΣΚΙΕ x` `x ΑΓΟΡΑ x` `x ΕΠΙΤΡΟΠΗ x` `x ΜΟΣΧΑ x` `x ΤΕΣΤ x` — is exact under
        # both spellings. An input span that is isupper() contains no ς of its own, so the
        # replace only ever touches what lower() just produced.
        return CAPS_G + span.lower().replace("ς", "σ")
    if span[:1].lower() == span[:1]:
        return span
    if span[:1].isupper() and not any(c.isupper() for c in span[1:]):
        return SHIFT_G + span.lower()
    return span


# ---- the marked stream --------------------------------------------------------------------------


def _is_borderable_text(body: str) -> bool:
    """Does this HARD body take the punctuation border markers — every character punctuation,
    symbol or format, judged PER CHARACTER by :func:`_marks_like_punct`?

    This is deliberately per-character: the earlier homogeneous run tests let a MIXED body — a
    format character against a BMP symbol — fall through and lose its markers. Measured
    2026-08-10 on the Sorani corpus row's `🎓 ‎⏰` (LRM + alarm clock, one under while glued
    markerless) and the grid bought from it: `1 ‎⏰ 1` `1 ⏰‎ 1` `1 €‎ 1` `1 ‎€ 1` `x ‎⏰ 5`.
    Ideographic punctuation and astral characters exclude their runs, exactly as they always
    excluded themselves; a trailing variation selector rides its base.

    A body of ONLY selectors is borderable too — a lone selector is still the catch-all
    alternative's material, whatever it failed to ride. Measured 2026-08-10, the row an in-situ
    window deletion manufactured and both families then confirmed on a bought grid: `5 ️ 5` reads
    two under with no markers, `a️ 5` `1️ 5` `!️ 5` `Э️ 5` `x ️ 5` `️ 5` `x ️️ 5` and `5 ️`
    one, while `a️ z` `x ️ x` (the seam cancels), `a️5` (no space), `a️` (message end) and the
    space-run rows `x ️  5` `a️  5` are exact. The run is not a symbol, but it takes the markers
    all the same."""
    core = [c for c in body if not VARIATION_SELECTORS[0] <= ord(c) <= VARIATION_SELECTORS[1]]
    return bool(body) and all(_marks_like_punct(c) for c in core)


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


def _takes_right_border(cls: str, body: str) -> bool:
    """Does this run write a boundary marker of its own on its RIGHT edge?

    The three populations that do: punctuation, symbols and format characters
    (:func:`_marks_like_punct`'s three predicates and the ``PUNCT`` class), a terminal separator
    run, and a digit run whose LAST character is a border digit (:func:`_digit_eow`). They are the
    runs the pretokenizer's catch-all alternative owns rather than its letter or number
    alternative, and they behave alike everywhere in this module.

    An unattached mark run is NOT one of them. It writes an ⟨eow⟩ of its own, but it is a word
    that writes it (see the ``_STRAY_MARK`` branch of :func:`stream_norm`), and a word lets the
    contraction seam through: `x ͣ's x` `x ֿ's x` `x ͅ's x` `x ͣ're x` `x a̱ͅ's x` all read one
    OVER when it is counted here, in both families, against `x ͣ'zz x` and `x ͣ'v x` exact.
    """
    return (cls == PUNCT
            or (cls == _KILLER and _borders(body[-1]))
            or _is_borderable_text(body)
            or (cls in (DIGIT, HARD) and _digit_run(body) and _digit_eow(body)))


def _contraction_seam(runs: list[tuple[str, str]], i: int) -> bool:
    """Does a lone apostrophe immediately left of wordy run ``i`` supply that word's ⟨bow⟩?

    `it's` is one word boundary, not two: the apostrophe IS the boundary, exactly as the seam space
    is. So the word after it is written bare — `x'll` = ⟨bow⟩x⟨eow⟩ + ' + ll⟨eow⟩ = 3, where paying
    for the boundary reads 4. It is the vocabulary that then decides whether a piece swallows the
    pair (`'s⟨eow⟩` does, at 1; `'ll⟨eow⟩` in this family does not, at 2).

    Three conditions, all measured. The suffix must be in ``CONTRACTION_SUFFIXES``, whole-word and
    lowercase. The apostrophe must be a punct run of its OWN: one that follows other punctuation
    belongs to that run and reaches the word with nothing — `}'s` = 3, `.'s.` = 4, `.'ve.` = 5,
    `a)'s b` = 5, `.'ll.` = 5 are each one more than the seam allows.

    And the run on the far side of that apostrophe must not write a right-hand border marker of
    its own (:func:`_takes_right_border`). That third condition began as "not punctuation", which
    the second one already covers, and the population is wider: it is every run the catch-all
    pretoken alternative owns. Measured 2026-08-10, one token under without it, in both families:

        x a̱'s x   x a्'s x   x a่'s x   x a݀'s x       a terminal separator run
        x ̱'re x   x .̱'re x   x 5̱'re x                 a separator run with no letter before it
        x ½'s x   x ٥'s x   x a②'s x                  a border-digit run
        x a←'s x   x a​'s x                            a symbol run, a format run (U+200B)

    uniformly over all seven v3 suffixes and all four v4.7 ones (`x a̱'ve x` = 19 on v4.7 reads two
    under, since `'ve⟨eow⟩` is a piece there and the split spelling pays three tokens for it).
    Controls exact: `x a's x` `x 5's x` `x 文's x` `x 한's x` `x あ's x` `x Ⅷ's x` `x 55's x`
    `x aͅ's x` `x aͣ's x` (marks that stay inside the word), `x ٥5's x` (a digit run ENDING in
    ASCII writes no ⟨eow⟩, the same last-character test `_digit_eow` has, against `x 5٥'s x`
    which does and blocks), `x a̱ 're x` and `x a̱  're x` (a space run between, which restores
    it), `x a̱''re x` (not a lone apostrophe), and `x a̱'v x` `x a̱'e x` `x a̱'vez x` `x a̱'zz x`
    (suffixes outside the contraction set, which never used the seam).

    A letter, an ASCII digit, an ideograph, a space run or the message edge on the left all let it
    through: `f's` = 2, `1'll` = 4, `a  'll b` = 5.
    """
    if runs[i][1] not in CONTRACTION_SUFFIXES or i == 0:
        return False
    prev_cls, prev_body = runs[i - 1]
    # A punct run is maximal, so a run that IS the apostrophe cannot have punctuation to its left.
    if prev_cls != PUNCT or prev_body != "'":
        return False
    return i < 2 or not _takes_right_border(*runs[i - 2])


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


def _borders(ch: str) -> bool:
    """Is this character one that can carry a border marker at all?

    An ASTRAL character cannot, and that is the same exclusion :func:`_marks_like_punct` and
    :func:`_is_symbol_text` already carry for punctuation, symbols and emoji — stated once here
    so the digit and terminal-separator branches stop being the two places it was missing.

    Measured 2026-08-10, and the sweep is exhaustive over both populations rather than sampled.
    **All 30 astral terminal separators** — Kharoshthi, Brahmi ×3, Kaithi, Chakma ×2, Sharada,
    Khojki, Khudawadi, Grantha, Newa, Tirhuta, Siddham, Modi, Takri, Ahom, Dogra, Dives Akuru ×2,
    Nandinagari, Zanabazar ×2, Soyombo, Bhaiksuki, Masaram Gondi ×2, Gunjala Gondi, Kawi ×2 —
    read `+1 +1 0 +2 0` on `x aK 5` / `5 Ka x` / `x aK x` / `5 K 5` / `x aKb x` with the markers
    written: two spurious markers, no character and no family dissenting. **72 astral border
    digits, one or two from each of the 56 astral number blocks**, read `+1 +2 0 +2` on
    `x D 5` / `文 D 文` / `x D x` / `5 D 5`. Both populations are exact with no marker written.

    The BMP controls are what make this an astral rule rather than a change to killers or digits:
    `่` `်` `្` `्` `்` `́` `ٰ` `݀` read 0 in all thirteen killer frames in both families, and
    every row of :func:`_digit_eow`'s grid is unmoved.

    It is per BORDER CHARACTER, as everywhere else in this module — a MIXED run keeps the marker
    on the side whose own character is BMP. `x a𑄴่ 5` (NFC orders the astral first) and
    `x 𑄶５ 5` are exact WITH the ⟨eow⟩, while `5 𑄴่a x` and `x ５𑄶 5` are one over with the
    marker written on the astral side.
    """
    return ord(ch) < 0x10000


def _digit_border(ch: str) -> bool:
    """Is this the kind of digit for which the border markers are written — a non-ASCII decimal
    digit, or any of the Unicode *other* numbers?

    ASCII digits take no border marker of their own: `1 1` = 4 and `文 5 文`, `文 5 5`, `x 5年 x`
    are all exact unmarked. Everything else does, in every script tried — `٥ 取` `۹ 取` `๙ 取`
    `१ 取` `５ 取` `½` — so the split is ASCII vs not, not script by script.

    Astral digits are the far end of the same range and take none either (:func:`_borders`).
    """
    cat = unicodedata.category(ch)
    return (cat == "No" or (cat == "Nd" and not ch.isascii())) and _borders(ch)


def _digit_run(body: str) -> bool:
    """A run the digit-border branch owns: all decimal digits, or all *other* numbers."""
    return _is_nd_run(body) or _is_no_run(body)


def _digit_bow(body: str) -> bool:
    """Does a digit run write ⟨bow⟩ where it borders a space on the left? Per BORDER CHARACTER,
    exactly as the punctuation marker is (see :func:`_marks_like_punct`) — the run's FIRST
    character decides, not the run as a whole.

    Measured 2026-08-09 on mixed ASCII/Arabic-Indic runs, which are the only runs where the two
    readings differ (a HARD digit sub-run is all non-ASCII by construction, since ASCII digits are
    their own class). `文 5٥` = 17 and `٥5 5` = 17 and `文 ٥5 5` = 20 each read one MORE under a
    whole-run test, which wrote a ⟨bow⟩ on a run that opens with `5`; `文 ٥5` = 18 and `文 ٥5 文`
    = 20 keep it, because those open with `٥`.
    """
    return _digit_run(body) and _digit_border(body[0])


def _digit_eow(body: str) -> bool:
    """Does a digit run write ⟨eow⟩ where it borders a single space on the right? The run's LAST
    character decides, the mirror of :func:`_digit_bow`.

    This is the half the digit branch never had, and the reason it looked complete is that the
    seam hides it: an ⟨eow⟩ before `space + ⟨bow⟩` is deleted along with the space, so every probe
    whose right neighbour is a word, a punctuation run or another marker-taking digit run reads
    the same with it and without it (`x ５ x` `８ ９` `١ ٢` `a ½ b` `文 ５ x` all exact either
    way). It shows only before a run that writes no ⟨bow⟩ of its own — a CJK or Hangul letter, or
    ideographic punctuation:

        ８ 取 = 16   １ 竹 = 16   ９ 。 = 16   ５ 取 = 16   ٥ 取 = 17   ۹ 取 = 17
        ๙ 取 = 17   १ 取 = 15   文 ½ 文 = 19   한 ５ 한 = 19   文 ٥ 文 = 20   取 １２ 取 = 19

    each one token more than an ⟨eow⟩-less spelling charges. Controls: `件 ５` and `文 ٥` = exact
    (the message end is not a space), `８  取` and `文 ５  文` = exact (a space RUN kills the
    marker, the rule punctuation has), `文 ٥\\t文` and `文 ٥\\n文` = exact (only a space counts),
    `9 取` and `文 5 文` = exact (ASCII digits are not border digits), and `文 ٥5 文` = 20 and
    `文 ٥5 5` = 20 exact, which is what fixes the last character rather than the first as the
    test — a `٥5` run ending in ASCII writes no ⟨eow⟩.
    """
    return _digit_run(body) and _digit_border(body[-1])


def is_killer(c: str) -> bool:
    """A mark that terminates the orthographic syllable, and so separates word runs.

    Three populations, and the split between them is the honest part. **Viramas** — the Brahmic sign
    that suppresses a consonant's inherent vowel so it can join the next one — are all canonical
    combining class 9, so those 65 characters are DEFINED, not listed. The **combining accents** of
    U+0300 are a measured RANGE (:data:`SEPARATOR_MARKS`), both of whose ends are pinned by marks
    inside the same block that do not join, and the accent, tone and annotation marks of the other
    combining blocks are measured RANGES too (:data:`SEPARATOR_ANNOTATIONS`), most of them pinned
    on both sides by a vowel point or a combining letter that stays inside the word. Everything
    else is ENUMERATED in ``EXTRA_KILLERS``: Thai and Lao tone marks, Myanmar dot-below, nukta, the
    Khmer consonant shifters, Tai Tham's tone signs. Those are not a combining class and no numeric
    rule picks them out — a Lao tone mark (ccc 122) splits and the Lao vowel sign beside it
    (ccc 118) does not. What they share is orthographic: a Thai tone mark is written after the
    whole syllable exactly as a virama is written after the whole cluster, and the vowel signs that
    do not split are written inside it.

    Every killer stands OUTSIDE the word: `⟨bow⟩C⟨eow⟩ killer ⟨bow⟩X⟨eow⟩`. The U+0300 block used
    to be excepted from that — it closed the word AFTER the mark — on the strength of decomposed
    Latin corpus slices. Those slices do not distinguish the two spellings: they differ only on a
    host whose whole word is one token, and only against a right neighbour that opens no word.

    **One ccc-9 character dissents, and being DEFINED rather than measured is how it hid**
    (:data:`NON_KILLERS`). Asked ours-against-oracle on a consonant of its own script, all 121
    characters this predicate claims reproduce except U+0E3A THAI PHINTHU:

    ```
                        x HMH x   HMH    x HM x   x HMHH x   x HHMH x
    U+0E3A  ก           +2        +2     +1       +1         +1
    U+0E48  ก mai ek     0         0      0        0          0     script-mate control
    U+094D  क virama     0         0      0        0          0     and 8 more, all zero
    ```

    It reads +2 in both families because the split is not there to be made, and the same
    misreading is an UNDER-count wherever the phinthu has no letter in front of it and our
    `_KILLER` branch writes no boundary at all: `!ฺ` = 12 / 16 against our 10 / 14, `1ฺ` `[ฺ]`
    `[文ฺ]` `◌ฺ` alike, which is 38 of the 151 texts that still under-counted. As an ordinary mark
    it is a word's own material after a letter (`xฺ` `xฺx` `กฺก` exact) and a stray-mark run after
    anything else, which is what those rows measure.
    """
    return (unicodedata.combining(c) == 9 and c not in NON_KILLERS
            or c in EXTRA_KILLERS
            or bool(SEPARATOR_MARKS.fullmatch(c))
            or bool(SEPARATOR_ANNOTATIONS.fullmatch(c)))


def _stray_mark(c: str) -> bool:
    r"""A combining mark, asked at a position where nothing before it can be its base.

    The letter alternative in a pretokenizer regex is conventionally ``\p{L}\p{M}*`` — a letter and
    the marks that hang off it — not ``\p{L}+``. Read literally, that alternative cannot match a
    mark with no letter in front of it, so such a mark is left to the catch-all class
    ``[^\s\p{L}\p{N}]+`` along with the punctuation and symbols. That is the whole rule, and it
    fires only where a mark's base is not a letter: after a symbol, a digit, punctuation, an
    ideograph, an emoji, or at the very start of the text.

    Measured against the alternatives on the corpora (v4.7 / v3 UDHR mean, 2026-08-07):

        this rule                                       0.0643% / 0.1094%   362 / 314 exact
        a mark opens a word of its own (what preceded)  0.0644% / 0.1096%   361 / 313
        a mark is an unmarked separator                 0.1403% / 0.1932%   361 / 315
        a mark is NOT in the letter class at all        1.5416% / 1.5842%   329 / 293

    The last row is the same idea with ``\p{M}`` simply dropped rather than tied to a preceding
    letter, and it is off by a factor of 24: marks manifestly ARE letters when they follow one, and
    treating them as punctuation shatters every accented word. The distinction this predicate draws
    is the only one the corpora support.

    Only a BMP mark reaches this branch: an astral one is HARD and takes no word model at all
    (:func:`is_hard_cp`), and a separator is a killer. Of the 2,435 cached `<mark>ꝛ` rows exactly
    243 are stray-mark runs, every one of them BMP; the five marks §14.4 cited against dropping the
    letter's ⟨bow⟩ — U+1BE6, U+2CEF, U+302A, U+3099, U+A8E0 — became ``SEPARATOR_ANNOTATIONS`` in
    §15's fifth pass and have not been in this branch since.
    """
    if _syriac_vowel(c):
        return False                   # a baseless Syriac vowel is a word-forming letter instead
    return unicodedata.combining(c) != 0 and not is_killer(c)


def _syriac_vowel(c: str) -> bool:
    """A Syriac vowel point (or superscript alaph) — a mark that acts as a word-forming LETTER
    wherever no base can hold it, rather than as a stray mark or a killer-run rider.

    Measured 2026-08-09 on 160 cached rows plus eight bought probes, every one reconciled by the
    letter reading and none by any marker rule tried before it:

      * riding a killer: `ܒ݂ܶ` = 21 is `⟨bow⟩ܒ⟨eow⟩ ݂ ⟨bow⟩ܶ⟨eow⟩` (10 content tokens — a word
        model around the vowel, ⟨eow⟩ and all, at MESSAGE END, which no stray-mark spelling
        writes); `x ܒ݂ܶ x` = 23 and `ܒ݂ܶ 5` = 23 and `ܒ݂ܶ  x` = 23 the same against space
        borders (run-kills-marker does not kill a word's ⟨eow⟩);
      * fusing with a following letter, exactly as a word-initial letter does: `ܒ݂ܶܒ` = 23 is
        `݂ ⟨bow⟩ܶܒ⟨eow⟩` and `x ܒ݂ܶx` = 22 is `݂ ⟨bow⟩ܶx⟨eow⟩` — one token less than a
        marked vowel standing alone, because `x⟨eow⟩` is a piece;
      * stray contexts, same law: `ܑ` = 15, `!ܑ` = 16, `1ܑ` = 17, `z ◌ܑ` = 19 (a full
        ⟨bow⟩…⟨eow⟩ word), and `x◌ܑ◌ܑx` = 24 — the vowel before `◌` closes its word, the one
        before `x` fuses into `⟨bow⟩ܑx⟨eow⟩`.

    Controls exact throughout: `x ܒܶ x` = 19 (a based vowel stays an ordinary in-word mark),
    `x ܒ݂ x` = 20 and `ܒ݂ ܒ` = 22 (a bare killer run is unchanged), `ܒܶ ܒ` = 21.
    """
    o = ord(c)
    return o == 0x0711 or 0x0730 <= o <= 0x073F


def _runs(norm: str, model) -> list[tuple[str, str]]:
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
    out, cur, cur_cls = [], norm[0], classify(norm[0])
    if cur_cls == WORDY and _stray_mark(norm[0]):
        cur_cls = _STRAY_MARK          # nothing in front of it, so no letter can be its base
    for ch in norm[1:]:
        c = classify(ch)
        # A Syriac-dot absorb clause stood here: a non-vowel combining mark after U+0740–U+074A
        # rode the killer run instead of opening a stray word. It predated §14 — its one motivating
        # row, `x ݂́ܒ x`, has the ACUTE as the rider, and the acute has been a killer in its own
        # right since the accent sweep, joining the run with no clause needed. For every rider the
        # clause still touched it was one token UNDER: the stray-word spelling is exact on
        # `x ݀ͅ x` = 16/20 and on ten bought predictions in both families — `x ݀ͣ x` `x ٰ݀ x`
        # `݀ͅ` at message end, `x ݀ͅ 5`, the double rider `x ݀ͅͅ x`, `x ݀ͅa x` (a letter
        # continues the stray word), `5݀ͅ5` — with `x ݂́ܒ x` and the vowel row `x ݂ܶ x` exact as
        # controls. So the clause is gone rather than narrowed.
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

    # A HARD run is not homogeneous. `文？` is one run by class, so a whole-run test sees a mixed
    # body and the `？` loses the border markers it is entitled to — while the same character in a
    # run of its own gets them. Measured
    # 2026-08-08: `文？ 文` and `文 ？文` each cost one more than that spelling charges, `文？文`
    # and `文？  文` are exact, and `あ？ 文` (already its own run) was exact all along. So the run
    # is split where the character KIND changes, and the existing predicates then apply per piece.
    #
    # A variation selector never opens a sub-run of its own: it rides its base's sub-run. So is
    # punct-like and Mn is not, so `⚖️` would otherwise sever at the selector — the symbol sub-run
    # takes its ⟨bow⟩ but the trailing selector falls to the no-marker branch and the ⟨eow⟩ is
    # lost. Measured 2026-08-09: `1 ⚖️ 1` = 22 and `1 ✔️ 1` = 21, one more than the severed
    # spelling charges; `a ⚖️ b` = 19 is exact either way because the letter seam cancels it.
    split = []
    for cls, body in out:
        if cls != HARD or len(body) == 1:
            split.append((cls, body))
            continue
        cur = body[0]
        for ch in body[1:]:
            if (VARIATION_SELECTORS[0] <= ord(ch) <= VARIATION_SELECTORS[1]
                    or _hard_kind(ch) == _hard_kind(cur[-1])):
                cur += ch
            else:
                split.append((cls, cur))
                cur = ch
        split.append((cls, cur))
    return split


def _ideographic_punct(ch: str) -> bool:
    """Punctuation of the CJK Symbols and Punctuation block, which takes NO border marker.

    Measured 2026-08-08 over every P-category character of U+3001–U+303F: 25 of 25 write neither
    ⟨bow⟩ nor ⟨eow⟩. Two independent signatures agree — the digit frames over-charge if a marker is
    written (`1 。 1` reads 17 against the 19 a marker costs), and the seam frame rejects a fused
    piece as the alternative explanation (`a。 b` reads 15; a `。⟨eow⟩` piece would make it 14, which
    is exactly how `，` was shown to be marker-TAKING with its ⟨eow⟩ swallowed by a piece).

    It is the block that predicts this, not the category and not the width. Controls outside it all
    take markers: fullwidth `？！～`, halfwidth `｡｢｣･`, and `・` U+30FB — which is East_Asian_Width
    Wide and CJK-looking, so it refutes both of those as the rule. Sentence-terminal does not
    predict it either: `。` is markerless and `？` is not.
    """
    return 0x3001 <= ord(ch) <= 0x303F and unicodedata.category(ch).startswith("P")


def _hard_kind(ch: str) -> str:
    """Which pretoken alternative a character of a HARD run belongs to.

    A HARD run is a run of our own class, not a pretoken: the conventional pretokenizer regex
    alternates ``\\p{L}\\p{M}*`` | ``\\p{N}+`` | ``[^\\s\\p{L}\\p{N}]+``, so a number and the
    ideograph beside it are different pretokens however our classifier grouped them. The
    punctuation split was measured first (`文？ 文`); the number split is the same fact for the
    other alternative, and `件 ５年` = 17, `件 ½年` = 17, `件 ５。` = 17, `件 ５５年` = 18,
    `取 ５年` = 17, `문 ５년` = 17 each cost one more than an unsplit run charges — the ⟨bow⟩ the
    digit branch writes once `５` is a run of its own. Controls: `件 5年` `x 5年 x` (ASCII digits
    are not border digits), `件 年５` `件 。５` (nothing borders the space), `x ５年 x` `x ５。 x`
    `x ५年 x` (exact either way — the seam eats the new ⟨bow⟩ against the word's ⟨eow⟩, which is
    why a Latin frame could never have found this), and `文〇 文` `件 〇年` (U+3007 is Nl, outside
    the measured Nd/No border population, and stays with its ideographs).
    """
    if _marks_like_punct(ch):
        return "punct"
    if _digit_border(ch):
        return "number"
    return "letter"


def _marks_like_punct(ch: str) -> bool:
    """Is this character one the border-marker branch can claim — punctuation, symbol or format?

    Ideographic punctuation is excluded, so it stays in the ideograph run it sits in and takes no
    markers. That is per BORDER CHARACTER rather than per run: `1。？ 1` and `1 ？。1` are exact
    because the marker sits on the `？` side, while `1？。 1` and `1 。？1` are one over if the run
    is judged as a whole.

    ASTRAL characters are excluded too: an emoji takes no border marker, so it must not be the
    punct KIND either — a format
    character in front of one would be glued into a single markerless sub-run and lose the ⟨bow⟩
    it is entitled to. Measured 2026-08-10 on the Sorani corpus row's three sites and the grid
    bought from them: `📐 ‎📝` `🎓 ‎⏰` `🔍 ‎📝` `📐 ‎👨` (LRM before an emoji) each read one
    under glued, in both families, while `1 📐 ‎1` `文 📐 ‎文` `📐 ‎` `📐‎📝` `📐 📝` are exact
    either way — the sub-run split at the letter/punct kind change is what keeps the LRM its own
    run against `文`, and this exclusion is what keeps it one against `📝`.
    """
    if ord(ch) >= 0x10000:
        return False
    cat = unicodedata.category(ch)
    return (cat[0] in ("P", "S") or cat == "Cf") and not _ideographic_punct(ch)


def stream(text: str, model) -> str:
    """Text → the marked stream, in the internal glyph form ``pieces.json`` keys parse to.

    A WORDY run is bracketed ⟨bow⟩…⟨eow⟩ and case-normalized. A single space between two such runs
    is dropped — the ⟨eow⟩⟨bow⟩ seam is what encodes it. Every other space stays literal.
    Punctuation-like, digit, killer, and stray-mark runs receive their measured boundary markers.
    """
    return stream_norm(nfc(text, fold_quotes=model.fold_quotes), model,
                       raw_head_space=raw_head_space(text))


def raw_head_space(text: str) -> bool:
    """Is the message's leading space one the RAW text supplies — the only one the frame absorbs?

    The frame's leading-space absorption is a fact about the RAW message head: the frame ends in
    ⟨bow⟩ and that ⟨bow⟩ IS the space (' a' = 12 on v4.7, same as 'a'). Anything else standing
    between the frame and the text was read by the oracle before the space was, and the oracle does
    not absorb across it — whether :func:`nfc` then STRIPS that character or FOLDS it INTO the
    space makes no difference to what the oracle saw.

    This predicate used to ask the narrower question "did nfc strip the first character", and the
    fold half was missing. Measured 2026-08-12, one token under without it in both families and
    exact with it: '\\xa0a' '\\xa0.' '\\xa0::' (the three NBSP-led Rosetta prefixes in the store),
    the other folded spaces '\\u2009a' '\\u202fa' '\\u2007a', and NUL, which ``nfc`` folds to a
    space rather than stripping: '\\x00a' '\\x00.' — 8 shapes per family, all at oracle 2 where the
    absorbed spelling charges 1.

    Controls, unmoved by the widening: ' a' = 1 and 'a' = 1 (a real raw space still absorbs),
    '  a' = 2, '\\x95a' = 1 (the strip itself is right — the character costs nothing), '\\x95 a'
    and '\\uf0d8 a' = 2 (2026-08-09, the rows this predicate was built on), '\\xa0 a' and
    '\\xa0\\xa0a' = 2 (a second space is not absorbed either way), 'a\\xa0a' 'a\\xa0b'
    'x \\xa0 x' (mid-text folds never touch the head rule), '\\ta' '\\na' '5 a' ' 5' ' .'.
    """
    return text.startswith(" ")


def stream_norm(norm: str, model, *, raw_head_space: bool = True) -> str:
    """The marked stream over already-normalized text.

    This is :func:`stream` over text the caller has already folded. It is split out so a document
    is NFC-folded once and the caller can read the content-final newline run — which ``rstrip``
    below drops — off the same string it streams (see ``engine.frame_tail``).
    """
    # The frame's tail, for a family whose frame HAS one: `engine.tile` reads the run off the same
    # string before dropping it here. A "free" family is stripped on the raw text instead (see
    # `tile`), so there is nothing left to take off here and taking it would eat a folded NBSP.
    if model.frame_tail == "ladder":
        norm = norm.rstrip(model.frame_strip)
    # A single leading space is dropped: the frame ends in ⟨bow⟩ and that ⟨bow⟩ IS the space
    # (' a' = 1). Two or more are a whitespace-run token and stay ('  a' = 2).
    # Where the frame does NOT end in a ⟨bow⟩ (v5), there is no space to stand in for: the leading
    # space is a character like any other, and ' a' costs one more than 'a' rather than the same.
    # A space that normalization EXPOSED or MANUFACTURED is not the raw head and is not absorbed
    # either — the oracle read `[stripped or folded char][space][text]` (see
    # :func:`raw_head_space`).
    if model.frame_bow and raw_head_space and norm[:1] == " " and norm[1:2] != " ":
        norm = norm[1:]
    runs = _runs(norm, model)
    if not runs:
        # Content that normalizes away entirely still pays for the frame's ⟨bow⟩. It is the same
        # ⟨bow⟩ the `out` list below writes when the first run supplies none: with nothing to
        # attach to it tiles as itself, and returning "" dropped it. Measured 2026-08-12, oracle 1
        # against our 0 in both families, on eight messages that strip to nothing — the private-use
        # characters U+F0B7, U+F0E8, U+E000 and U+F0B7 doubled, and the controls U+0095, U+0001,
        # U+007F and U+0095 U+0096. Controls, unmoved at 1, where the same ⟨bow⟩ is absorbed into
        # the word that follows: 'a', '\x95a', '\uf0b7a'. A whitespace-only message cannot be
        # asked at all — the API refuses U+000B.
        return BOW_G if model.frame_bow else ""
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
                   first[0] in (WORDY, PUNCT, _STRAY_MARK)
                   or (first[0] == _KILLER and _borders(first[1][0]))
                   or _is_borderable_text(first[1])
                   or (first[0] in (DIGIT, HARD) and _digit_bow(first[1]))
                   or (first[0] == SPACE and first[1][:1] == " "))
    # Nothing to hand out where the frame ends in no ⟨bow⟩: a digit or an ideograph opening the
    # message pays for no marker, which is exactly where v5 counts one token under v4.7.
    out = [] if has_own_bow or not model.frame_bow else [" " if head_quote else BOW_G]
    for i, (cls, body) in enumerate(runs):
        if cls == WORDY:
            # A wordy span is flanked on both sides, always — except where a contraction apostrophe
            # is already its opening boundary (see `_contraction_seam`), or where an unattached mark
            # run in front of it already opened this very word (the `_STRAY_MARK` branch below).
            # In that second case the span's head is the MARK, not this letter, which is why the
            # case markers go with it (`mark_case(head_mark=...)`).
            fused = bool(i) and runs[i - 1][0] == _STRAY_MARK
            n = mark_case(body, caps, head_mark=fused)
            pre = ""
            while n[:1] in (SHIFT_G, CAPS_G):     # case markers precede ⟨bow⟩ in the file's spelling
                pre, n = pre + n[0], n[1:]
            bow = "" if (fused or _contraction_seam(runs, i)) else BOW_G
            out.append(pre + bow + n + EOW_G)
        elif cls == _STRAY_MARK:
            # A stray-mark pretoken is a WORD: ⟨bow⟩ on the left even when it is adjacent to a
            # symbol, digit or punctuation run, and ⟨eow⟩ on the right against everything except a
            # LETTER — which does not merely continue the word, it IS the rest of it. The mark run
            # writes no ⟨eow⟩ and the letter writes no ⟨bow⟩ of its own (the WORDY branch above):
            # `⟨bow⟩M abc⟨eow⟩`, one word, exactly as `_syriac_vowel` and U+0CF3 already fuse.
            #
            # Measured 2026-08-10, on the frame that cancels the mark's own price. The two
            # spellings differ ONLY by the word's ⟨bow⟩, so across right-hand words W the severed
            # error moves with `cost(⟨bow⟩W⟨eow⟩) - cost(W⟨eow⟩)` and the fused error cannot move
            # at all — whatever the mark costs, it costs the same in every column:
            #
            #     W          x     abc    the     ก      ꝛ     ся        (`x ͣW x`, v3 / v4.7)
            #     severed    0/0  -1/0    0/-1   +1/+1  +1/+1  +1/+1
            #     fused      0/0   0/0    0/0     0/0    0/0    0/0
            #
            # 22 marks spanning the combining Latin/Cyrillic letters, U+0345, the Hebrew points,
            # the Arabic harakat and annotations, Samaritan, Thaana, Tibetan, Thai and Buginese,
            # each on those six words in two frames (`x MW x`, `!MW x`) and both families: the
            # severed spelling reads a SPREAD of −1/0/+1 for every mark and the fused spelling a
            # constant, never the other way round. `x ͣabc x` = 14 on v3 and `x ͣthe x` = 18 on
            # v4.7 — the last two under-counting texts in the cache — are two cells of it, and
            # §14.6's `x ͣก x` `x ͣب x` over-counts are two more.
            #
            # The run head does NOT byte-price. That clause was standing in for this boundary: with
            # the word's ⟨bow⟩ wrongly written, every mark that owns a unit piece read one under,
            # and forcing the raw floor cancelled it. Separated, the floor is a constant over-charge
            # on exactly those marks — U+064F U+0E38 U+05B0 +1 and U+0F72 U+064B +1/+2 in all nine
            # frames of the head grid, exact without it, with U+0363 U+05B1 U+2DE0 U+0670 U+0EB8
            # unmoved either way. That closes LIMITS §14.6's "three marks over-priced at a stray
            # run head by a constant"; the marks reach their piece here as anywhere else.
            letter_follows = i + 1 < n_runs and runs[i + 1][0] == WORDY
            out.append(BOW_G + body + ("" if letter_follows else EOW_G))
        elif cls == _KILLER:
            # A terminal separator run takes the same border markers punctuation does. Measured
            # 2026-08-08 on Lao ່, Khmer ់, Myanmar ့, Thai ่, Bengali ্: `ກ່ 5` and `5 ່ກ` each
            # cost one more than an unmarked run charges, `5 ່ 5` costs two, and `ກ່5`, `ກ່  5`
            # (space run kills the marker) and `ກ່` at message end are exact. The control is a
            # NON-terminal mark of the same script — Lao ຸ — which is exact unmarked.
            #
            # An ASTRAL separator writes neither (:func:`_borders`), per border CHARACTER as the
            # digit branch is. All 30 of them read two markers too many with this unqualified.
            out.append((BOW_G if borders_space(i, -1) and _borders(body[0]) else "") + body
                       + (EOW_G if borders_space(i, +1) and _borders(body[-1]) else ""))
        elif cls == PUNCT or _is_borderable_text(body):
            # A punct span is marked only on the side that borders whitespace: `a! b` gets `!⟨eow⟩`,
            # `a!b` gets a bare `!`. The marker is written unconditionally; the vocabulary decides
            # whether a piece swallows it.
            takes_bow = borders_space(i, -1) and not _opens_word(runs, i)
            out.append((BOW_G if takes_bow else "") + body
                       + (EOW_G if borders_space(i, +1) else ""))
        elif _digit_run(body) and cls in (DIGIT, HARD):
            # A digit run takes the same border markers punctuation does, on BOTH sides, and which
            # side is written is decided by the border character (`_digit_bow`, `_digit_eow`).
            #
            # The ⟨eow⟩ half was missing, and with it went a clause that gave an ASCII run a ⟨bow⟩
            # "against a non-ASCII digit neighbour across the space". That clause was standing in
            # for the neighbour's own ⟨eow⟩: wherever it fired, the seam deleted the space between
            # the two markers, so the pair is interchangeable and the probes could not tell them
            # apart. They separate on a space RUN, which kills the marker but not the seam-less
            # ⟨bow⟩ — `٥  5` = 16 and `٥5 5` = 17 and `文 ٥5 5` = 20 each read one MORE with the
            # lookback clause and exact without it. So it is gone rather than mirrored.
            out.append((BOW_G if _digit_bow(body) and borders_space(i, -1) else "") + body
                       + (EOW_G if _digit_eow(body) and borders_space(i, +1) else ""))
        else:
            out.append(body)                      # HARD letter scripts and whitespace: no markers
    return SEAM_RE.sub(r"\1" + EOW_G + r"\2" + BOW_G, "".join(out))
