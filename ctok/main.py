"""The entry points: the public API, version routing, and the ``ctok`` command.

A requested version selects a *family* — one reconstructed tokenizer generation — and from it a data
directory holding that family's ``pieces.json``. Everything below this module is version-agnostic:
one encode (``normalize.py``) and one tiling (``engine.py``), over one vocabulary.
"""

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import cache
from importlib.resources import files

from .constants import MARKER_GLYPHS, PAD
from .engine import ByteFloor, build_vocab, tile
from .normalize import nfc, stream
from .notation import parse_marked, render_bytes, render_marked


@dataclass(frozen=True)
class Family:
    """One reconstructed tokenizer generation."""

    pieces: str | None         # its vocabulary file under data/; None = not reconstructed yet
    source_model: str          # the count_tokens model this family reconstructs
    min_version: Decimal       # lowest requested version this family serves
    meta: tuple[tuple[str, object], ...] = ()   # measured overrides on that file's ``meta``
    also_serves: tuple[str, ...] = ()           # other model ids MEASURED to count identically


FAMILIES: dict[str, Family] = {
    "v3": Family("pieces_v3.json", "claude-opus-4-5", Decimal("3.0")),
    "v4.7": Family("pieces_v4_7.json", "claude-opus-4-7", Decimal("4.7")),
    # v5 BORROWS v4.7's vocabulary: its message frame is measured (`count_tokens` on a one-character
    # message is 7 tokens, so the frame is 6 against 4.7's 11) but no piece has been mined against
    # opus-5 yet, so the honest model is "v4.7's token list read through v5's frame". The other two
    # family scalars were checked rather than assumed: v5 folds no quotes and has no all-caps marker,
    # exactly like v4.7. Sharing the file rather than copying it means the two cannot drift while
    # that holds; the day a v5 piece is measured, v5 gets `pieces_v5.json` and this note goes away.
    # `claude-sonnet-5` is not assumed to share this family — it was measured: 80 texts drawn from
    # the line corpora and the held-out Rosetta sample count identically to `claude-opus-5`, frame
    # and all.
    "v5": Family("pieces_v4_7.json", "claude-opus-5", Decimal("5.0"),
                 (("message_overhead", 6), ("frame_bow", False), ("frame_tail", "free")),
                 ("claude-sonnet-5",)),
}

_MODEL_TO_FAMILY = {model: key for key, fam in FAMILIES.items()
                    for model in (fam.source_model, *fam.also_serves)}
# (base version, family key), highest first — derived from FAMILIES, so adding a family is one edit.
_FAMILY_BASES = sorted(((fam.min_version, key) for key, fam in FAMILIES.items()), reverse=True)


def _parse_version(version: float | str) -> Decimal:
    """Parse only. There is no floor check here: a version below every family's base matches no
    entry in ``_FAMILY_BASES``, and :func:`_family` raises the same error on that fallthrough."""
    try:
        return Decimal(str(version))
    except (InvalidOperation, ValueError):
        raise NotImplementedError(f"Unknown Claude tokenizer version: {version!r}") from None


def _family(version: float | str) -> str:
    """Route a requested version to its family key: [3.0, 4.7) → v3, [4.7, 5.0) → v4.7,
    [5.0, ∞) → v5. A source-model id (``"claude-opus-4-7"``) routes straight to its family."""
    key = _MODEL_TO_FAMILY.get(str(version))
    if key is not None:
        return key
    v = _parse_version(version)
    for base, key in _FAMILY_BASES:
        if v >= base:
            return key
    raise NotImplementedError(f"Unknown Claude tokenizer version: {version!r}")


@cache
def _model(family: str) -> "TokenizerModel":
    if family not in FAMILIES:
        raise NotImplementedError(f"Unknown Claude tokenizer family: {family!r}")
    pieces = FAMILIES[family].pieces
    if pieces is None:
        raise NotImplementedError(
            f"The {family!r} Claude tokenizer family is not reconstructed yet; "
            f"available families: {', '.join(k for k, f in FAMILIES.items() if f.pieces)}."
        )
    path = files("ctok").joinpath("data", pieces)
    doc = json.loads(path.read_text(encoding="utf-8"))
    # A family may borrow another's vocabulary file and carry its own measured scalars over it (see
    # v5 above). The override is applied to the loaded copy only — the file on disk stays the one
    # its own family compiled.
    doc["meta"] = {**doc["meta"], **dict(FAMILIES[family].meta)}
    return TokenizerModel(doc)


@cache
def _vocabulary(family: str) -> dict:
    """The raw vocabulary document for ``family`` — read again, and cached separately.

    `_model` consumes its copy into the tiling structures and keeps no vocabulary document, which is
    right for counting and useless for the question this answers: what is this piece, and what was
    measured to put it there. Two small readers of one file beat one structure serving both.
    """
    path = files("ctok").joinpath("data", FAMILIES[family].pieces)
    return json.loads(path.read_text(encoding="utf-8"))


def pieces(version: float | str = 3.0) -> dict[str, dict | None]:
    """Every piece in the vocabulary, mapped to its witness — the evidence that it is one token.

    A witness is one probe and the count that accepts it: ``{"probe": "the", "n": 1, "kind":
    "bare"}`` says the bare message ``the`` was measured at one content token, so ``⟨bow⟩the⟨eow⟩``
    is a token and nothing about the rest of the vocabulary is involved in saying so. ``kind`` is
    the rung — ``bare`` (the piece IS the message), ``edge`` (one anchor word beside it), ``frame``
    (one on each side) — and ``n`` is always ``1 + anchors``.

    Three values are not witnesses and each says which it is: ``{"kind": "unframeable"}`` for a
    word-interior piece no probe can isolate, ``{"kind": "unmeasured"}`` for one nobody has paid the
    API call for yet, and ``None`` for a ``bytes_fallback`` prefix, which is not a token at all.
    """
    doc = _vocabulary(_family(version))
    return {p: w for group, entries in doc["tokens"].items() for p, w in entries.items()}


def witness(piece: str, version: float | str = 3.0) -> dict | None:
    """The witness for one piece, in the notation the vocabulary file uses (``⟨bow⟩the⟨eow⟩``).
    Raises ``KeyError`` for a string that is not a piece — which is itself the membership answer."""
    return pieces(version)[piece]


class TokenizerModel:
    """The loaded vocabulary plus the family scalars the encoder and tiler read from it.

    Everything the tiler needs is derived here, once: the tiling vocabulary with its longest piece,
    and the byte floor — what a codepoint costs when no piece covers it. ``doc`` is consumed rather
    than kept, so there is no second, lazier copy of the vocabulary question.
    """

    def __init__(self, doc: dict) -> None:
        meta = doc["meta"]
        # What a SINGLE user message costs before its content. Measured, and decomposed: a request
        # costs a fixed prefix P, each turn costs a role marker plus its content, and a request that
        # ends on the user is followed by the frame's own assistant prompt T. An assistant marker
        # costs exactly T, and adjacent same-role messages merge into one turn joined by a 1-token
        # separator — so the marker total is (number of user turns) x (H + T), and for one message
        # that is P + H + T: 1 + 6 on v3, 1 + 10 on v4.7, 2 + 4 on v5. Only the sum H + T is
        # measurable, since every request opens on a user turn.
        self.message_overhead = meta["message_overhead"]
        self.fold_quotes = meta["fold_quotes"]
        self.allcaps_min = meta["allcaps_min"]
        # What the frame does at each edge. v3 and v4.7 share one shape and are the defaults; v5
        # measured different at BOTH edges, which is why these are family scalars and not constants.
        #   frame_bow  — the frame's last token before the content is a ⟨bow⟩, so message start is
        #                an interior word boundary: it absorbs one leading space, and a run that
        #                cannot own that ⟨bow⟩ pays for it as a token of its own.
        #   frame_tail — "ladder": the frame's own ⏎⏎ tail, which one token can span into, so a
        #                trailing newline run is nearly free but not quite (`engine.frame_tail`).
        #                "free": trailing whitespace of every kind costs nothing at all.
        self.frame_bow = meta.get("frame_bow", True)
        self.frame_tail = meta.get("frame_tail", "ladder")
        # The characters the frame absorbs off the end of the content, per that rule.
        self.frame_strip = "\n" if self.frame_tail == "ladder" else " \t\n\r\f\v"

        tokens = doc["tokens"]
        # Every group is cost-1 pieces except the byte fallback, which is prefix costs rather than
        # tokens. Grouping is for provenance — which campaign measured a piece — so the loader takes
        # them all and stays correct when a group is added or split.
        pieces = [p for group, ps in tokens.items() if group != "bytes_fallback" for p in ps]
        # Cost-1 whole single-codepoint characters live in ``pieces`` (a whole character is a
        # length-1 token, not a byte prefix). The byte floor folds them back into its membership set
        # so an uncovered character still prices at 1. The structural markers are not text.
        self.unit_pieces = {c for c in (parse_marked(p) for p in pieces)
                            if len(c) == 1 and c not in MARKER_GLYPHS}
        self.bytes = ByteFloor(tokens["bytes_fallback"], self.unit_pieces)
        self.vocab, self.max_piece_len = build_vocab(pieces, tokens)

        self._char_cost_cache: dict[str, int] = {}


def _require_text(text) -> str:
    """The public text API is ``str``-only: reject anything else with an error naming the contract
    instead of letting a deep ``TypeError`` surface from inside NFC."""
    if not isinstance(text, str):
        raise TypeError(f"text must be str, not {type(text).__name__}")
    return text


def tokenize(text: str, version: float | str = 3.0) -> list[str]:
    """``text`` as a token list — the model's primary object, of which ``token_count`` is the length.

    Every element is a string in the public notation: text tokens carry their structural markers
    in-line (``'⟨shift⟩⟨bow⟩token⟨eow⟩'``), sub-character byte chunks render as ``⟨0xNN⟩`` atoms, and
    a marker no piece absorbed stands as its own token. The list starts with the single-message
    frame as ``⟨pad⟩`` tokens, so its length matches ``count_tokens`` on a one-message request.

    Token *boundaries* are approximate; the *length* is the count model's prediction.
    """
    model = _model(_family(version))
    _cost, toks = tile(_require_text(text), model)
    rendered = [render_marked(t) if isinstance(t, str) else render_bytes(t) for t in toks]
    return [PAD] * model.message_overhead + rendered


def token_count(text: str, version: float | str = 3.0) -> int:
    """Reconstructed token count for ``text`` as a single user message — by definition
    ``len(tokenize(text, version))``, which structurally precludes a negative or fractional count."""
    return len(tokenize(text, version))


def normalize(text: str, version: float | str = 3.0) -> str:
    """The model's irreversible text normalization: NFC plus the family's quote folding (v3 folds
    curly quotes to ASCII; v4.7 keeps them literal)."""
    return nfc(_require_text(text), fold_quotes=_model(_family(version)).fold_quotes)


def marked_stream(text: str, version: float | str = 3.0) -> str:
    """The marked stream the tiler tiles, in public notation — the single intermediate
    representation. Useful for understanding a count; not part of the stable API."""
    return render_marked(stream(_require_text(text), _model(_family(version))))


def main(argv=None) -> None:
    """The ``ctok`` command: count a string and show how it tiles."""
    ap = argparse.ArgumentParser(prog="ctok", description="Claude tokenizer count tool")
    ap.add_argument("text")
    ap.add_argument("--version", default=3.0,
                    help="tokenizer version (default 3.0; 4.7 also available)")
    args = ap.parse_args(argv)

    overhead = _model(_family(args.version)).message_overhead
    tokens = tokenize(args.text, version=args.version)

    print(f"  stream: {marked_stream(args.text, version=args.version)!r}")
    print(f"  tokens: {tokens[overhead:]!r}")
    print(f"\n  content {len(tokens) - overhead} + frame {overhead} = {len(tokens)}")


if __name__ == "__main__":
    main()
