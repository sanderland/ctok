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

Which one applies is a property of the piece: a piece's marked form says where in a word it lives
(``⟨bow⟩p⟨eow⟩`` whole, ``⟨bow⟩p`` prefix, ``p⟨eow⟩`` suffix, bare ``p`` interior), and a probe that
puts it anywhere else measures a different thing. `verify` re-checks that placement against the
encoder rather than trusting the recorded kind.
"""

from __future__ import annotations

from .constants import BOW_G, CAPS_G, EOW_G, MARKER_GLYPHS, SHIFT_G
from .normalize import nfc, stream_norm

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
    if set(FIELDS) - set(witness):
        return f"missing {sorted(set(FIELDS) - set(witness))}"
    templates = meta["witness"]["templates"]
    if witness["kind"] == "prefix":
        return _verify_prefix(key, witness, meta, model)
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
        # EXCEPT a killer-final suffix piece whose probe is its own bare message: the stream is
        # exactly ⟨bow⟩ + the piece, no other instrument reaches a mark-bearing piece at all, and
        # the reading is the region's — the same attribution ambiguity every ヲ cell carries. Any
        # OTHER left context keeps the veto, and so does a plain-letter suffix piece, whose word
        # form really would be measured instead (that mistake refuted 2,317 good prefixes).
        from .normalize import is_killer
        body = surface(key)
        if not (pos == "eow" and left == BOW_G and s == left + key
                and body and is_killer(body[-1])):
            return False
    return True
