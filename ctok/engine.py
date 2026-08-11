"""The min-cost tiling, with the marked-stream vocabulary indexed by a reverse trie.

    min_tile        generic segmentation DP for tiny byte strings
    min_vocab_tile  the same recurrence, visiting only vocabulary edges through the trie
    ByteFloor       byte tiling for characters no piece covers
    tile            marked-stream tiling for the count

The marker atoms are in the vocabulary as cost-1 tokens, so a marker no piece absorbs needs no rule:
it tiles as itself. That is what a boundary "junction charge" always was. The count is the number of
tiles.
"""

from __future__ import annotations

from .constants import EOW_G, MARKER_GLYPHS
from .normalize import nfc, stream_norm, stripped_head
from .notation import parse_marked


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
    """Vocabulary index for the stream DP.

    The DP ends a tile at each stream position, so storing pieces backwards lets it stop as soon as
    the preceding characters cease to match any piece. ``starts`` returns shortest matches first;
    the DP reverses that small list to retain ``min_tile``'s existing longest-final-piece tie order.
    """

    _END = None

    def __init__(self, pieces) -> None:
        self.root = {}
        for piece in pieces:
            node = self.root
            for ch in reversed(piece):
                node = node.setdefault(ch, {})
            node[self._END] = None

    def starts(self, text: str, end: int) -> list[int]:
        """Starts of vocabulary pieces ending at ``end``, shortest piece first."""
        node = self.root
        found = []
        for start in range(end - 1, -1, -1):
            node = node.get(text[start])
            if node is None:
                break
            if self._END in node:
                found.append(start)
        return found


def min_vocab_tile(text: str, trie: ReverseTrie, unit_cost) -> tuple[float, list[tuple[int, int]]]:
    """Min-cost tiling over a cost-1 vocabulary plus a guaranteed one-character floor.

    This is the marked stream's specialized form of :func:`min_tile`. The generic DP asks about
    every substring up to the longest vocabulary piece. One 128-newline piece therefore made every
    v3 character pay for 128 dictionary probes. The trie visits only prefixes that can still become
    a piece and creates no candidate substrings.
    """
    INF = float("inf")
    best = [0.0] + [INF] * len(text)
    par = [0] * (len(text) + 1)
    for end in range(1, len(text) + 1):
        # min_tile visits starts from left to right. Reverse the trie's shortest-first results so a
        # tied count keeps the same spans and public token list as before this index existed.
        starts = trie.starts(text, end)
        for start in reversed(starts):
            candidate = best[start] + 1
            if candidate < best[end]:
                best[end] = candidate
                par[end] = start

        # Every character has a floor. A one-character vocabulary edge already supplied the same
        # cost, so avoid pricing that floor twice.
        if not starts or starts[0] != end - 1:
            start = end - 1
            candidate = best[start] + unit_cost(start)
            if candidate < best[end]:
                best[end] = candidate
                par[end] = start

    spans, end = [], len(text)
    while end > 0:
        start = par[end]
        spans.append((start, end))
        end = start
    return best[-1], spans[::-1]


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


def build_vocab(pieces, tokens: dict) -> frozenset[str]:
    """The tiling vocabulary: every piece and the glued contraction spelling.

    The structural markers used to be added here as well, which made three places that decided a
    marker costs one token: this line, `tile`'s unit floor below, and the two of the four that the
    vocabulary file happened to list. They live in the file now, in a `markers` group of their own —
    a reader of `pieces.json` sees the whole tiling vocabulary rather than most of it.
    """
    vocab = {parse_marked(p) for p in pieces}
    # The contraction suffix, in the spelling the stream uses. The file stores `'t` and the encoder
    # writes `'t⟨eow⟩` — `⟨bow⟩don⟨eow⟩'t⟨eow⟩`, with no ⟨bow⟩ after the apostrophe, because the
    # apostrophe IS that word's opening boundary (`normalize._contraction_seam`).
    #
    # That is measured, not a spelling convention. The increment a contraction adds over its left
    # context alone is 1 after a letter, a digit or a space, and 2 after punctuation — uniformly
    # across all four v4.7 suffixes, all seven v3 suffixes and `}` `.` `)` in both families
    # (2026-08-05). The step is the boundary token, appearing exactly where the apostrophe does not
    # supply one. Marking every wordy span uniformly instead would have to reproduce that step out
    # of the vocabulary, which moves the special case rather than removing it.
    vocab.update(glued_contraction(cn) for cn in tokens["contractions"])
    return frozenset(vocab)


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
    """What a content-final run of ``n`` frame-absorbed characters costs beyond the frame's own
    trailing token.

    Only where the family's frame ends in that ⏎⏎ tail (``frame_tail == "ladder"``). v5 measured
    the other shape — trailing whitespace of every kind is free there, spaces and tabs included,
    and a 29-newline run that costs v4.7 a token costs it nothing — so the run is simply gone.

    The message frame appends ⏎⏎ after the content, and ONE token can span content into it. So the
    run the tokenizer actually sees is ``n + 2`` newlines, tiled over the newline-run vocabulary,
    of which the frame already pays for one token — ``stream`` is right to drop the run, but not to
    call it free.

    That is why the cost is not monotonic in ``n``: up to 28 trailing newlines cost nothing (30 is
    a single token), 29 costs one, 30 and 31 are free again (32 and 33 are single tokens), and 38
    is free (40 is). Live-exact on all 40 recorded ``a`` + ``n`` newline rows, n = 1…40. Beyond 40
    the prediction rests on the vocabulary's sampled ladder (48, 64, 96, 128) being complete.
    """
    if n == 0 or model.frame_tail != "ladder":
        return []
    run = "\n" * (n + 2)

    _total, spans = min_vocab_tile(run, model.trie, lambda _at: 1)
    return [run[j:i] for j, i in spans][:-1]      # the last token is the frame's own ⏎⏎


def tile(text: str, model) -> tuple[int, list[str | bytes]]:
    """One min-cost tiling of the marked stream. Returns ``(cost, tokens)``.

    Tokens are internal-form: a ``str`` for a vocabulary piece or a marker, and ``bytes`` for a
    sub-character chunk of a codepoint the vocabulary does not cover. ``len(tokens) == cost``.
    """
    if model.frame_tail == "ladder":
        norm = nfc(text, fold_quotes=model.fold_quotes)
        n_tail = len(norm) - len(norm.rstrip(model.frame_strip))
    else:
        # The frame absorbs RAW ASCII whitespace, which is why this strip runs before NFC rather
        # than after it: `nfc` folds NBSP and the other space separators to U+0020, and those do
        # NOT come free at the end — `'a\xa0'` costs one token more than `'a'`, `'a '` costs the
        # same. Stripping the folded text would hand back that token and under-count 363 documents
        # of the Rosetta corpus, which is how this was found.
        norm = nfc(text.rstrip(model.frame_strip), fold_quotes=model.fold_quotes)
        n_tail = 0
    s = stream_norm(norm, model, head_stripped=stripped_head(text))
    tail = frame_tail(n_tail, model)
    if not s:
        return len(tail), list(tail)
    pieces = model.vocab

    def unit_floor(j: int) -> int:
        """What one character costs where no piece covers it — a marker is a token, anything else
        falls to the byte floor. Wider uncovered spans are simply unavailable to the DP."""
        ch = s[j]
        # A marker the vocabulary somehow does not hold still costs one token — it is structure, not
        # text, and the byte floor would price its three UTF-8 bytes. The `markers` group means this
        # never fires in practice; it stays as the floor under a file that lost one.
        if ch in MARKER_GLYPHS:
            return 1
        return char_cost(model, ch)

    total, spans = min_vocab_tile(s, model.trie, unit_floor)
    # A span the vocabulary covers is one token, but a span that fell to the byte floor may cost
    # more than one — a 4-byte letter with no piece costs 4 — so it must expand into that many
    # tokens, or len(tokenize(x)) stops being the count.
    out: list[str | bytes] = []
    for j, i in spans:
        seg = s[j:i]
        if seg in pieces or unit_floor(j) == 1:
            out.append(seg)
        else:
            chunks = model.bytes.chunks(seg.encode())
            out.extend(chunks if len(chunks) > 1 else [seg])
    assert len(out) == int(total), (len(out), int(total))
    out.extend(tail)
    return int(total) + len(tail), out
