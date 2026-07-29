"""The public API contract: the count is the length of the token list, the model is total on any
``str``, and version routing behaves."""

import random

import pytest

from ctok import marked_stream, normalize, token_count, tokenize
from ctok.constants import PAD
from ctok.main import _family, _model

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


@pytest.mark.parametrize("version", [2.9, 0, "banana", 5.0, "5.1"])
def test_unavailable_versions_raise(version):
    """Below 3.0 and at/above 5.0 are not reconstructed, and neither is a nonsense version."""
    with pytest.raises(NotImplementedError):
        token_count("hello", version=version)
    with pytest.raises(NotImplementedError):
        tokenize("hello", version=version)


@pytest.mark.parametrize("bad", [b"bytes", 42, None, ["a"]])
def test_non_str_input_rejected(bad):
    with pytest.raises(TypeError):
        token_count(bad)


def test_trailing_newlines_and_a_single_leading_space_are_free():
    """The message frame absorbs trailing newlines, and its final ⟨bow⟩ IS a single leading space."""
    assert token_count("hello\n\n\n") == token_count("hello")
    assert token_count(" hello") == token_count("hello")
    assert token_count("  hello") == token_count("hello") + 1
