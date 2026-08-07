"""What a piece rests on: the probe that pins it at exactly one token.

Every piece in ``data/pieces_*.json`` carries a witness — the probe text, the raw ``count_tokens``
value it returned, and which template it is — and this module is how a reader checks one. The
arithmetic ships WITH the data (``meta.witness``) rather than being restated here, so the file is
self-describing and a reader never has to know what the mining rig believed:

    cost = raw − BASE + 1 − overhead        is_token ⟺ cost == 1

``BASE`` is ``count_tokens`` on the one-character message ``"a"`` for that family — 8 on v3, 12 on
v4.7, 7 on v5 — so it is a known single token measured through the same frame, and every template's
``overhead`` is calibrated against it. That is the whole reason the surrounding material never has to
be measured on its own: the anchors are not summed, they are subtracted as a template constant.

The templates are the mining repo's `PROBES.md` inventory, not an invention of this file:

    raw         X                               the span IS the message
    word        .X.                             a wordy span between Latin anchors
    bow/eow/mid .Xヲ. / .ヲX. / .ヲXヲ.            the ヲ separator grid, by position
    cased_*     XController / československX    CamelCase scaffolds, for material with a capital
    char        aXa                             one non-ASCII codepoint's intrinsic cost
    glued       aXb                             an ASCII digit piece

Some own-script pieces replace more than two fallback tiles, so deleting one changes a natural
probe by more than one token and the direct ablation instrument cannot isolate it.  A ``fitness``
witness records two or more exact natural probes and checks the next strongest membership claim:
after deleting the piece, enumerate every single stream span whose addition restores each count.
The claimed piece must be the unique candidate common to every row.  This is deliberately a
fewest-new-tokens proof; ambiguity remains a gap rather than being broken by corpus frequency.

Which one applies is a property of the piece: a piece's marked form says where in a word it lives
(``⟨bow⟩p⟨eow⟩`` whole, ``⟨bow⟩p`` prefix, ``p⟨eow⟩`` suffix, bare ``p`` interior), and a probe that
puts it anywhere else measures a different thing. `verify` re-checks that placement against the
encoder rather than trusting the recorded kind.
"""

from __future__ import annotations

import copy

from .constants import BOW_G, CAPS_G, EOW_G, MARKER_GLYPHS, SHIFT_G
from .normalize import nfc, stream_norm, stream_plan

# piece shape -> which position it occupies in a word, and so which templates can ask about it.
POSITIONS = {(True, True): "word", (True, False): "bow", (False, True): "eow", (False, False): "mid"}

# A witness record is these three fields. Everything else about it derives from `meta.witness`.
FIELDS = ("probe", "raw", "kind")


def surface(key: str) -> str:
    """The literal text a probe puts around ``key`` — markers dropped, case markers re-applied."""
    body = "".join(c for c in key if c not in MARKER_GLYPHS)
    if SHIFT_G in key:
        return body[:1].upper() + body[1:]
    if CAPS_G in key:
        return body.upper()
    return body


def position(key: str) -> str:
    """Where in a word this piece lives: ``word``, ``bow``, ``eow`` or ``mid``.

    The CASE markers come first and the boundary marker second — a capitalized whole word is
    ``⟨shift⟩⟨bow⟩nicolas⟨eow⟩`` — so reading the first character alone calls it a suffix piece and
    sends it to a probe that measures the wrong end of a word.
    """
    body = key.lstrip(SHIFT_G + CAPS_G)
    return POSITIONS[(body.startswith(BOW_G), body.endswith(EOW_G))]


def cost(raw: int, base: int, overhead: int) -> int:
    """The piece's own cost, from the raw count of its probe. One means it is a token."""
    return raw - base + 1 - overhead


def verify(key: str, witness: dict, meta: dict, model=None) -> str | None:
    """``None`` if the witness holds, else why it does not.

    Three questions, and the third is the one a stale file fails: does the probe text match the
    template it names, does the arithmetic come out at exactly one token, and — when a ``model`` is
    given — does the encoder still write the piece into that probe's stream where the template says
    it stands? A template whose text no longer places the piece is measuring something else, and no
    amount of correct arithmetic on it means anything.
    """
    if witness.get("kind") == "fitness":
        return _verify_fitness(key, witness, model)
    if set(FIELDS) - set(witness):
        return f"missing {sorted(set(FIELDS) - set(witness))}"
    templates = meta["witness"]["templates"]
    if witness["kind"] == "prefix":
        return _verify_prefix(key, witness, meta, model)
    if witness["kind"] == "ownscript":
        return _verify_ownscript(key, witness, model)
    if witness["kind"] not in templates:
        return f"unknown template {witness['kind']!r}"
    template, overhead = templates[witness["kind"]]
    if template.format(surface(key)) != witness["probe"]:
        return f"probe is not {witness['kind']} of this piece"
    got = cost(witness["raw"], meta["witness"]["base"], overhead)
    if got != 1:
        return f"cost {got}, not 1 — the probe refutes the piece"
    # A contraction's stored spelling is not its tiling spelling: the file says `'s` and the encoder
    # writes `'s⟨eow⟩`, so the placement check has to ask about the glued form.
    if witness["kind"] == "contraction":
        from .engine import glued_contraction
        key = glued_contraction(key)
    if model is not None and not places(key, witness["probe"], model):
        return "the encoder no longer writes this piece into that probe"
    return None


def _verify_ownscript(key: str, witness: dict, model) -> str | None:
    """Verify a natural-text ablation witness for a piece no synthetic frame can isolate.

    Combining-mark pieces cannot be moved onto the Latin/Katakana witness scaffolds: the host
    becomes the mark's base and the probe asks about a different cluster.  An own-script witness
    leaves the piece in a natural word and asks the narrower, reproducible question instead: the
    shipped vocabulary matches the recorded count, and removing only this piece costs one token.
    """
    if model is None:
        return None
    rows = [{k: witness[k] for k in ("probe", "raw", "without") if k in witness}]
    rows.extend(witness.get("corroborating", ()))
    if not rows or any(set(("probe", "raw", "without")) - set(row) for row in rows):
        return "ownscript witness is missing probe, raw or without"

    from .engine import ByteFloor, tile

    without = copy.copy(model)
    without.vocab = frozenset(set(model.vocab) - {key})
    without.max_piece_len = max(map(len, without.vocab), default=1)
    if len(key) == 1 and key not in MARKER_GLYPHS:
        without.unit_pieces = set(model.unit_pieces) - {key}
        without.bytes = ByteFloor(set(model.bytes.tokens) - {key.encode().hex()},
                                  without.unit_pieces)
        without._char_cost_cache = {}
    for row in rows:
        probe, raw = row["probe"], row["raw"]
        stream = stream_norm(nfc(probe, fold_quotes=model.fold_quotes), model)
        if key not in stream:
            return f"the encoder does not place this piece in {probe!r}"
        with_n = tile(probe, model)[0] + model.message_overhead
        without_n = tile(probe, without)[0] + model.message_overhead
        if with_n != raw:
            return f"the shipped vocabulary counts {probe!r} at {with_n}, not recorded {raw}"
        if without_n != row["without"]:
            return (f"ablating the piece counts {probe!r} at {without_n}, "
                    f"not recorded {row['without']}")
        if without_n != raw + 1:
            return f"ablating the piece changes {probe!r} by {without_n - raw}, not 1"
    return None


def _without_key(model, key: str):
    """A shallow model clone with one vocabulary key removed, including the unit-character floor."""
    from .engine import ByteFloor

    without = copy.copy(model)
    without.vocab = frozenset(set(model.vocab) - {key})
    without.max_piece_len = max(map(len, without.vocab), default=1)
    if len(key) == 1 and key not in MARKER_GLYPHS:
        without.unit_pieces = set(model.unit_pieces) - {key}
        without.bytes = ByteFloor(set(model.bytes.tokens) - {key.encode().hex()},
                                  without.unit_pieces)
        without._char_cost_cache = {}
    return without


def _with_key(model, key: str):
    """A shallow model clone with one vocabulary key added, for fitness-candidate verification."""
    from .engine import ByteFloor

    with_key = copy.copy(model)
    with_key.vocab = frozenset(set(model.vocab) | {key})
    with_key.max_piece_len = max(model.max_piece_len, len(key))
    if len(key) == 1 and key not in MARKER_GLYPHS:
        with_key.unit_pieces = set(model.unit_pieces) | {key}
        with_key.bytes = ByteFloor(model.bytes.tokens, with_key.unit_pieces)
        with_key._char_cost_cache = {}
    return with_key


def _fitness_candidates(model, probe: str, raw: int) -> set[str]:
    """Every one-piece vocabulary addition that makes ``probe`` reproduce ``raw``.

    Prefix and suffix costs identify candidate spans in quadratic time; the full tokenizer then
    verifies each survivor because adding a unit character also changes the byte floor everywhere
    that character occurs.
    """
    from .engine import char_cost, tile

    norm = nfc(probe, fold_quotes=model.fold_quotes)
    if norm.endswith("\n"):
        return set()                    # fitness rows intentionally avoid frame-tail arithmetic
    stream, floor_positions = stream_plan(norm, model)
    n = len(stream)
    floor_prefix = [0] * (n + 1)
    for at in floor_positions:
        floor_prefix[at + 1] = 1
    for i in range(n):
        floor_prefix[i + 1] += floor_prefix[i]

    def span_cost(j: int, i: int) -> int | None:
        if floor_prefix[i] != floor_prefix[j]:
            if i - j != 1 or j not in floor_positions:
                return None
            return model.raw_bytes.cost_char(stream[j])
        if stream[j:i] in model.vocab:
            return 1
        if i - j == 1:
            if stream[j] in MARKER_GLYPHS:
                return 1
            if j in floor_positions:
                return model.raw_bytes.cost_char(stream[j])
            return char_cost(model, stream[j])
        return None

    inf = float("inf")
    prefix = [0.0] + [inf] * n
    for i in range(1, n + 1):
        for j in range(max(0, i - model.max_piece_len), i):
            cost_ = span_cost(j, i)
            if cost_ is not None:
                prefix[i] = min(prefix[i], prefix[j] + cost_)
    suffix = [inf] * n + [0.0]
    for j in range(n - 1, -1, -1):
        for i in range(j + 1, min(n, j + model.max_piece_len) + 1):
            cost_ = span_cost(j, i)
            if cost_ is not None:
                suffix[j] = min(suffix[j], cost_ + suffix[i])

    target = raw - model.message_overhead
    possible = set()
    for i in range(n):
        for j in range(i + 1, n + 1):
            key = stream[i:j]
            if key in model.vocab or not any(c not in MARKER_GLYPHS for c in key):
                continue
            if prefix[i] + 1 + suffix[j] == target:
                possible.add(key)
    return {key for key in possible
            if tile(probe, _with_key(model, key))[0] + model.message_overhead == raw}


def _verify_fitness(key: str, witness: dict, model) -> str | None:
    """Verify that ``key`` is the unique common one-token explanation of natural probe rows."""
    if model is None:
        return None
    rows = witness.get("rows", ())
    if len(rows) < 2:
        return "fitness witness needs at least two independent rows"
    without = _without_key(model, key)
    from .engine import tile

    common = None
    for row in rows:
        if set(("probe", "raw", "without")) - set(row):
            return "fitness row is missing probe, raw or without"
        probe, raw = row["probe"], row["raw"]
        stream = stream_norm(nfc(probe, fold_quotes=model.fold_quotes), model)
        if key not in stream:
            return f"the encoder does not place this piece in {probe!r}"
        with_n = tile(probe, model)[0] + model.message_overhead
        without_n = tile(probe, without)[0] + model.message_overhead
        if with_n != raw:
            return f"the shipped vocabulary counts {probe!r} at {with_n}, not recorded {raw}"
        if without_n != row["without"]:
            return (f"ablating the piece counts {probe!r} at {without_n}, "
                    f"not recorded {row['without']}")
        if without_n <= raw:
            return f"ablating the piece does not make {probe!r} more expensive"
        if common is None:
            common = _fitness_candidates(without, probe, raw)
        else:
            # Only candidates surviving earlier rows can belong to the final intersection.  Testing
            # those directly avoids re-enumerating every span in long corroborating documents.
            common = {candidate for candidate in common if candidate in stream and
                      tile(probe, _with_key(without, candidate))[0] +
                      model.message_overhead == raw}
    if common != {key}:
        return f"common one-token explanations are {sorted(common or ())!r}, not this piece alone"
    return None


def _verify_prefix(prefix: str, witness: dict, meta: dict, model) -> str | None:
    """A byte prefix is not a token, so ``cost == 1`` is the wrong question. It makes a PREDICTION.

    The byte floor tiles a codepoint's UTF-8 over the prefixes, so carrying `e0a4` says every
    character opening with those bytes costs one token less than it otherwise would. The witness
    names a character and the count its probe returned; the prefix holds when the shipped floor
    reproduces that count, and earns its place when a floor without it does not.
    """
    if model is None:
        return None                                 # the check needs the byte floor
    from .engine import ByteFloor

    template, overhead = meta["witness"]["templates"]["char"]
    body = witness["probe"][1:-1]                   # `a{X}a`
    if template.format(body) != witness["probe"]:
        return f"probe is not the char template of {body!r}"
    want = cost(witness["raw"], meta["witness"]["base"], overhead)
    if model.bytes.cost_char(body) != want:
        return (f"the floor prices {body!r} at {model.bytes.cost_char(body)}, "
                f"the probe measured {want}")
    without = ByteFloor(set(model.bytes.tokens) - {prefix}, ())
    if without.cost_bytes(body.encode()) == want:
        return f"the floor reaches {body!r} without this prefix — it earns nothing"
    return None


def places(key: str, probe: str, model) -> bool:
    """Does the encoder write ``key`` into ``probe``'s marked stream, in its own position?

    A ``raw`` probe must stream to the piece and nothing else — the piece IS the message. Any other
    template surrounds it, so the piece must appear with its boundaries intact and material on the
    side its position claims. Computed from the encoder, never assumed: the message edges are
    family-scoped (v5 absorbs trailing whitespace and opens on no ⟨bow⟩ where v4.7 does neither),
    and a probe verified against the wrong family's frame is verified against nothing.
    """
    s = stream_norm(nfc(probe, fold_quotes=model.fold_quotes), model)
    if s == key:
        return True                     # the piece IS the whole content, markers and all
    at = s.find(key)
    if at < 0:
        return False
    pos, left, right = position(key), s[:at], s[at + len(key):]
    if pos == "word":
        return True                     # a whole word inside a longer stream is still a whole word
    # A prefix piece carries the word's opening and NOT its close, so a ⟨eow⟩ immediately after it
    # means the probe wrote the whole word — `⟨bow⟩ab` is not what `ab` alone measures, and reading
    # it as such refutes 2,317 perfectly good v4.7 prefixes. The mirror holds for a suffix piece.
    if pos in ("bow", "mid") and (not right or right.startswith(EOW_G)):
        return False
    if pos in ("eow", "mid") and (not left or left.endswith(BOW_G)):
        return False
    return True
