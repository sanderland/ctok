"""The public API contract, normalization rules, and recorded edge cases."""

import random
import unicodedata

import pytest
import regex

from ctok import marked_stream, normalize, token_count, tokenize
from ctok.constants import HARD, PAD, WORDY
from ctok.main import FAMILIES, _family, _model
from ctok.normalize import classify, is_separator

# Inputs that have historically been edge cases, or would crash a naive byte path.
ADVERSARIAL = [
    "",
    " ", "\t", "\n", "\n" * 40, "\r\n", " " * 5000,
    "\x00", "\x01\x02\x1f", "\x7f",
    "\ud83d", "\udc00", "a\ud800b",      # lone / embedded surrogates: not UTF-8-encodable
    "�",
    "\U0001F600", "\U0010FFFF",
    "👨‍👩‍👧‍👦",                            # ZWJ emoji sequence
    "İstanbul", "ﬁ", "ß", "ẞ",           # casing and ligature oddities
    "नमस्ते", "ก็็็็็", "中文", "한국어",     # Brahmic / stacked Thai marks / CJK / Hangul
    "́" * 50,                       # combining marks only
    "a" * 20000, "1" * 20000, "!" * 20000,
    "WORLD中hello",
    "﷐﷑",                      # the marker noncharacters, as literal input
]


@pytest.mark.parametrize("version", ["3.0", "4.7"])
@pytest.mark.parametrize("text", ADVERSARIAL, ids=range(len(ADVERSARIAL)))
def test_tokenize_is_total_on_str(text: str, version: str):
    """Every ``str`` produces a finite token list."""
    tokens = tokenize(text, version=version)
    assert isinstance(tokens, list)
    assert len(tokens) >= _model(_family(version)).message_overhead


@pytest.mark.parametrize("version", ["3.0", "4.7"])
def test_token_list_starts_with_the_message_frame(version: str):
    """The list is the frame as ⟨pad⟩ tokens followed by the content tokens, which concatenate back
    to the marked stream. How many pieces the content takes is family-specific."""
    overhead = _model(_family(version)).message_overhead
    tokens = tokenize("hello", version=version)
    assert tokens[:overhead] == [PAD] * overhead
    assert "".join(tokens[overhead:]) == "⟨bow⟩hello⟨eow⟩" == marked_stream("hello", version=version)


def test_word_count_never_exceeds_letter_count():
    rng = random.Random(0)
    overhead = _model("v3").message_overhead
    for _ in range(500):
        word = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(1, 24)))
        assert overhead + 1 <= token_count(word) <= overhead + len(word)


def test_marked_stream_is_the_one_intermediate():
    assert marked_stream("hello, world") == "⟨bow⟩hello⟨eow⟩,⟨eow⟩⟨bow⟩world⟨eow⟩"


# ---- marks and boundaries: (text, marked stream or None, content tokens or None), identical in
# both families. Claude's word class is Unicode Alphabetic: non-Alphabetic marks stand outside;
# Alphabetic marks stay inside. A Syriac vowel point after a separator is a word-forming letter;
# an unattached Alphabetic mark run is a word that a following letter continues. Every content
# number is a recorded measurement.
MARK_ROWS = [
    # separator marks stand outside word boundaries; at a single-space border the separator
    # takes punctuation's right-hand ⟨eow⟩ and the seam then deletes the space
    ("क्", "⟨bow⟩क⟨eow⟩्", None),
    ("क्ष", "⟨bow⟩क⟨eow⟩्⟨bow⟩ष⟨eow⟩", None),
    ("क् ष", "⟨bow⟩क⟨eow⟩्⟨eow⟩⟨bow⟩ष⟨eow⟩", None),
    ("्", "⟨bow⟩्", None),
    # U+0301 and U+030A are not Alphabetic; U+0345 and U+0363 are.
    ("h\u0301b", "⟨bow⟩h⟨eow⟩́⟨bow⟩b⟨eow⟩", None),
    ("h\u030ab", "⟨bow⟩h⟨eow⟩̊⟨bow⟩b⟨eow⟩", None),
    ("h\u0345b", "⟨bow⟩hͅb⟨eow⟩", None),
    ("h\u0363b", "⟨bow⟩hͣb⟨eow⟩", None),
    # Syriac separator runs: a vowel point after one is a word-forming letter (`_syriac_vowel`);
    # vowel points on a real base stay inside one word
    ("ܒ݁ܒ", "⟨bow⟩ܒ⟨eow⟩݁⟨bow⟩ܒ⟨eow⟩", 10),
    # Same count as the older `݂ ⟨bow⟩` spelling: the separator's ⟨eow⟩ lets the seam eat the space.
    ("ܒ݂ ܒ", "⟨bow⟩ܒ⟨eow⟩݂⟨eow⟩⟨bow⟩ܒ⟨eow⟩", 11),
    ("ܒ݂ܶܒ", "⟨bow⟩ܒ⟨eow⟩݂⟨bow⟩ܶܒ⟨eow⟩", 12),
    ("ܒ݀ܒ", "⟨bow⟩ܒ⟨eow⟩݀⟨bow⟩ܒ⟨eow⟩", 10),
    ("ܒ݊ܶܒ", "⟨bow⟩ܒ⟨eow⟩݊⟨bow⟩ܶܒ⟨eow⟩", 12),
    ("ܒܰܒ", "⟨bow⟩ܒܰܒ⟨eow⟩", 8),
    # accents separate a Syriac word like any other host's
    ("ܒ̱", "⟨bow⟩ܒ⟨eow⟩̱", 6),
    ("ܒ̱ܒ", "⟨bow⟩ܒ⟨eow⟩̱⟨bow⟩ܒ⟨eow⟩", 10),
    # The separator takes punctuation's right-hand ⟨eow⟩ at a single-space border and the
    # seam then deletes the space, so this row costs the same as a literal space.
    ("ܒ̱ ܒ", "⟨bow⟩ܒ⟨eow⟩̱⟨eow⟩⟨bow⟩ܒ⟨eow⟩", 11),
    ("ܒ̱ܶܒ", "⟨bow⟩ܒ⟨eow⟩̱⟨bow⟩ܶܒ⟨eow⟩", 12),
    ("ܒ̣ܒ", "⟨bow⟩ܒ⟨eow⟩̣⟨bow⟩ܒ⟨eow⟩", 10),
    ("ܒ̣ܶܒ", "⟨bow⟩ܒ⟨eow⟩̣⟨bow⟩ܶܒ⟨eow⟩", 12),
    ("ܒͣܒ", "⟨bow⟩ܒͣܒ⟨eow⟩", 8),
    # an unattached mark run is a word (`_stray_mark`)
    ("\u0363", "⟨bow⟩ͣ⟨eow⟩", 4),
    ("\u0363\u0363", "⟨bow⟩ͣͣ⟨eow⟩", 6),
    ("x \u0363 x", "⟨bow⟩x⟨eow⟩⟨bow⟩ͣ⟨eow⟩⟨bow⟩x⟨eow⟩", 6),
    ("x \u03635 x", "⟨bow⟩x⟨eow⟩⟨bow⟩ͣ⟨eow⟩5 ⟨bow⟩x⟨eow⟩", 8),
    ("x \u0363", "⟨bow⟩x⟨eow⟩⟨bow⟩ͣ⟨eow⟩", 5),
    # A letter after it is the same word: no ⟨eow⟩, and no ⟨bow⟩ of its own.
    ("x \u0363x x", "⟨bow⟩x⟨eow⟩⟨bow⟩ͣx⟨eow⟩⟨bow⟩x⟨eow⟩", 6),
    ("x \u0363abc x", "⟨bow⟩x⟨eow⟩⟨bow⟩ͣabc⟨eow⟩⟨bow⟩x⟨eow⟩", 7),
    ("!\u0363a", "⟨bow⟩!⟨bow⟩ͣa⟨eow⟩", 5),
    ("\u0363\ua75b", "⟨bow⟩ͣꝛ⟨eow⟩", 7),
    # The span head is the mark, so neither case marker can assert what it asserts: literal.
    ("x \u0363\u0e01 x", "⟨bow⟩x⟨eow⟩⟨bow⟩ͣก⟨eow⟩⟨bow⟩x⟨eow⟩", 6),
    # A separator mark is not a stray one, and writes no ⟨eow⟩ at message end.
    ("\u1be6\ua75b", "⟨bow⟩᯦⟨bow⟩ꝛ⟨eow⟩", 9),
    ("\u0302", "⟨bow⟩̂", 3),
    ("\u0302\u0302", "⟨bow⟩̂̂", 5),
    ("\u0363\u0302", "⟨bow⟩ͣ⟨eow⟩̂", 6),
    ("\u0302\u0363", "⟨bow⟩̂⟨bow⟩ͣ⟨eow⟩", 7),
    # a non-separator stray mark opens its own run after punctuation; a separator shares the
    # punctuation run's opening boundary
    ("!\u0302", "⟨bow⟩!̂", 3),
    ("!\u0363", "⟨bow⟩!⟨bow⟩ͣ⟨eow⟩", 5),
    # an apostrophe opens an unattached mark word too (Syriac vowels are already word-forming;
    # separator accents are not mark words)
    ("'ً", None, 4), ("a 'ً x", None, 6), ("1 'ً 1", None, 8), ("a 'ͣ x", None, 8),
    ("a 'ܶ x", None, 8), ("a '́ x", None, 5),
    # a variation selector keeps its base's kind and owns the run's right edge
    ("  ☀️夏", None, 7), ("🏻️ 5", None, 8), ("夏️ 5", None, 7), ("☀️ 5", None, 7),
]


@pytest.mark.parametrize("version", ["3.0", "4.7"])
@pytest.mark.parametrize("text,stream,content", MARK_ROWS,
                         ids=lambda v: repr(v) if isinstance(v, str) else str(v))
def test_marks_and_boundaries(version, text, stream, content):
    if stream is not None:
        assert marked_stream(text, version) == stream
    if content is not None:
        overhead = _model(_family(version)).message_overhead
        assert token_count(text, version) - overhead == content


def test_bmp_mark_class_is_unicode_alphabetic():
    """The apparent script-specific separator law is exactly Unicode ``Alphabetic``.

    This exhaustive check is the evidence for using the regex property rather than maintaining
    accent, virama, tone-mark, and annotation tables by hand.
    """
    for codepoint in range(0x10000):
        char = chr(codepoint)
        if not unicodedata.category(char).startswith("M"):
            continue
        alphabetic = bool(regex.fullmatch(r"\p{Alphabetic}", char))
        assert (classify(char) == WORDY) is alphabetic
        if 0xFE00 <= codepoint <= 0xFE0F:
            assert not is_separator(char)
        else:
            assert is_separator(char) is not alphabetic
        assert classify(char) in (WORDY, HARD)


def test_the_accent_spelling_does_not_depend_on_the_host():
    """No accent but U+0301 is a piece; the two rows differ only by what the host letters
    cost, and the mark spelling is one rule with no per-host exception."""
    assert marked_stream("ܒ̣ܒ", "4.7") == "⟨bow⟩ܒ⟨eow⟩̣⟨bow⟩ܒ⟨eow⟩"
    assert marked_stream("q̣q", "4.7") == "⟨bow⟩q⟨eow⟩̣⟨bow⟩q⟨eow⟩"
    assert token_count("q̂q", "4.7") == 15
    assert token_count("ܒ̂ܒ", "4.7") == 21


@pytest.mark.parametrize("version", ["3.0", "4.7"])
def test_case_markers_do_not_fire_on_a_mark_headed_word(version):
    """⟨shift⟩ and ⟨caps⟩ both go when an unattached mark run heads the word: `x ͣThe x` reads one
    over with ⟨shift⟩ written, and v3's `x ͣHELLO x` reads two under with ⟨caps⟩."""
    overhead = _model(_family(version)).message_overhead
    assert marked_stream("x \u0363The x", version) == "⟨bow⟩x⟨eow⟩⟨bow⟩ͣThe⟨eow⟩⟨bow⟩x⟨eow⟩"
    assert marked_stream("x \u0363HELLO x", version) == "⟨bow⟩x⟨eow⟩⟨bow⟩ͣHELLO⟨eow⟩⟨bow⟩x⟨eow⟩"
    assert token_count("x \u0363The x", version) - overhead == (6 if version == "3.0" else 7)
    assert token_count("x \u0363HELLO x", version) - overhead == (10 if version == "3.0" else 9)


def test_normalization_is_family_specific():
    # v3 folds the curly quotes to ASCII; v4.7 measured not to.
    assert normalize("don’t", version="3.0") == "don't"
    assert normalize("don’t", version="4.7") == "don’t"


@pytest.mark.parametrize("version", ("3.0", "4.7"))
def test_thai_sara_am_composes_but_nfkc_does_not_apply(version):
    """Claude composes Thai SARA AM without applying NFKC generally."""
    assert normalize("ทํางาน", version=version) == "ทำงาน"
    assert token_count("ทํางาน", version=version) == token_count("ทำงาน", version=version)
    assert normalize("นํ้า", version=version) == "นํ้า"
    assert normalize("น้ํา", version=version) == "น้ำ"

    for text in ("ﬁ", "１", "Ⅻ", "①", "²"):
        assert normalize(text, version=version) == text


@pytest.mark.parametrize("version, overhead", (("3.0", 7), ("4.7", 11)))
@pytest.mark.parametrize("literal", [chr(cp) for cp in range(0xFDD0, 0xFDD5)])
def test_literal_internal_marker_codepoints_are_byte_priced(version, overhead, literal):
    """Input noncharacters must not become the engine's structural markers."""
    assert normalize(literal, version=version) == literal
    assert token_count(literal, version=version) == overhead + 4
    assert token_count(literal * 2, version=version) == overhead + 7
    assert token_count(f"a{literal}b", version=version) == overhead + 5
    assert "⟨0xEF⟩" in marked_stream(literal, version=version)


@pytest.mark.parametrize("version, overhead", (("3.0", 7), ("4.7", 11)))
def test_bmp_unassigned_characters_take_space_border_markers(version, overhead):
    for literal, content_cost in (("\u0378", 9), ("\u083f", 10), ("\u0efb", 9), ("\ufdef", 10)):
        assert token_count(f"5 {literal} 5", version=version) == overhead + content_cost

    # Astral unassigned codepoints remain markerless.
    assert token_count("5 \U0001000c 5", version=version) == overhead + 9


@pytest.mark.parametrize("version, overhead", (("3.0", 7), ("4.7", 11)))
def test_unicode_16_letters_use_the_word_and_case_model(version, overhead):
    """The source models know two cased letters newer than Python 3.13's Unicode table."""
    assert token_count("\u1c89", version=version) == overhead + 6
    assert token_count("\u1c8a", version=version) == overhead + 5
    assert token_count("\ua7cb", version=version) == overhead + 5
    assert token_count("\u0264", version=version) == overhead + 4
    assert token_count("\u1c89abc", version=version) == overhead + 7
    assert token_count("\ua7cb\u0264\u0264\u0264", version=version) == overhead + 11

    expected_caps = 11 if version == "3.0" else 14
    assert token_count("\ua7cb" * 4, version=version) == overhead + expected_caps


def test_dotted_capital_i_uses_the_ordinary_unit_piece():
    """İ is literal inside a cased span. It does not become a two-byte fallback after an uppercase
    vocabulary tile; that retired reading over-counted every short form where it still applied."""
    assert token_count("RPİ", version="3.0") == 10
    assert token_count("APİ", version="4.7") == 14


def test_version_routing():
    assert _family("3.0") == _family("3.5") == _family("4.6") == "v3"
    assert _family("4.7") == _family("4.8") == _family("4.9") == "v4.7"
    assert _family("5.0") == _family("5") == "v5"
    # Dotted-integer comparison, not decimal: "4.10" sorts after "4.9", not below "4.2".
    assert _family("4.10") == "v4.7"
    assert _family("4.1") == "v3"


def test_version_must_be_a_string():
    """A float cannot distinguish "4.1" from "4.10", so versions are not coerced."""
    for bad in (4.7, 5, None, ["4.7"]):
        with pytest.raises(TypeError):
            _family(bad)


def test_v5_borrows_the_v4_7_vocabulary_under_its_own_frame():
    """v5 reads v4.7's pieces with its own measured message frame."""
    assert FAMILIES["v5"].pieces == FAMILIES["v4.7"].pieces
    assert token_count("hello, world", "5.0") == token_count("hello, world", "4.7") - 5


def test_the_v5_frame_absorbs_any_trailing_whitespace():
    """v4.7's frame ends in ⏎⏎ and absorbs a trailing NEWLINE run, on a ladder that charges for
    some lengths. v5's absorbs every kind of trailing whitespace, at every length, but only the
    ASCII kind: a trailing NBSP folds to a space in normalization and still costs a token, which is
    why the strip runs on the raw text."""
    for tail in (" ", "   ", " " * 50, "\t", "\n", "\n" * 29, "\r\n", " \n\t \n"):
        assert token_count("hello world" + tail, "5.0") == token_count("hello world", "5.0"), repr(tail)
    assert token_count("hello world\xa0", "5.0") == token_count("hello world", "5.0") + 1
    # v4.7 keeps its ladder: 29 trailing newlines cost it a token where v5 pays nothing.
    assert token_count("hello world" + "\n" * 29, "4.7") == token_count("hello world", "4.7") + 1


def test_the_v5_frame_ends_in_no_bow():
    """Message start is an interior word boundary on v4.7. Its frame ends in ⟨bow⟩, so a
    single leading space is free and an opening run that cannot own that ⟨bow⟩ pays for it. v5 has
    no such token: the digit and the ideograph open for free, and the leading space is a character
    like any other."""
    assert token_count("123", "5.0") == token_count("123", "4.7") - 6      # 4.7 pays for the ⟨bow⟩
    assert token_count("日本", "5.0") == token_count("日本", "4.7") - 6
    assert token_count(" a", "5.0") == token_count("a", "5.0") + 1
    assert token_count(" a", "4.7") == token_count("a", "4.7")
    # A word opens with its own ⟨bow⟩ in both families, so nothing moves there beyond the frame.
    assert token_count("hello", "5.0") == token_count("hello", "4.7") - 5


@pytest.mark.parametrize("version", ["2.9", "banana"])
def test_unavailable_versions_raise(version):
    """Below 3.0 is not reconstructed, and neither is a nonsense version string."""
    with pytest.raises(NotImplementedError):
        token_count("hello", version=version)
    with pytest.raises(NotImplementedError):
        tokenize("hello", version=version)


@pytest.mark.parametrize("bad", [b"bytes", 42, None, ["a"]])
def test_non_str_input_rejected(bad):
    with pytest.raises(TypeError):
        token_count(bad)


def test_a_single_leading_space_is_free():
    """The frame's final ⟨bow⟩ is a single leading space; two or more are a whitespace-run token."""
    assert token_count(" hello") == token_count("hello")
    assert token_count("  hello") == token_count("hello") + 1


def test_trailing_newlines_are_absorbed_only_as_far_as_one_token_reaches():
    """The frame appends ⏎⏎ and one token spans content into it, so a trailing run of n newlines is
    really a run of n + 2 tiled over the newline vocabulary, less the frame's own token. Hence not
    monotonic: 1 to 28 free (30 is one token), 29 costs one, 30 and 31 free again (32 and 33 are),
    and 38 free (40 is). The split below is the measured pattern from all 40 recorded ``a`` + n
    rows and is prefix-independent across every other cached prefix."""
    base = token_count("hello")
    for n in (1, 3, 28, 30, 31, 38):
        assert token_count("hello" + "\n" * n) == base, n
    for n in (29, 32, 37, 39, 40):
        assert token_count("hello" + "\n" * n) == base + 1, n


# ---- the apostrophe and strip rules, each row a recorded ``count_tokens`` measurement ------------

# (version, text, content tokens). The count excludes the message frame, so the rows read as costs.
# Every one is a probe taken against that family's source model.
APOSTROPHE_ROWS = [
    # ⟨bow⟩' is a real piece: the boundary and the apostrophe price 1 together wherever no word
    # follows: at the message edge, before punctuation, or before a space.
    ("4.7", "'", 1), ("4.7", "'.", 2), ("4.7", "', '", 3), ("3.0", "'", 1), ("3.0", "'.", 1),
    # ...and it is not what the oracle reaches for in front of a word. Each of these costs one more.
    ("4.7", "'d", 3), ("4.7", "'m", 3), ("4.7", "'F", 3), ("4.7", "'First", 3),
    ("4.7", "a 'b", 4), ("4.7", "a 'x b", 5), ("3.0", "a 'b", 4),
    # A two-space run already priced this way, and the single space now matches it.
    ("4.7", "a  'b", 4),
    # Only `'` behaves so: the other word-opening punctuation absorbs the boundary normally.
    ("4.7", 'a "b', 3), ("4.7", "a (b", 3), ("4.7", "a -b", 3), ("3.0", 'a "b', 3),
    # And only a run that is exactly the apostrophe: in `('` or `'''` the boundary lands elsewhere.
    ("4.7", "a ('b", 4), ("4.7", "a '''a", 4), ("4.7", "z '''w", 4),
    ("3.0", "a '''a", 3), ("3.0", "z '''w", 3),
    # The contraction suffix is word-side: after a word or the boundary it is one token, after
    # other punctuation it is not.
    ("4.7", "f's", 2), ("4.7", "x's", 2), ("4.7", "x't", 2), ("4.7", "'s", 2), ("4.7", "'t", 2),
    ("4.7", "a 's b", 4), ("3.0", "x's", 2), ("3.0", "x't", 2),
    ("4.7", "}'s", 3), ("4.7", ".'s.", 4), ("4.7", ".'re.", 4), ("4.7", ".'ve.", 5),
    ("3.0", ".'s.", 4), ("3.0", ".'re.", 4), ("3.0", ".'ve.", 4),
]

# A punct piece spelled with a trailing space is the SEAM space, so it cannot open a run of two or
# more. The space-run ladder is {1..16} parts for a punct lead exactly as it is for a letter.
SPACE_RUN_ROWS = [("4.7", "]" + " " * 17 + "i", 5), ("4.7", "a" + " " * 17 + "b", 4)]


# A message whose content strips to nothing is pinned to the measured count, not to another
# stripped message. A relative comparison cannot fail because both sides move together.
FRAME_ONLY = {"3.0": 8, "4.7": 12, "5.0": 6}


@pytest.mark.parametrize("version, expected", sorted(FRAME_ONLY.items()))
@pytest.mark.parametrize("text", ["\uf8ff", "\x01", "\ue000\x01\x85"])
def test_content_that_strips_to_nothing_costs_the_frame(text, version, expected):
    assert normalize(text, version=version) == ""
    assert token_count(text, version=version) == expected


@pytest.mark.parametrize("version", ["3.0", "4.7", "5.0"])
def test_private_use_characters_are_stripped(version: str):
    """A BMP private-use codepoint is deleted like the C0/C1 controls. It costs nothing and
    joins its neighbours into one word. An astral private-use codepoint is not stripped and pays
    its bytes, as does an unassigned codepoint."""
    assert token_count("a\uf0b7b", version=version) == token_count("ab", version=version)
    assert normalize("a\ue000\uf8ffb", version=version) == "ab"
    assert token_count("\U000f0000", version=version) == FRAME_ONLY[version] + 4
    assert token_count("\U000f0000\U000f0001", version=version) == FRAME_ONLY[version] + 8
    assert token_count("a\U00090095a", version=version) > token_count("aa", version=version)


# The apostrophe is a word boundary only for the contraction suffixes. Each row is
# a recorded measurement; `x'll` is the one that discriminates, since `ll⟨eow⟩` is a piece where
# `⟨bow⟩ll⟨eow⟩` is not.
CONTRACTION_ROWS = [
    ("4.7", "x'll", 3), ("4.7", "we'll", 3), ("4.7", "a'll b", 4), ("4.7", "a 'll b", 5), ("4.7", "'ll", 3),
    ("4.7", "1'll", 4), ("4.7", "a  'll b", 5), ("4.7", "A'll", 3),
    # ...blocked when the apostrophe is inside a punct run, exactly as the suffix pieces are.
    ("4.7", ".'ll.", 5), ("4.7", "}'ll", 4), ("4.7", "a)'ll b", 6),
    # ...whole-word and lowercase only.
    ("4.7", "x'llo", 4), ("4.7", "x'lls", 4), ("4.7", "x'S", 3), ("4.7", "x'LL", 4),
    # ...and not a general rule: these have bow-less pieces too and still pay for the boundary.
    ("4.7", "x'ji", 4), ("4.7", "x'ka", 4), ("4.7", "x'ing", 4), ("4.7", "a ll b", 4), ("4.7", "ll", 2),
]

# Astral symbols take no boundary markers, where BMP ones do; variation selectors take no word
# model. Digit anchors, as the boundary campaign used.
# The thirteen pieces the 2026-08-01 bisect witnessed, each with the control that bounds it.
PIECE_ROWS = [
    ("4.7", "△", 1), ("4.7", "▽", 3), ("4.7", "◇", 3),                       # ⟨bow⟩△, and its neighbours
    ("4.7", "║", 2), ("4.7", "a║b", 3), ("4.7", "╔", 3),                      # ║ is a whole character
    ("4.7", "a McN b", 4), ("4.7", "a McQ b", 5), ("4.7", "a MdN b", 5),      # ⟨bow⟩Mc, control MdN
    ("4.7", "a neither b", 4), ("4.7", "a zither b", 4), ("4.7", "a wather b", 4),   # ither⟨eow⟩
    ("4.7", "'./", 1), ("4.7", "a './b", 3), ("4.7", "'.", 2), ("4.7", "./", 2),       # ⟨bow⟩'./
    ("4.7", "a КИ b", 5), ("4.7", "a КЭ b", 6), ("4.7", "a ЛИ b", 7),         # ⟨bow⟩К, control Л
    ("4.7", "a МИ b", 5), ("4.7", "a СИ b", 5), ("4.7", "a ПИ b", 6),         # ⟨bow⟩М ⟨bow⟩С, control П
]

SYMBOL_ROWS = [
    ("4.7", "1🐫1", 6), ("4.7", "1 🐫1", 7), ("4.7", "1🐫 1", 7), ("4.7", "1 🐫 1", 8),
    ("4.7", "1😀1", 5), ("4.7", "1 😀1", 6), ("4.7", "1 😀 1", 7),
    ("4.7", "1←1", 4), ("4.7", "1 ←1", 6), ("4.7", "1← 1", 5), ("4.7", "1 ← 1", 7),
    ("4.7", "️", 2), ("4.7", "⚖️", 5), ("4.7", "⚖︎", 6), ("4.7", "a️b", 3),
]


@pytest.mark.parametrize(
    "version,text,content",
    APOSTROPHE_ROWS + SPACE_RUN_ROWS + CONTRACTION_ROWS + SYMBOL_ROWS + PIECE_ROWS,
    ids=lambda v: repr(v) if isinstance(v, str) else str(v))
def test_recorded_costs(version, text, content):
    overhead = _model(_family(version)).message_overhead
    assert token_count(text, version=version) - overhead == content


@pytest.mark.parametrize("corpus_name", ["rosetta", "multipl_e", "udhr", "rosetta_holdout"])
def test_v5_tracks_v4_7_document_for_document(corpus_name):
    """v5 makes the same error as v4.7 on every document, which is why it is not gated
    separately: for each document, v5's deviation from its recorded count equals v4.7's from its
    own, both fixtures being independent `count_tokens` readings. Deliberately not asserted: that
    the two counts differ by a constant (they differ by 5 or 6 depending on the opening run, and
    predicting which would restate the head rule inside a test).
    """
    from gates import GATES, corpus, recorded

    key = GATES[corpus_name]["key"]
    rows = corpus(corpus_name)[:60]
    c47, c5 = recorded(corpus_name, "v4.7")["counts"], recorded(corpus_name, "v5")["counts"]
    for r in rows:
        text, k = r["text"], r[key]
        assert token_count(text, "5.0") - c5[k] == token_count(text, "4.7") - c47[k], \
            f"v5 stopped tracking v4.7 on {corpus_name}/{k}; it needs its own gate row again"
