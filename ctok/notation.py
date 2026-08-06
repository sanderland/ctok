"""Codecs for the public marker notation — the one encoding shared by ``tokenize()`` output and the
keys of ``pieces.json``. The glyphs and atom names themselves live in ``constants.py``.

    ⟨bow⟩ ⟨eow⟩ ⟨shift⟩ ⟨caps⟩   structural markers, fused in-string or standalone
    ⟨pad⟩                        a message-frame token
    ⟨0xNN⟩                       one raw byte (sub-character chunks, and bracket escapes)
"""

import re

from .constants import ATOM_TO_GLYPH, GLYPH_TO_ATOM, L, R

_ATOM_RE = re.compile(f"{L}(?:bow|eow|jeow|shift|caps|pad|0x[0-9A-Fa-f]{{2}}){R}" "|.", re.DOTALL)
_BYTE_ATOM_RE = re.compile(f"{L}0x([0-9A-Fa-f]{{2}}){R}")


def escape_bytes(bs: bytes) -> str:
    """Raw bytes → a run of ⟨0xNN⟩ atoms."""
    return "".join(f"{L}0x{b:02X}{R}" for b in bs)


def escape_text(s: str) -> str:
    """Literal text → its public form, with the bracket characters byte-escaped so rendered text
    can never form a marker atom."""
    if L not in s and R not in s:
        return s
    return "".join(escape_bytes(c.encode()) if c in (L, R) else c for c in s)


def render_bytes(bs: bytes) -> str:
    """A raw byte chunk → literal text when it decodes, else a ⟨0xNN⟩ escape run."""
    try:
        return escape_text(bs.decode())
    except UnicodeDecodeError:
        return escape_bytes(bs)


def render_marked(marked: str) -> str:
    """An internal marked string → its public form: glyphs become named atoms, text is escaped."""
    return "".join(GLYPH_TO_ATOM.get(c) or escape_text(c) for c in marked)


def atoms(public: str):
    """Parse a public token string, yielding ``("marker", glyph)``, ``("byte", int)`` or
    ``("char", c)``."""
    for m in _ATOM_RE.finditer(public):
        tok = m.group(0)
        if len(tok) == 1:
            yield ("char", tok)
            continue
        glyph = ATOM_TO_GLYPH.get(tok)
        if glyph is not None:
            yield ("marker", glyph)
            continue
        byte = _BYTE_ATOM_RE.fullmatch(tok)
        if byte:
            yield ("byte", int(byte.group(1), 16))
        else:
            yield ("marker", tok)                         # ⟨pad⟩: zero-surface, no glyph form


def parse_marked(public: str) -> str:
    """Inverse of ``render_marked`` for ``pieces.json`` keys: named atoms back to single glyphs,
    ⟨0xNN⟩ escape runs back to their decoded characters."""
    parts: list[str] = []
    buf = bytearray()

    def flush():
        if buf:
            parts.append(bytes(buf).decode("utf-8"))
            buf.clear()

    for kind, v in atoms(public):
        if kind == "byte":
            buf.append(v)
        else:
            flush()
            parts.append(v)
    flush()
    return "".join(parts)
