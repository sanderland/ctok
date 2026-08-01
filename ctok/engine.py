"""The min-cost tiling: one DP, applied at two scales.

    min_tile        the segmentation DP itself — knows nothing about text, markers or Claude
    ByteFloor       that DP over a codepoint's UTF-8 bytes, for characters no piece covers
    tile            that DP over the marked stream, for the count

The marker atoms are in the vocabulary as cost-1 tokens, so a marker no piece absorbs needs no rule:
it tiles as itself. That is what a boundary "junction charge" always was. The count is the number of
tiles.
"""

from __future__ import annotations

from .constants import EOW_G, MARKER_GLYPHS
from .normalize import nfc, stream_norm
from .notation import parse_marked


def min_tile(n: int, cost_fn, max_len: int) -> tuple[float, list[tuple[int, int]]]:
    """Min-cost tiling of ``[0, n)``. ``cost_fn(j, i)`` gives the cost of segment ``[j, i)``, or
    ``None`` if it is not a piece. Returns ``(total_cost, spans)`` with the chosen ``(j, i)`` in
    order. Callers guarantee a tiling exists by supplying a length-1 floor. Ties break on strict
    ``<``, i.e. towards the leftmost/shortest final segment, which makes the result deterministic."""
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


class ByteFloor:
    """What a codepoint costs when no piece covers it: a min-cost tiling of its UTF-8 bytes over the
    partial byte-prefix tokens, every single byte costing 1."""

    def __init__(self, byte_tokens, unit_chars=()) -> None:
        # Membership is all that is needed, since every token costs 1. ``unit_chars`` are the cost-1
        # WHOLE codepoints from the piece vocabulary, folded in so an uncovered char still prices 1.
        self.tokens = set(byte_tokens) | {c.encode().hex() for c in unit_chars}
        self.max_len = max((len(k) // 2 for k in self.tokens), default=1)
        self._chunks: dict[bytes, list[bytes]] = {}

    def chunks(self, bs: bytes) -> list[bytes]:
        """The chosen byte segments, one per token — the floor's single result, from which the cost
        is just the length. One tiling per distinct byte string: the same character recurs thousands
        of times in a CJK run, and asking for its cost and its chunks must not tile it twice."""
        hit = self._chunks.get(bs)
        if hit is None:
            def cost_fn(j: int, i: int) -> int | None:
                return 1 if (i - j == 1 or bs[j:i].hex() in self.tokens) else None

            _, spans = min_tile(len(bs), cost_fn, self.max_len)
            hit = self._chunks[bs] = [bs[j:i] for j, i in spans]
        return hit

    def cost_bytes(self, bs: bytes) -> int:
        """One token per chunk, so the count IS the chunk count — structurally, not by two DPs
        agreeing."""
        return len(self.chunks(bs))

    def cost_char(self, c: str) -> int:
        """Isolated codepoint cost via the byte floor."""
        return self.cost_bytes(c.encode()) if self.tokens else len(c.encode())


# ---- tiling the marked stream ---------------------------------------------------------------


def glued_contraction(cn: str) -> str:
    """A contraction suffix in the spelling the marked stream uses: `'t` → `'t⟨eow⟩`.

    No ⟨bow⟩: the apostrophe IS the word's opening boundary, and `normalize._contraction_seam`
    writes the stream that way."""
    return cn + EOW_G


def build_vocab(pieces, tokens: dict) -> tuple[frozenset[str], int]:
    """The tiling vocabulary: every piece, the marker atoms and the glued contraction spelling.
    Returns it with the longest piece length, the DP's window."""
    vocab = {parse_marked(p) for p in pieces}
    vocab.update(MARKER_GLYPHS)
    # A contraction suffix needs no encoder rule: the normal rewrites already produce
    # `⟨bow⟩don⟨eow⟩'⟨bow⟩t⟨eow⟩`, so the suffix arrives in `pieces` already spelled that way. Only
    # the glued form, `it'sX`, has to be added here.
    vocab.update(glued_contraction(cn) for cn in tokens["contractions"])
    return frozenset(vocab), max((len(p) for p in vocab), default=1)


def char_cost(model, ch: str) -> int:
    """The cost of one codepoint standing alone: 1 if the character is itself a token, else its
    byte-floor tiling. Every character has this fallback; HARD is merely where the vocabulary
    usually runs out. Memoized — a long CJK run asks the same question thousands of times."""
    cache = model._char_cost_cache
    hit = cache.get(ch)
    if hit is None:
        hit = cache[ch] = 1 if ch in model.unit_pieces else model.bytes.cost_char(ch)
    return hit


def frame_tail(n: int, model) -> list[str]:
    """What a content-final run of ``n`` newlines costs beyond the frame's own trailing token.

    The message frame appends ⏎⏎ after the content, and ONE token can span content into it. So the
    run the tokenizer actually sees is ``n + 2`` newlines, tiled over the newline-run vocabulary,
    of which the frame already pays for one token — ``stream`` is right to drop the run, but not to
    call it free.

    That is why the cost is not monotonic in ``n``: up to 28 trailing newlines cost nothing (30 is
    a single token), 29 costs one, 30 and 31 are free again (32 and 33 are single tokens), and 38
    is free (40 is). Live-exact on all 40 recorded ``a`` + ``n`` newline rows, n = 1…40. Beyond 40
    the prediction rests on the vocabulary's sampled ladder (48, 64, 96, 128) being complete.
    """
    if n == 0:
        return []
    run = "\n" * (n + 2)

    def cost_fn(j: int, i: int) -> int | None:
        return 1 if (i - j == 1 or run[j:i] in model.vocab) else None

    _total, spans = min_tile(len(run), cost_fn, model.max_piece_len)
    return [run[j:i] for j, i in spans][:-1]      # the last token is the frame's own ⏎⏎


def tile(text: str, model) -> tuple[int, list[str | bytes]]:
    """One min-cost tiling of the marked stream. Returns ``(cost, tokens)``.

    Tokens are internal-form: a ``str`` for a vocabulary piece or a marker, and ``bytes`` for a
    sub-character chunk of a codepoint the vocabulary does not cover. ``len(tokens) == cost``.
    """
    norm = nfc(text, fold_quotes=model.fold_quotes)
    s = stream_norm(norm, model)
    tail = frame_tail(len(norm) - len(norm.rstrip("\n")), model)
    if not s:
        return len(tail), list(tail)
    pieces = model.vocab

    def unit_floor(j: int) -> int:
        """What one character costs where no piece covers it — a marker is a token, anything else
        falls to the byte floor. Wider uncovered spans are simply unavailable to the DP."""
        ch = s[j]
        return 1 if ch in MARKER_GLYPHS else char_cost(model, ch)

    def cost_fn(j: int, i: int) -> int | None:
        if s[j:i] in pieces:
            return 1
        return unit_floor(j) if i - j == 1 else None

    total, spans = min_tile(len(s), cost_fn, model.max_piece_len)
    # A span the vocabulary covers is one token, but a span that fell to the byte floor may cost
    # more than one — a 4-byte letter with no piece costs 4 — so it must expand into that many
    # tokens, or len(tokenize(x)) stops being the count.
    out: list[str | bytes] = []
    for j, i in spans:
        seg = s[j:i]
        if seg in pieces or unit_floor(j) == 1:
            out.append(seg)
        else:
            out.extend(model.bytes.chunks(seg.encode()))
    assert len(out) == int(total), (len(out), int(total))
    out.extend(tail)
    return int(total) + len(tail), out
