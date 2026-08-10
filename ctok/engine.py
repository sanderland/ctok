"""The min-cost tiling: one DP, applied at two scales.

    min_tile        the segmentation DP itself — knows nothing about text, markers or Claude
    ByteFloor       that DP over a codepoint's UTF-8 bytes, for characters no piece covers
    tile            that DP over the marked stream, for the count

The marker atoms are in the vocabulary as cost-1 tokens, so a marker no piece absorbs needs no rule:
it tiles as itself. That is what a boundary "junction charge" always was. The count is the number of
tiles.
"""

from __future__ import annotations

from .constants import BOW_G, CAPS_G, EOW_G, MARKER_GLYPHS, SHIFT_G
from .normalize import nfc, stream_plan, stripped_head
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
    """The tiling vocabulary: every piece and the glued contraction spelling. Returns it with the
    longest piece length, the DP's window.

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

    def cost_fn(j: int, i: int) -> int | None:
        return 1 if (i - j == 1 or run[j:i] in model.vocab) else None

    _total, spans = min_tile(len(run), cost_fn, model.max_piece_len)
    return [run[j:i] for j, i in spans][:-1]      # the last token is the frame's own ⏎⏎


def _dotted_host_blocked(seg: str) -> bool:
    """Is ``seg`` a tile after which the dotted capital İ byte-prices, in İ's contextual spot —
    a marker-carrying tile ending in an uppercase ASCII letter?

    Measured 2026-08-09, cached grid. Word-final İ after such a tile pays its two bytes: `Bİ Dİ
    Kİ Lİ Rİ Sİ Tİ` = 15 each and `x Aİ x` `x Eİ x` `x Sİ x` = 17, where the unit piece would
    read one less. So does İ before a LOWERCASE ASCII letter: `Dİs` = 15, `x Dİl x` = 17. Every
    other neighbourhood keeps the piece at 1: mid-word before an uppercase letter (`AİD` `BİR`
    `DİN` `x DİREKTOR x` `TƏSDİQLƏMİSİNİZ` exact), word-final after a lowercase host (`aİ` `xİ`
    `x nİ x` `x dİ x` exact), after a bare uppercase mid-word tile (`RPİ` = 15 exact), after
    `⟨bow⟩İ` itself (`x İİ x` = 16 exact — İ is uppercase but not ASCII), and after a markerless
    multi-letter tile (`xalqlarınİ` `x novunİ x` exact). `x Hüseynovunİ x` = 22 stays one under
    and is reported in LIMITS.md: `(un)` is the same tile `x novunİ x` prices the piece after, so
    no tile rule separates them out of our vocabulary.
    """
    return seg[0] in (BOW_G, SHIFT_G, CAPS_G) and seg[-1].isascii() and seg[-1].isupper()


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
    s, floor_positions = stream_plan(norm, model, head_stripped=stripped_head(text))
    tail = frame_tail(n_tail, model)
    if not s:
        return len(tail), list(tail)
    pieces = model.vocab
    floor_prefix = [0] * (len(s) + 1)
    for at in floor_positions:
        floor_prefix[at + 1] = 1
    for i in range(len(s)):
        floor_prefix[i + 1] += floor_prefix[i]
    # The dotted capital İ, in its one measured byte-pricing spot: word-final or followed by an
    # ASCII lowercase letter, and not word-initial (`⟨bow⟩İ` covers that position as a piece).
    # There its unit piece prices 1 only after a tile `_dotted_host_tile` admits; after a
    # marker-carrying tile ending in an uppercase ASCII letter it pays its two UTF-8 bytes.
    ctx_dotted = frozenset(
        j for j, ch in enumerate(s)
        if ch == "İ" and 0 < j < len(s) - 1 and s[j - 1] not in MARKER_GLYPHS
        and j not in floor_positions
        and (s[j + 1] == EOW_G or "a" <= s[j + 1] <= "z"))
    ctx_prefix = [0] * (len(s) + 1)
    for at in ctx_dotted:
        ctx_prefix[at + 1] = 1
    for i in range(len(s)):
        ctx_prefix[i + 1] += ctx_prefix[i]

    def unit_floor(j: int) -> int:
        """What one character costs where no piece covers it — a marker is a token, anything else
        falls to the byte floor. Wider uncovered spans are simply unavailable to the DP."""
        ch = s[j]
        # A marker the vocabulary somehow does not hold still costs one token — it is structure, not
        # text, and the byte floor would price its three UTF-8 bytes. The `markers` group means this
        # never fires in practice; it stays as the floor under a file that lost one.
        if ch in MARKER_GLYPHS:
            return 1
        if j in floor_positions:
            return model.raw_bytes.cost_char(ch)
        return char_cost(model, ch)

    def cost_fn(j: int, i: int) -> int | None:
        # A forced-floor codepoint is outside the context where ordinary vocabulary pieces were
        # measured. No piece may span across it; its one-character raw-byte tiling is the only edge
        # offered to the DP.
        if floor_prefix[i] != floor_prefix[j]:
            return unit_floor(j) if i - j == 1 and j in floor_positions else None
        if ctx_prefix[i] != ctx_prefix[j]:
            # A span touching the tile-contextual İ. Alone, the character pays its raw bytes; the
            # only way to its one-token piece is a combined edge [host tile][piece], which costs
            # the pair of tokens it is. No ordinary piece may span the position.
            if i - j == 1:
                return model.raw_bytes.cost_char(s[j])
            last = i - 1
            if ctx_prefix[last] != ctx_prefix[j] or floor_prefix[last] != floor_prefix[j]:
                return None
            host = s[j:last]
            # Any tile may precede it at price 1 except the measured marker-carrying-uppercase
            # shape (`_dotted_host_blocked`).
            if _dotted_host_blocked(host):
                return None
            host_cost = 1 if host in pieces else (unit_floor(j) if last - j == 1 else None)
            return None if host_cost is None else host_cost + 1
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
        if j in ctx_dotted:
            # A contextual position that no eligible host tile precedes: its raw-byte chunks.
            out.extend(model.raw_bytes.chunks(seg.encode()))
        elif i - 1 in ctx_dotted and i - j > 1:
            # A combined [host tile][piece] edge, split where the DP priced it. The host is a
            # piece or a single character, which may itself expand to byte chunks.
            host = seg[:-1]
            if host in pieces or unit_floor(j) == 1:
                out.append(host)
            else:
                out.extend(model.bytes.chunks(host.encode()))
            out.append(seg[-1])
        elif j not in floor_positions and (seg in pieces or unit_floor(j) == 1):
            out.append(seg)
        else:
            floor = model.raw_bytes if j in floor_positions else model.bytes
            chunks = floor.chunks(seg.encode())
            out.extend(chunks if len(chunks) > 1 else [seg])
    assert len(out) == int(total), (len(out), int(total))
    out.extend(tail)
    return int(total) + len(tail), out
