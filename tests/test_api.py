"""The public API contract: the count is the length of the token list, the model is total on any
``str``, and version routing behaves."""

import random

import pytest

from ctok import marked_stream, normalize, token_count, tokenize
from ctok.constants import PAD
from ctok.main import FAMILIES, _family, _model

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


@pytest.mark.parametrize("version", [3.0, 4.7])
@pytest.mark.parametrize("text", ADVERSARIAL, ids=range(len(ADVERSARIAL)))
def test_total_and_count_is_list_length(text: str, version: float):
    """The model is total — every ``str`` gets a finite count without raising — and the count is by
    definition the length of the token list."""
    tokens = tokenize(text, version=version)
    count = token_count(text, version=version)
    assert isinstance(count, int)
    assert count == len(tokens)
    assert count >= _model(_family(version)).message_overhead


@pytest.mark.parametrize("version", [3.0, 4.7])
def test_token_list_starts_with_the_message_frame(version: float):
    """The list is the frame as ⟨pad⟩ tokens followed by the content tokens, which concatenate back
    to the marked stream. How many pieces the content takes is family-specific."""
    overhead = _model(_family(version)).message_overhead
    tokens = tokenize("hello", version=version)
    assert tokens[:overhead] == [PAD] * overhead
    assert "".join(tokens[overhead:]) == "⟨bow⟩hello⟨eow⟩" == marked_stream("hello", version=version)
    assert token_count("hello", version=version) == overhead + len(tokens[overhead:])


def test_word_count_never_exceeds_letter_count():
    rng = random.Random(0)
    overhead = _model("v3").message_overhead
    for _ in range(500):
        word = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(1, 24)))
        assert overhead + 1 <= token_count(word) <= overhead + len(word)


def test_marked_stream_is_the_one_intermediate():
    assert marked_stream("hello, world") == "⟨bow⟩hello⟨eow⟩,⟨eow⟩⟨bow⟩world⟨eow⟩"


def test_a_killer_junction_closes_on_jeow_and_a_final_killer_on_eow():
    """The internal junction and the word end are different positions with different spellings —
    a final-form piece is a prefix of the old ⟨eow⟩⟨bow⟩ junction pair, so one glyph for both let
    every `mark⟨eow⟩` piece match inside words, where the oracle prices the close differently."""
    assert marked_stream("क्ष", 4.7) == "⟨bow⟩क्⟨jeow⟩⟨bow⟩ष⟨eow⟩"
    assert marked_stream("क्", 4.7) == "⟨bow⟩क्⟨eow⟩"
    assert marked_stream("क्ष", 3.0) == "⟨bow⟩क्⟨jeow⟩⟨bow⟩ष⟨eow⟩"


def test_the_killer_seam_law_is_per_codepoint_and_per_family():
    """A killer-final word before a single space absorbs it only for the MEASURED absorb set
    (`normalize._KILLER_SEAM_ABSORB`), and only in the family whose vocabulary was translated —
    v3's corpus lines reject the translation, so its killers all keep the literal space."""
    # Malayalam virama: ABSORB in v4.7, kept in v3
    assert marked_stream("ത് ത", 4.7) == "⟨bow⟩ത്⟨eow⟩⟨bow⟩ത⟨eow⟩"
    assert marked_stream("ത് ത", 3.0) == "⟨bow⟩ത്⟨eow⟩ ⟨bow⟩ത⟨eow⟩"
    # Bengali virama: measured KEEP in both families
    assert marked_stream("ক্ ক", 4.7) == "⟨bow⟩ক্⟨eow⟩ ⟨bow⟩ক⟨eow⟩"
    assert marked_stream("ক্ ক", 3.0) == "⟨bow⟩ক্⟨eow⟩ ⟨bow⟩ক⟨eow⟩"


def test_normalization_is_family_specific():
    # v3 folds the curly quotes to ASCII; v4.7 measured not to.
    assert normalize("don’t", version=3.0) == "don't"
    assert normalize("don’t", version=4.7) == "don’t"


def test_version_routing():
    assert _family(3.0) == _family("3.5") == _family(4.6) == "v3"
    assert _family(4.7) == _family("4.8") == "v4.7"
    assert _family(5.0) == "v5"
    # A version is a decimal, not a dotted tuple: "4.10" is 4.1, which is below the v4.7 base.
    assert _family("4.10") == "v3"
    # A source-model id routes straight to the family that reconstructs it.
    assert _family("claude-opus-4-5") == "v3"
    assert _family("claude-opus-4-7") == "v4.7"
    assert _family("claude-opus-5") == "v5"
    # Measured, not assumed: sonnet-5 counts identically to opus-5 on 80 corpus texts.
    assert _family("claude-sonnet-5") == "v5"


def test_v5_borrows_the_v4_7_vocabulary_under_its_own_frame():
    """v5 counts with v4.7's pieces and its own measured message frame — five tokens smaller. The
    family table's override is what makes that one file rather than a copy that can drift."""
    assert FAMILIES["v5"].pieces == FAMILIES["v4.7"].pieces
    assert token_count("hello, world", 5.0) == token_count("hello, world", 4.7) - 5


def test_the_v5_frame_absorbs_any_trailing_whitespace():
    """v4.7's frame ends in ⏎⏎ and absorbs a trailing NEWLINE run, on a ladder that charges for
    some lengths. v5's absorbs every kind of trailing whitespace, at every length — but only the
    ASCII kind: a trailing NBSP folds to a space in normalization and still costs a token, which is
    why the strip runs on the raw text."""
    for tail in (" ", "   ", " " * 50, "\t", "\n", "\n" * 29, "\r\n", " \n\t \n"):
        assert token_count("hello world" + tail, 5.0) == token_count("hello world", 5.0), repr(tail)
    assert token_count("hello world\xa0", 5.0) == token_count("hello world", 5.0) + 1
    # v4.7 keeps its ladder: 29 trailing newlines cost it a token where v5 pays nothing.
    assert token_count("hello world" + "\n" * 29, 4.7) == token_count("hello world", 4.7) + 1


def test_the_v5_frame_ends_in_no_bow():
    """Message start is an interior word boundary on v4.7 — the frame's last token IS a ⟨bow⟩, so a
    single leading space is free and an opening run that cannot own that ⟨bow⟩ pays for it. v5 has
    no such token: the digit and the ideograph open for free, and the leading space is a character
    like any other."""
    assert token_count("123", 5.0) == token_count("123", 4.7) - 6      # 4.7 pays for the ⟨bow⟩
    assert token_count("日本", 5.0) == token_count("日本", 4.7) - 6
    assert token_count(" a", 5.0) == token_count("a", 5.0) + 1
    assert token_count(" a", 4.7) == token_count("a", 4.7)
    # A word opens with its own ⟨bow⟩ in both families, so nothing moves there beyond the frame.
    assert token_count("hello", 5.0) == token_count("hello", 4.7) - 5


@pytest.mark.parametrize("version", [2.9, 0, "banana"])
def test_unavailable_versions_raise(version):
    """Below 3.0 is not reconstructed, and neither is a nonsense version."""
    with pytest.raises(NotImplementedError):
        token_count("hello", version=version)
    with pytest.raises(NotImplementedError):
        tokenize("hello", version=version)


@pytest.mark.parametrize("bad", [b"bytes", 42, None, ["a"]])
def test_non_str_input_rejected(bad):
    with pytest.raises(TypeError):
        token_count(bad)


def test_a_single_leading_space_is_free():
    """The frame's final ⟨bow⟩ IS a single leading space; two or more are a whitespace-run token."""
    assert token_count(" hello") == token_count("hello")
    assert token_count("  hello") == token_count("hello") + 1


def test_trailing_newlines_are_absorbed_only_as_far_as_one_token_reaches():
    """The frame appends ⏎⏎ and one token spans content into it, so a trailing run of n newlines is
    really a run of n + 2 tiled over the newline vocabulary, less the frame's own token. Hence not
    monotonic: 1–28 free (30 is one token), 29 costs one, 30 and 31 free again (32 and 33 are), 38
    free (40 is). The split below is the live-measured pattern — 40/40 recorded ``a`` + n rows, and
    prefix-independent across every other cached prefix."""
    base = token_count("hello")
    for n in (1, 3, 28, 30, 31, 38):
        assert token_count("hello" + "\n" * n) == base, n
    for n in (29, 32, 37, 39, 40):
        assert token_count("hello" + "\n" * n) == base + 1, n


# ---- the apostrophe and strip rules, each row a recorded ``count_tokens`` measurement ------------

# (version, text, content tokens) — the count MINUS the message frame, so the rows read as costs.
# Every one is a probe taken against that family's source model.
APOSTROPHE_ROWS = [
    # ⟨bow⟩' is a real piece: the boundary and the apostrophe price 1 together wherever no word
    # follows — at the message edge, before punctuation, before a space.
    (4.7, "'", 1), (4.7, "'.", 2), (4.7, "', '", 3), (3.0, "'", 1), (3.0, "'.", 1),
    # ...and it is not what the oracle reaches for in front of a word. Each of these costs one more.
    (4.7, "'d", 3), (4.7, "'m", 3), (4.7, "'F", 3), (4.7, "'First", 3),
    (4.7, "a 'b", 4), (4.7, "a 'x b", 5), (3.0, "a 'b", 4),
    # A two-space run already priced this way, and the single space now matches it.
    (4.7, "a  'b", 4),
    # Only `'` behaves so: the other word-opening punctuation absorbs the boundary normally.
    (4.7, 'a "b', 3), (4.7, "a (b", 3), (4.7, "a -b", 3), (3.0, 'a "b', 3),
    # And only a run that IS the apostrophe: in `('` or `'''` the boundary lands elsewhere.
    (4.7, "a ('b", 4), (4.7, "a '''a", 4), (4.7, "z '''w", 4),
    (3.0, "a '''a", 3), (3.0, "z '''w", 3),
    # The contraction suffix is word-side: after a word or the boundary it is one token, after
    # other punctuation it is not.
    (4.7, "f's", 2), (4.7, "x's", 2), (4.7, "x't", 2), (4.7, "'s", 2), (4.7, "'t", 2),
    (4.7, "a 's b", 4), (3.0, "x's", 2), (3.0, "x't", 2),
    (4.7, "}'s", 3), (4.7, ".'s.", 4), (4.7, ".'re.", 4), (4.7, ".'ve.", 5),
    (3.0, ".'s.", 4), (3.0, ".'re.", 4), (3.0, ".'ve.", 4),
]

# A punct piece spelled with a trailing space is the SEAM space, so it cannot open a run of two or
# more. The space-run ladder is {1..16} parts for a punct lead exactly as it is for a letter.
SPACE_RUN_ROWS = [(4.7, "]" + " " * 17 + "i", 5), (4.7, "a" + " " * 17 + "b", 4)]


@pytest.mark.parametrize("version,text,content", APOSTROPHE_ROWS + SPACE_RUN_ROWS,
                         ids=lambda v: repr(v) if isinstance(v, str) else str(v))
def test_recorded_apostrophe_and_space_run_costs(version, text, content):
    overhead = _model(_family(version)).message_overhead
    assert token_count(text, version=version) - overhead == content


@pytest.mark.parametrize("version", [3.0, 4.7])
def test_private_use_characters_are_stripped(version: float):
    """A BMP private-use codepoint costs nothing AND joins its neighbours into one word — it is
    deleted, like the C0/C1 controls, not merely free. An UNASSIGNED codepoint is the control: it
    survives and pays its bytes."""
    assert token_count("ab", version=version) == token_count("ab", version=version)
    assert token_count("", version=version) == token_count("", version=version)
    assert normalize("ab", version=version) == "ab"
    assert token_count("a\U00090095a", version=version) > token_count("aa", version=version)


# The apostrophe is a word boundary for the contraction suffixes — and only for those. Each row is
# a recorded measurement; `x'll` is the one that discriminates, since `ll⟨eow⟩` is a piece where
# `⟨bow⟩ll⟨eow⟩` is not.
CONTRACTION_ROWS = [
    (4.7, "x'll", 3), (4.7, "we'll", 3), (4.7, "a'll b", 4), (4.7, "a 'll b", 5), (4.7, "'ll", 3),
    (4.7, "1'll", 4), (4.7, "a  'll b", 5), (4.7, "A'll", 3),
    # ...blocked when the apostrophe is inside a punct run, exactly as the suffix pieces are.
    (4.7, ".'ll.", 5), (4.7, "}'ll", 4), (4.7, "a)'ll b", 6),
    # ...whole-word and lowercase only.
    (4.7, "x'llo", 4), (4.7, "x'lls", 4), (4.7, "x'S", 3), (4.7, "x'LL", 4),
    # ...and not a general rule: these have bow-less pieces too and still pay for the boundary.
    (4.7, "x'ji", 4), (4.7, "x'ka", 4), (4.7, "x'ing", 4), (4.7, "a ll b", 4), (4.7, "ll", 2),
]

# Astral symbols take no boundary markers, where BMP ones do; variation selectors take no word
# model. Digit anchors, as the boundary campaign used.
# The thirteen pieces the 2026-08-01 bisect witnessed, each with the control that bounds it.
PIECE_ROWS = [
    (4.7, "△", 1), (4.7, "▽", 3), (4.7, "◇", 3),                       # ⟨bow⟩△, and its neighbours
    (4.7, "║", 2), (4.7, "a║b", 3), (4.7, "╔", 3),                      # ║ is a whole character
    (4.7, "a McN b", 4), (4.7, "a McQ b", 5), (4.7, "a MdN b", 5),      # ⟨bow⟩Mc, control MdN
    (4.7, "a neither b", 4), (4.7, "a zither b", 4), (4.7, "a wather b", 4),   # ither⟨eow⟩
    (4.7, "'./", 1), (4.7, "a './b", 3), (4.7, "'.", 2), (4.7, "./", 2),       # ⟨bow⟩'./
    (4.7, "a КИ b", 5), (4.7, "a КЭ b", 6), (4.7, "a ЛИ b", 7),         # ⟨bow⟩К, control Л
    (4.7, "a МИ b", 5), (4.7, "a СИ b", 5), (4.7, "a ПИ b", 6),         # ⟨bow⟩М ⟨bow⟩С, control П
]

SYMBOL_ROWS = [
    (4.7, "1🐫1", 6), (4.7, "1 🐫1", 7), (4.7, "1🐫 1", 7), (4.7, "1 🐫 1", 8),
    (4.7, "1😀1", 5), (4.7, "1 😀1", 6), (4.7, "1 😀 1", 7),
    (4.7, "1←1", 4), (4.7, "1 ←1", 6), (4.7, "1← 1", 5), (4.7, "1 ← 1", 7),
    (4.7, "️", 2), (4.7, "⚖️", 5), (4.7, "⚖︎", 6), (4.7, "a️b", 3),
]


@pytest.mark.parametrize("version,text,content", CONTRACTION_ROWS + SYMBOL_ROWS + PIECE_ROWS,
                         ids=lambda v: repr(v) if isinstance(v, str) else str(v))
def test_recorded_contraction_and_symbol_costs(version, text, content):
    overhead = _model(_family(version)).message_overhead
    assert token_count(text, version=version) - overhead == content
