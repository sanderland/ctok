"""The vocabulary index must be an exact acceleration of the generic tiling DP."""

from ctok.engine import ReverseTrie, min_tile, min_vocab_tile


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
