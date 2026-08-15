"""Every witness in the shipped vocabulary, re-checked against the arithmetic it ships with.

Nothing here talks to the API; everything else about a witness is checkable offline and is checked:

* the probe text really is the named template applied to this piece;
* ``cost = raw − base + 1 − overhead`` comes out at exactly 1;
* the encoder still writes the piece into that probe where its position claims;
* nothing calls itself unwitnessable while a template in the file's own table reaches it. This is
  the check that rots as `normalize.py` changes and unreachable pieces become askable.
"""


import json
from importlib.resources import files

import pytest

from ctok.main import FAMILIES, _family, _model, pieces, witness
from ctok.constants import MARKER_GLYPHS
from ctok.notation import parse_marked
from ctok.witness import position, verify

FILES = sorted({fam.pieces for fam in FAMILIES.values() if fam.pieces})
GAP_KINDS = {"unmeasured", "no-instrument", "refuted", "special"}


def _doc(name):
    return json.loads(files("ctok").joinpath("data", name).read_text(encoding="utf-8"))


def _family_of(name):
    return next(k for k, fam in FAMILIES.items() if fam.pieces == name and not fam.meta)


@pytest.mark.parametrize("name", FILES)
def test_every_piece_carries_a_witness_or_says_why_not(name):
    """No piece is silent. A gap is a recorded kind, never a missing key or a bare null."""
    doc = _doc(name)
    # `prefix` is a witness but not a template: a byte prefix is verified by the floor
    # reproducing a character it predicts, not by a probe costing one token.
    kinds = set(doc["meta"]["witness"]["templates"]) | GAP_KINDS | {"prefix"}
    for group, entries in doc["tokens"].items():
        assert isinstance(entries, dict), f"{group}: expected a piece-to-witness mapping"
        for piece, w in entries.items():
            assert isinstance(w, dict) and w.get("kind"), f"{piece}: no witness record"
            assert w["kind"] in kinds, f"{piece}: unknown kind {w['kind']!r}"


@pytest.mark.parametrize("name", FILES)
def test_each_witness_holds_under_the_arithmetic_that_ships_with_it(name):
    """probe == template(piece), cost == 1, and the encoder still places the piece in the probe."""
    doc = _doc(name)
    model = _model(_family_of(name))
    for group, entries in doc["tokens"].items():
        for piece, w in entries.items():
            if w["kind"] in GAP_KINDS:
                continue
            why = verify(parse_marked(piece), w, doc["meta"], model)
            assert why is None, f"{piece} ({w.get('probe')!r}): {why}"


@pytest.mark.parametrize("name", FILES)
def test_a_witness_asks_about_the_position_the_piece_actually_occupies(name):
    """A ``bow`` template on a suffix piece would be measuring the wrong end of a word.

    Choosing the template requires the measurement inventory and its controls. What is checkable
    here is that a recorded witness and the piece's own marked form agree about where in a word it
    sits, and that a gap kind carries no measurement.
    """
    doc = _doc(name)
    for group, entries in doc["tokens"].items():
        for piece, w in entries.items():
            if w["kind"] in GAP_KINDS:
                assert "probe" not in w, f"{piece}: a {w['kind']} record carries a measurement"
                continue
            if w["kind"] == "prefix":
                continue                     # this kind validates placement in its own verifier
            pos = position(parse_marked(piece))
            # A digit piece is stored bare, such as `00`, because a digit run carries its own
            # boundary markers. The glued frame that pins it reads at `mid`. Every other template
            # names the position in its own name, whichever anchor family it belongs to.
            named = w["kind"].removeprefix("cased_").removeprefix("digit_")
            # A contraction is stored bare (`'s`) and tiled glued (`'s⟨eow⟩`), so its stored form
            # reads `mid` while the piece it stands for closes a word.
            # `mark_mid` and `mark_sep` share the probe `.ᛒ{}ᛒ.` and differ only in overhead: a
            # mark that closes its own word puts an ⟨eow⟩ and a ⟨bow⟩ into the probe that the
            # anchor has not got, and `mark_sep` carries those two in its constant. Both are
            # word-interior frames, so both read `mid`.
            expect = {"raw": ("word", "bow"), "word": ("word",), "char": ("mid",),
                      "glued": ("mid", "word"), "contraction": ("mid",),
                      "mark_mid": ("mid",), "mark_sep": ("mid",)}.get(w["kind"], (named,))
            assert pos in expect, f"{piece} sits at {pos} but is witnessed as {w['kind']}"


def test_the_witness_reader_serves_a_borrowing_family():
    """v5 borrows v4.7's file and its witnesses, measured on v4.7's source model,
    as `meta.witness.measured_on` says."""
    assert witness("⟨bow⟩the⟨eow⟩", "4.7") == witness("⟨bow⟩the⟨eow⟩", "5.0")
    assert pieces("5.0") == pieces("4.7")
    for fam in FAMILIES.values():
        if fam.pieces:
            meta = _doc(fam.pieces)["meta"]
            assert meta["witness"]["measured_on"] == FAMILIES[_family_of(fam.pieces)].source_model
            assert meta["witness"]["base"] > meta["message_overhead"], "BASE is one token above it"
    assert _family("5.0") == "v5"


@pytest.mark.parametrize("name", FILES)
def test_every_vocabulary_piece_is_witnessed_or_special(name):
    """CI's target is literal: every shipped text piece has evidence; only structure is special."""
    from tests.gates import MISSING, UNRESOLVED

    gaps = {group: {kind: [piece for piece, witness in entries.items()
                           if witness.get("kind") == kind]
                    for kind in MISSING + UNRESOLVED
                    if any(witness.get("kind") == kind for witness in entries.values())}
            for group, entries in _doc(name)["tokens"].items()
            if any(witness.get("kind") in MISSING + UNRESOLVED
                   for witness in entries.values())}
    missing = sum(len(pieces) for kinds in gaps.values() for pieces in kinds.values())
    assert not missing, (
        f"{_family_of(name)}: {missing} shipped pieces are neither witnessed nor special: {gaps}. "
        "Find a witness or remove the piece; lowering a percentage floor is no longer an option.")


def test_unknown_witness_kinds_do_not_count_as_evidence():
    """Coverage must fail closed when a new kind has not been classified."""
    from tests.gates import witnessed

    assert witnessed({"word": 2, "special": 1, "unknown": 5}) == 3


def test_a_witness_is_readable_without_reading_the_file():
    """The published API answers the question the file exists to answer."""
    assert witness("⟨bow⟩the⟨eow⟩", "4.7") == {"probe": "the", "raw": 12, "kind": "raw"}
    assert witness("00", "4.7") == {"probe": "a00b", "raw": 14, "kind": "glued"}
    assert witness("e0a4", "4.7")["kind"] == "prefix"
    with pytest.raises(KeyError):
        witness("this is not a piece", "4.7")


def test_piece_results_do_not_expose_the_cached_vocabulary():
    result = pieces("4.7")
    result["⟨bow⟩the⟨eow⟩"]["raw"] = 0
    assert witness("⟨bow⟩the⟨eow⟩", "4.7")["raw"] == 12


def test_tamil_terminal_ng_has_one_direct_witness_not_overlapping_proxies():
    """The terminal consonant is one measured suffix, not a family of count-equivalent patches."""
    assert witness("ங⟨eow⟩", "4.7") == {"probe": ".ヲங.", "raw": 17, "kind": "eow"}
    assert {piece for piece in pieces("4.7") if "ங" in piece} == {"ங⟨eow⟩"}


@pytest.mark.parametrize("name", FILES)
def test_no_piece_mixes_whitespace_with_other_material(name):
    """A space, tab or newline is either the whole piece or not in it. A piece holding a
    letter and a space is not a token that was measured; it is a modelling device standing in for
    an absorption the stream failed to perform, and its witness cannot tell the two apart."""
    doc = _doc(name)
    bad = [piece for entries in doc["tokens"].values() for piece in entries
           if (body := "".join(c for c in piece if c not in MARKER_GLYPHS))
           and any(c.isspace() for c in body) and not all(c.isspace() for c in body)]
    assert not bad, (f"{_family_of(name)}: {len(bad)} pieces mix whitespace with other material: "
                     f"{bad}. Whitespace is its own run. A piece like this is compensating for a "
                     f"stream rule that is missing.")
