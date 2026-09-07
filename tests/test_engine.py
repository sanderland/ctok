"""The vocabulary index and byte floor must preserve their reference tilings."""

import json
from importlib.resources import files

from ctok.engine import ByteFloor, ReverseTrie, min_tile, min_vocab_tile, valid_utf8_prefix


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


def test_byte_fallback_entries_are_utf8_prefixes_and_the_fast_path_matches_dp():
    for name in ("pieces_v3.json", "pieces_v4_7.json"):
        doc = json.loads(files("ctok").joinpath("data", name).read_text())
        prefixes = set(doc["tokens"]["bytes_fallback"])
        assert all(valid_utf8_prefix(bytes.fromhex(prefix)) for prefix in prefixes)

        floor = ByteFloor(prefixes)
        # Each sequence is one codepoint, the only input shape ByteFloor receives from the tiler.
        for char in ("\x00", "é", "अ", "€", "😀", "\U0010ffff"):
            encoded = char.encode()
            assert floor.chunks(encoded) == _reference_byte_chunks(encoded, floor.tokens)
