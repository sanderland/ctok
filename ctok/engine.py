"""The min-cost tiling, with the marked-stream vocabulary indexed by a reverse trie.

    min_tile        generic segmentation DP for tiny byte strings
    min_vocab_tile  the same recurrence, visiting only vocabulary edges through the trie
    ByteFloor       byte tiling for characters no piece covers
    tile            marked-stream tiling for the count

Marker atoms are in the vocabulary as cost-1 tokens, so a marker no piece absorbs tiles as itself.
The count is the number of tiles.
"""

from __future__ import annotations

from .constants import EOW_G, ESCAPED_MARKER_LITERALS, MARKER_GLYPHS
from .normalize import nfc, raw_head_space, stream_norm


def min_tile(n: int, cost_fn, max_len: int) -> tuple[float, list[tuple[int, int]]]:
    """Min-cost tiling of ``[0, n)``. ``cost_fn(j, i)`` gives the cost of segment ``[j, i)``, or
    ``None`` if it is not a piece. Returns ``(total_cost, spans)`` with the chosen ``(j, i)`` in
    order. Callers guarantee a tiling exists by supplying a length-1 floor. Ties break on strict
    ``<``, towards the leftmost start and therefore the longest final segment, which makes the
    result deterministic."""
    INF = float("inf")
    best = [0.0] + [INF] * n
    par = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(max(0, i - max_len), i):
            c = cost_fn(j, i)
            if c is not None and best[j] + c < best[i]:
                best[i] = best[j] + c
                par[i] = j
    spans, i = [], n
    while i > 0:
        j = par[i]
        spans.append((j, i))
        i = j
    return best[n], spans[::-1]


class ReverseTrie:
    """Vocabulary index for the stream DP: pieces stored backwards, since the DP ends a tile at
    each position and scans candidate starts right to left."""

    _END = None

    def __init__(self, pieces) -> None:
        self.root = {}
        for piece in pieces:
            node = self.root
            for ch in reversed(piece):
                node = node.setdefault(ch, {})
            node[self._END] = None


def min_vocab_tile(text: str, trie: ReverseTrie, unit_cost) -> tuple[int, list[tuple[int, int]]]:
    """Min-cost tiling over a cost-1 vocabulary plus a guaranteed one-character floor.

    The specialized form of :func:`min_tile`: the trie visits only prefixes that can still become
    a piece, instead of probing every substring up to the longest piece (128 for v3).
    """
    best = [0] * (len(text) + 1)
    par = [0] * (len(text) + 1)
    root = trie.root
    terminal = trie._END
    for end in range(1, len(text) + 1):
        # The guaranteed one-character edge: the vocabulary spelling if it is a piece, else the
        # byte floor.
        start = end - 1
        node = root.get(text[start])
        best[end] = best[start] + (1 if node is not None and terminal in node
                                   else unit_cost(start))
        par[end] = start

        if node is None:
            continue
        for start in range(end - 2, -1, -1):
            node = node.get(text[start])
            if node is None:
                break
            if terminal in node:
                candidate = best[start] + 1
                # Starts decrease through the traversal, so replacing on a tie retains min_tile's
                # longest-final-piece tie order.
                if candidate <= best[end]:
                    best[end] = candidate
                    par[end] = start

    spans, end = [], len(text)
    while end > 0:
        start = par[end]
        spans.append((start, end))
        end = start
    return best[-1], spans[::-1]


class ByteFloor:
    """What a codepoint costs when no piece covers it: a min-cost tiling of its UTF-8 bytes over
    the partial byte-prefix tokens, every single byte costing 1."""

    def __init__(self, byte_tokens, unit_chars=()) -> None:
        # Membership is all that is needed, since every token costs 1. ``unit_chars`` are the
        # cost-1 whole codepoints from the piece vocabulary.
        self.tokens = set(byte_tokens) | {c.encode().hex() for c in unit_chars}
        self.max_len = max((len(k) // 2 for k in self.tokens), default=1)
        self._chunks: dict[bytes, list[bytes]] = {}

    def chunks(self, bs: bytes) -> list[bytes]:
        """The chosen byte segments, one per token. Memoized per byte string."""
        hit = self._chunks.get(bs)
        if hit is None:
            def cost_fn(j: int, i: int) -> int | None:
                return 1 if (i - j == 1 or bs[j:i].hex() in self.tokens) else None

            _, spans = min_tile(len(bs), cost_fn, self.max_len)
            hit = self._chunks[bs] = [bs[j:i] for j, i in spans]
        return hit

    def cost_bytes(self, bs: bytes) -> int:
        """One token per chunk."""
        return len(self.chunks(bs))

    def cost_char(self, c: str) -> int:
        """Isolated codepoint cost via the byte floor."""
        return self.cost_bytes(c.encode()) if self.tokens else len(c.encode())


# ---- tiling the marked stream ---------------------------------------------------------------


def glued_contraction(cn: str) -> str:
    """Add the closing marker used for a contraction suffix in the marked stream.

    The apostrophe supplies the opening boundary, so there is no ⟨bow⟩.
    """
    return cn + EOW_G


def build_vocab(pieces, tokens: dict) -> frozenset[str]:
    """The tiling vocabulary: every parsed piece and the glued contraction spelling.

    The structural markers are not added here: they live in the vocabulary file's `markers` group,
    which is the one place that decides a marker costs one token.
    """
    vocab = set(pieces)
    # The file stores `'t`, the encoder writes `'t⟨eow⟩` (see `glued_contraction`).
    vocab.update(glued_contraction(cn) for cn in tokens["contractions"])
    return frozenset(vocab)


def char_cost(model, ch: str) -> int:
    """One codepoint standing alone: 1 if it is itself a token, else its byte-floor tiling.
    The cache avoids repricing repeated characters in long runs."""
    ch = ESCAPED_MARKER_LITERALS.get(ch, ch)
    cache = model._char_cost_cache
    hit = cache.get(ch)
    if hit is None:
        hit = cache[ch] = 1 if ch in model.unit_pieces else model.bytes.cost_char(ch)
    return hit


def frame_tail(n: int, model) -> list[str]:
    """What a content-final run of ``n`` frame-absorbed characters costs beyond the frame's own
    trailing token. Ladder families only; on v5 trailing whitespace is simply free.

    The frame appends ⏎⏎ after the content and one token can span into it, so the run the
    tokenizer sees is ``n + 2`` newlines, of which the frame already pays for one token. The cost
    is therefore not monotonic in ``n`` (28 trailing newlines are free, 29 cost one). Exact on all
    40 recorded rows; beyond 40 it rests on the vocabulary's newline ladder being complete.
    """
    if n == 0 or model.frame_tail != "ladder":
        return []
    run = "\n" * (n + 2)

    _total, spans = min_vocab_tile(run, model.trie, lambda _at: 1)
    return [run[j:i] for j, i in spans][:-1]      # the last token is the frame's own ⏎⏎


def tile(text: str, model) -> tuple[int, list[str | bytes]]:
    """One min-cost tiling of the marked stream. Returns ``(cost, tokens)``.

    Tokens are internal-form: ``str`` for a vocabulary piece or marker, ``bytes`` for a
    sub-character chunk. ``len(tokens) == cost``.
    """
    if model.frame_tail == "ladder":
        norm = nfc(text, fold_quotes=model.fold_quotes)
        n_tail = len(norm) - len(norm.rstrip(model.frame_strip))
    else:
        # The frame absorbs raw ASCII whitespace, so strip before NFC: `nfc` folds NBSP etc. to
        # U+0020, and those are not free at the end (`'a\xa0'` costs one more than `'a'`).
        norm = nfc(text.rstrip(model.frame_strip), fold_quotes=model.fold_quotes)
        n_tail = 0
    s = stream_norm(norm, model, raw_head_space=raw_head_space(text))
    tail = frame_tail(n_tail, model)
    if not s:
        return len(tail), list(tail)
    pieces = model.vocab

    def unit_floor(j: int) -> int:
        """One character where no piece covers it: a marker is a token, anything else falls to the
        byte floor."""
        ch = s[j]
        if ch in MARKER_GLYPHS:
            return 1
        return char_cost(model, ch)

    total, spans = min_vocab_tile(s, model.trie, unit_floor)
    # A span that fell to the byte floor may cost more than one token (a 4-byte letter with no
    # piece costs 4) and must expand into that many, or len(tokenize(x)) stops being the count.
    out: list[str | bytes] = []
    for j, i in spans:
        seg = s[j:i]
        if seg in pieces or unit_floor(j) == 1:
            out.append(seg)
        else:
            literal = ESCAPED_MARKER_LITERALS.get(seg, seg)
            out.extend(model.bytes.chunks(literal.encode()))
    assert len(out) == int(total), (len(out), int(total))
    out.extend(tail)
    return int(total) + len(tail), out
