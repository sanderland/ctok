"""Checking witnesses: the probe that pins a piece at exactly one token.

Every piece in ``data/pieces_*.json`` carries a witness: the probe text, the raw ``count_tokens``
value it returned, and which template it is. The arithmetic ships with the data (``meta.witness``):

    cost = raw − BASE + 1 − overhead        is_token ⟺ cost == 1

``BASE`` is ``count_tokens`` on the one-character message ``"a"`` for that family (8 on v3, 12 on
v4.7, 7 on v4.8+), and every template's ``overhead`` is calibrated against it. Templates
(``meta.witness.templates``):

    raw         X                               the span is the message
    word        .X.                             a wordy span between Latin anchors
    bow/eow/mid .Xヲ. / .ヲX. / .ヲXヲ.            the ヲ separator grid, by position
    cased_*     XController / československX    CamelCase scaffolds, for material with a capital
    char        aXa                             one non-ASCII codepoint's intrinsic cost
    glued       aXb                             an ASCII digit piece

Which template applies is a property of the piece: its marked form says where in a word it lives
(``⟨bow⟩p⟨eow⟩`` whole, ``⟨bow⟩p`` prefix, ``p⟨eow⟩`` suffix, bare ``p`` interior), and a probe
that puts it anywhere else measures a different thing. `verify` re-checks that placement against
the encoder rather than trusting the recorded kind.
"""

from __future__ import annotations

from .constants import BOW_G, CAPS_G, EOW_G, MARKER_GLYPHS, SHIFT_G
from .normalize import nfc, stream_norm

# piece shape -> which position it occupies in a word, and so which templates can ask about it.
POSITIONS = {(True, True): "word", (True, False): "bow", (False, True): "eow", (False, False): "mid"}

# A witness record is these three fields. Everything else about it derives from `meta.witness`.
FIELDS = ("probe", "raw", "kind")


def surface(key: str) -> str:
    """The literal probe text for ``key``, without markers and with case reapplied."""
    body = "".join(c for c in key if c not in MARKER_GLYPHS)
    if SHIFT_G in key:
        return body[:1].upper() + body[1:]
    if CAPS_G in key:
        return body.upper()
    return body


def position(key: str) -> str:
    """Where in a word this piece lives: ``word``, ``bow``, ``eow`` or ``mid``. The case
    markers come first and the boundary marker second (``⟨shift⟩⟨bow⟩nicolas⟨eow⟩``), hence the
    lstrip.
    """
    body = key.lstrip(SHIFT_G + CAPS_G)
    return POSITIONS[(body.startswith(BOW_G), body.endswith(EOW_G))]


def cost(raw: int, base: int, overhead: int) -> int:
    """The piece's own cost, from the raw count of its probe. One means it is a token."""
    return raw - base + 1 - overhead


def verify(key: str, witness: dict, meta: dict, model=None) -> str | None:
    """``None`` if the witness holds, else why it does not.

    It checks the named template, the one-token arithmetic, and, when given a model, the piece's
    position in the encoded probe. A template that no longer places the piece measures something
    else.
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
        return f"cost {got}, not 1; the probe refutes the piece"
    # A contraction's stored spelling is not its tiling spelling: the file says `'s` and the encoder
    # writes `'s⟨eow⟩`, so the placement check has to ask about the glued form.
    if witness["kind"] == "contraction":
        from .engine import glued_contraction
        key = glued_contraction(key)
    if model is not None and not places(key, witness["probe"], model):
        return "the encoder no longer writes this piece into that probe"
    return None


def _verify_prefix(prefix: str, witness: dict, meta: dict, model) -> str | None:
    """A byte prefix is not a token; it makes a prediction. The byte floor tiles a codepoint's
    UTF-8 over the prefixes, so carrying `e0a4` says every character opening with those bytes
    costs one token less than it otherwise would. The prefix holds when the shipped floor
    reproduces the probe's count, and earns its place when a floor without it does not.
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
        return f"the floor reaches {body!r} without this prefix; it earns nothing"
    return None


def places(key: str, probe: str, model) -> bool:
    """Does the encoder write ``key`` into ``probe``'s marked stream, in its own position?

    A ``raw`` probe must stream to the piece and nothing else. Any other template surrounds it,
    so the piece must appear with its boundaries intact and material on the side its position
    claims. Computed from the encoder rather than assumed: the message edges are family-scoped,
    so a probe must be checked against its own family's frame.
    """
    s = stream_norm(nfc(probe, fold_quotes=model.fold_quotes), model)
    if s == key:
        return True                     # the piece is the whole content, markers and all
    at = s.find(key)
    if at < 0:
        return False
    pos, left, right = position(key), s[:at], s[at + len(key):]
    if pos == "word":
        return True                     # a whole word inside a longer stream is still a whole word
    # A prefix piece carries the word's opening but not its close, so a ⟨eow⟩ immediately after
    # it means the probe wrote the whole word, which measures a different thing. Mirrored for a
    # suffix piece.
    if pos in ("bow", "mid") and (not right or right.startswith(EOW_G)):
        return False
    if pos in ("eow", "mid") and (not left or left.endswith(BOW_G)):
        return False
    return True
