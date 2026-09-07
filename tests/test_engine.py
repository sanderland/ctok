"""The vocabulary index and byte floor must preserve their reference tilings."""

import pytest

from ctok.engine import ByteFloor, ReverseTrie, min_tile, min_vocab_tile, valid_utf8_prefix
from ctok.main import TokenizerModel


def test_reverse_trie_dp_matches_exhaustive_search_including_ties():
    pieces = frozenset({"a", "b", "ab", "ba", "aba", "bab", "aaaa", "\n" * 128})
    trie = ReverseTrie(pieces)

    def exhaustive(text, floors):
        def cost_fn(start, end):
            if text[start:end] in pieces:
                return 1
            return floors[text[start]] if end - start == 1 else None

        return min_tile(len(text), cost_fn, max(map(len, pieces)))

    floors = {"a": 1, "b": 2, "x": 4, "\n": 1}
    for text in ("a", "x", "abba", "abababa", "baxab", "a" * 20, "\n" * 257):
        assert min_vocab_tile(text, trie, lambda at: floors[text[at]]) == exhaustive(text, floors)


def _reference_byte_chunks(bs: bytes, tokens: set[str]) -> list[bytes]:
    def cost_fn(start, end):
        return 1 if end - start == 1 or bs[start:end].hex() in tokens else None

    _, spans = min_tile(len(bs), cost_fn, max((len(token) // 2 for token in tokens), default=1))
    return [bs[start:end] for start, end in spans]


def test_byte_floor_matches_the_generic_dp_for_prefixes_and_unit_pieces():
    floor = ByteFloor({"c3", "e2", "e282", "f0"}, unit_chars=("é",))
    for char in ("", "a", "¢", "é", "€", "😀", "\U0010ffff"):
        encoded = char.encode()
        assert floor.chunks(encoded) == _reference_byte_chunks(encoded, floor.tokens)


def test_utf8_prefix_validation_rejects_nonprefix_bytes():
    assert valid_utf8_prefix(b"\xe0")
    assert valid_utf8_prefix(b"\xf0\x9f")
    for invalid in (b"a", b"\x80", b"a\xe0", b"\xed\xa0"):
        assert not valid_utf8_prefix(invalid)

    doc = {"meta": {"message_overhead": 1, "fold_quotes": False, "allcaps_min": None},
           "tokens": {"bytes_fallback": {"61": {}}}}
    with pytest.raises(ValueError, match="non-prefix"):
        TokenizerModel(doc)
