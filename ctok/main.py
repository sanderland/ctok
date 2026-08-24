"""Public API, version routing, and the ``ctok`` command.

A requested version selects a tokenizer family and its vocabulary file under ``data/``. The
encoder and tiler are shared by every family.
"""

import argparse
import json
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

from .constants import MARKER_GLYPHS, PAD
from .engine import ByteFloor, ReverseTrie, build_vocab, tile
from .normalize import nfc, stream
from .notation import parse_marked, render_bytes, render_marked


@dataclass(frozen=True)
class Family:
    """One reconstructed tokenizer generation."""

    pieces: str | None                 # its vocabulary file under data/; None = not reconstructed
    source_model: str                  # the count_tokens model this family was measured against
    min_version: tuple[int, ...]       # lowest requested version this family serves
    meta: tuple[tuple[str, object], ...] = ()   # measured overrides on that file's ``meta``


FAMILIES: dict[str, Family] = {
    "v3": Family("pieces_v3.json", "claude-opus-4-5", (3, 0)),
    "v4.7": Family("pieces_v4_7.json", "claude-opus-4-7", (4, 7)),
    # v5 reuses v4.7's vocabulary; only the message frame differs. Sonnet 5 counts like Opus 5.
    "v5": Family("pieces_v4_7.json", "claude-opus-5", (5, 0),
                 (("message_overhead", 6), ("frame_bow", False), ("frame_tail", "free"))),
}

# (base version, family key), highest first.
_FAMILY_BASES = sorted(((fam.min_version, key) for key, fam in FAMILIES.items()), reverse=True)


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse "4.7" to (4, 7). ``str`` only: the float literal ``4.10`` is ``4.1``."""
    if not isinstance(version, str):
        raise TypeError(f'version must be a string like "4.7", not {version!r}')
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        raise NotImplementedError(f"Unknown Claude tokenizer version: {version!r}") from None


def _at_least(v: tuple[int, ...], base: tuple[int, ...]) -> bool:
    """``v >= base`` with missing trailing components read as zero, so "5" equals "5.0"."""
    n = max(len(v), len(base))
    return v + (0,) * (n - len(v)) >= base + (0,) * (n - len(base))


def _family(version: str) -> str:
    """Route a requested version to its family key: [3.0, 4.7) → v3, [4.7, 5.0) → v4.7,
    [5.0, ∞) → v5."""
    v = _parse_version(version)
    for base, key in _FAMILY_BASES:
        if _at_least(v, base):
            return key
    raise NotImplementedError(f"Unknown Claude tokenizer version: {version!r}")


@cache
def _document(filename: str) -> dict:
    """Load one vocabulary document once."""
    path = files("ctok").joinpath("data", filename)
    return json.loads(path.read_text(encoding="utf-8"))


def _pieces_file(family: str) -> str:
    """The vocabulary file for a family."""
    try:
        filename = FAMILIES[family].pieces
    except KeyError:
        raise NotImplementedError(f"Unknown Claude tokenizer family: {family!r}") from None
    if filename is None:
        raise NotImplementedError(
            f"The {family!r} Claude tokenizer family is not reconstructed yet; "
            f"available families: {', '.join(k for k, f in FAMILIES.items() if f.pieces)}."
        )
    return filename


@cache
def _model(family: str) -> "TokenizerModel":
    doc = _document(_pieces_file(family))
    # A family may borrow another's vocabulary file with its own measured scalars (v5 above).
    # Replace the metadata mapping rather than mutating the cached document.
    family_doc = {**doc, "meta": {**doc["meta"], **dict(FAMILIES[family].meta)}}
    return TokenizerModel(family_doc)


def _vocabulary(family: str) -> dict:
    """The vocabulary document for ``family``, including its published witness records."""
    return _document(_pieces_file(family))


def pieces(version: str = "3.0") -> dict[str, dict]:
    """Every piece in the vocabulary, mapped to the evidence that it is one token.

    A token witness records a probe, its raw message count, and the fixed template used to isolate
    the piece, for example ``{"probe": "the", "raw": 12, "kind": "raw"}``. Byte prefixes use
    ``kind="prefix"`` and structural marker atoms use ``kind="special"``.
    """
    doc = _vocabulary(_family(version))
    return {p: w.copy() for entries in doc["tokens"].values() for p, w in entries.items()}


def witness(piece: str, version: str = "3.0") -> dict:
    """The witness for one piece, in the notation the vocabulary file uses (``⟨bow⟩the⟨eow⟩``).
    Raises ``KeyError`` for a string that is not a piece."""
    doc = _vocabulary(_family(version))
    for entries in doc["tokens"].values():
        if piece in entries:
            return entries[piece].copy()
    raise KeyError(piece)


class TokenizerModel:
    """The loaded vocabulary plus the family scalars the encoder and tiler read from it."""

    def __init__(self, doc: dict) -> None:
        meta = doc["meta"]
        # Measured fixed cost of a single user message before its content.
        self.message_overhead = meta["message_overhead"]
        self.fold_quotes = meta["fold_quotes"]
        self.allcaps_min = meta["allcaps_min"]
        # v3 and v4.7 share the defaults. v5 differs at both frame edges.
        # frame_bow says whether the frame ends in a ⟨bow⟩ that absorbs one leading space.
        # frame_tail is "ladder" for the measured newline ladder and "free" when the frame absorbs
        # all trailing ASCII whitespace.
        self.frame_bow = meta.get("frame_bow", True)
        self.frame_tail = meta.get("frame_tail", "ladder")
        # The characters the frame absorbs off the end of the content, per that rule.
        self.frame_strip = "\n" if self.frame_tail == "ladder" else " \t\n\r\f\v"

        tokens = doc["tokens"]
        # Every group is cost-1 pieces except the byte fallback, which holds prefix costs.
        # Grouping is provenance only, so take all groups.
        pieces = [p for group, ps in tokens.items() if group != "bytes_fallback" for p in ps]
        # Fold single-codepoint pieces into the byte floor's membership set, so an uncovered
        # character still prices at 1.
        parsed_pieces = [parse_marked(p) for p in pieces]
        self.unit_pieces = {c for c in parsed_pieces
                            if len(c) == 1 and c not in MARKER_GLYPHS}
        self.bytes = ByteFloor(tokens["bytes_fallback"], self.unit_pieces)
        self.vocab = build_vocab(parsed_pieces, tokens)
        self.trie = ReverseTrie(self.vocab)

        self._char_cost_cache: dict[str, int] = {}


def _require_text(text) -> str:
    """The public text API is ``str``-only."""
    if not isinstance(text, str):
        raise TypeError(f"text must be str, not {type(text).__name__}")
    return text


def tokenize(text: str, version: str = "3.0") -> list[str]:
    """``text`` as a token list; ``token_count`` is its length.

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


def token_count(text: str, version: str = "3.0") -> int:
    """Reconstructed token count for ``text`` as a single user message."""
    return len(tokenize(text, version))


def normalize(text: str, version: str = "3.0") -> str:
    """The model's irreversible text normalization: NFC plus the family's quote folding (v3 folds
    curly quotes to ASCII; v4.7 keeps them literal)."""
    return nfc(_require_text(text), fold_quotes=_model(_family(version)).fold_quotes)


def marked_stream(text: str, version: str = "3.0") -> str:
    """The marked stream the tiler tiles, in public notation. Useful for understanding a count;
    not part of the stable API."""
    return render_marked(stream(_require_text(text), _model(_family(version))))


# Both generations, shown side by side when no version is asked for: the two differ enough on the
# same string — case marking, vocabulary, frame size — that one alone invites reading a v3 count as
# "the" Claude count.
DEFAULT_VERSIONS = ("3.0", "5.0")


def _report(text: str, version: str, *, label: bool) -> None:
    """One family's reading of ``text``: the marked stream, the content tokens, and the arithmetic."""
    overhead = _model(_family(version)).message_overhead
    tokens = tokenize(text, version=version)
    if label:
        print(f"  v{version}")
    print(f"  stream: {marked_stream(text, version=version)!r}")
    print(f"  tokens: {tokens[overhead:]!r}")
    print(f"\n  content {len(tokens) - overhead} + frame {overhead} = {len(tokens)}")


def main(argv=None) -> None:
    """The ``ctok`` command: count a string and show how it tiles."""
    ap = argparse.ArgumentParser(prog="ctok", description="Claude tokenizer count tool")
    ap.add_argument("text")
    ap.add_argument("--version", default=None,
                    help='tokenizer version (default: both "3.0" and "5.0"; "4.7" also available)')
    args = ap.parse_args(argv)

    versions = [args.version] if args.version else list(DEFAULT_VERSIONS)
    for i, version in enumerate(versions):
        if i:
            print()
        _report(args.text, version, label=len(versions) > 1)


if __name__ == "__main__":
    main()
