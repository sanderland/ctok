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


FAMILIES: dict[str, Family] = {
    "v3": Family("pieces_v3.json", "claude-opus-4-5", Decimal("3.0")),
    "v4.7": Family("pieces_v4_7.json", "claude-opus-4-7", Decimal("4.7")),
    "v5": Family(None, "claude-opus-5", Decimal("5.0")),
}

_MODEL_TO_FAMILY = {fam.source_model: key for key, fam in FAMILIES.items()}
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
    return TokenizerModel(json.loads(path.read_text(encoding="utf-8")))


class TokenizerModel:
    """The loaded vocabulary plus the family scalars the encoder and tiler read from it.

    Everything the tiler needs is derived here, once: the tiling vocabulary with its longest piece,
    and the byte floor — what a codepoint costs when no piece covers it. ``doc`` is consumed rather
    than kept, so there is no second, lazier copy of the vocabulary question.
    """

    def __init__(self, doc: dict) -> None:
        meta = doc["meta"]
        self.message_overhead = meta["message_overhead"]
        self.fold_quotes = meta["fold_quotes"]
        self.allcaps_min = meta["allcaps_min"]

        tokens = doc["tokens"]
        pieces = (list(tokens["word_pieces"]) + list(tokens.get("digits", []))
                  + list(tokens.get("ascii_digits", [])) + list(tokens.get("other_digits", []))
                  + list(tokens["punctuation"]))
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
