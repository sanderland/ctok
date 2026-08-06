"""Every witness in the shipped vocabulary, re-checked against the arithmetic it ships with.

The file records, per piece, the probe that was sent and the raw ``count_tokens`` value it returned.
Nothing here talks to the API — that is the mining repo's job and its measurement cache lives there —
but everything else about a witness is checkable offline and is checked here:

* the probe text really is the named template applied to this piece;
* ``cost = raw − base + 1 − overhead`` comes out at exactly 1, so the record cannot claim a probe and
  a number that do not go together;
* the ENCODER still writes the piece into that probe where its position claims — a suffix piece in a
  probe that closes the word before it is measuring something else;
* nothing calls itself unwitnessable while a template in the file's own table reaches it.

The last one is what rots. `normalize.py` changes, a piece that no template could isolate becomes
reachable, and the file keeps saying "no instrument" for something now askable. That is an unclaimed
measurement rather than a wrong answer, and this is what notices.
"""

import json
from importlib.resources import files

import pytest

from ctok.main import FAMILIES, _family, _model, pieces, witness
from ctok.notation import parse_marked
from ctok.witness import cost, places, position, surface, verify

FILES = sorted({fam.pieces for fam in FAMILIES.values() if fam.pieces})
GAP_KINDS = {"unmeasured", "no-instrument", "refuted", "context-bound", "special"}


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
    kinds = set(doc["meta"]["witness"]["templates"]) | GAP_KINDS | {"prefix", "ownscript"}
    for group, entries in doc["tokens"].items():
        assert isinstance(entries, dict), f"{group} is still a list — run scripts/witness_pieces.py"
        for piece, w in entries.items():
            # `bytes_fallback` used to be null here — a prefix is not a token, so there was thought
            # to be nothing to ask. There is: it predicts what characters sharing it cost.
            assert isinstance(w, dict) and w.get("kind"), f"{piece}: no witness record"
            assert isinstance(w, dict) and w.get("kind"), f"{piece}: no witness record"
            assert w["kind"] in kinds, f"{piece}: unknown kind {w['kind']!r}"


@pytest.mark.parametrize("name", FILES)
def test_each_witness_holds_under_the_arithmetic_that_ships_with_it(name):
    """probe == template(piece), cost == 1, and the encoder still places the piece in the probe."""
    doc = _doc(name)
    model = _model(_family_of(name))
    for group, entries in doc["tokens"].items():
        for piece, w in entries.items():
            if not w or w["kind"] in GAP_KINDS:
                continue
            why = verify(parse_marked(piece), w, doc["meta"], model)
            assert why is None, f"{piece} ({w.get('probe')!r}): {why}"


@pytest.mark.parametrize("name", FILES)
def test_a_refutation_records_what_refuted_it(name):
    """A refuted piece is one the file admits it cannot justify. It has to say by which probe, and
    that probe must genuinely disagree — otherwise it is a stale label nobody can act on."""
    doc = _doc(name)
    base = doc["meta"]["witness"]["base"]
    templates = doc["meta"]["witness"]["templates"]
    for group, entries in doc["tokens"].items():
        for piece, w in entries.items():
            if not w or w["kind"] != "refuted":
                continue
            assert w.get("refused"), f"{piece}: refuted by nothing recorded"
            for r in w["refused"]:
                if r["kind"] == "prefix":
                    assert r["floor"] != r["measured"], f"{piece}: {r} does not refute anything"
                    continue
                template, overhead = templates[r["kind"]]
                assert template.format(surface(parse_marked(piece))) == r["probe"]
                assert cost(r["raw"], base, overhead) != 1, f"{piece}: {r} does not refute anything"


@pytest.mark.parametrize("name", FILES)
def test_a_witness_asks_about_the_position_the_piece_actually_occupies(name):
    """A ``bow`` template on a suffix piece would be measuring the wrong end of a word.

    WHICH template a piece is entitled to is the mining repo's question — the hazards that decide it
    are `PROBES.md`'s and they need the probe inventory to answer (`tests/test_witness_file.py`).
    What is checkable from here is that a recorded witness and the piece's own marked form agree
    about where in a word it sits, and that a gap kind carries no measurement.
    """
    doc = _doc(name)
    for group, entries in doc["tokens"].items():
        for piece, w in entries.items():
            if not w:
                continue
            if w["kind"] in GAP_KINDS:
                assert "probe" not in w, f"{piece}: a {w['kind']} record carries a measurement"
                continue
            if w["kind"] in ("prefix", "ownscript"):
                continue                     # these kinds validate placement in their own verifier
            pos = position(parse_marked(piece))
            # A digit piece is stored bare — `00`, no boundary markers, because a digit run carries
            # its own — so the glued frame that pins it reads at `mid`. Every other template names
            # the position in its own name, whichever anchor family it belongs to.
            named = w["kind"].removeprefix("cased_").removeprefix("digit_")
            # A contraction is stored bare (`'s`) and tiled glued (`'s⟨eow⟩`), so its stored form
            # reads `mid` while the piece it stands for closes a word.
            expect = {"raw": ("word", "bow"), "word": ("word",), "char": ("mid",),
                      "glued": ("mid", "word"), "contraction": ("mid",)}.get(w["kind"], (named,))
            assert pos in expect, f"{piece} sits at {pos} but is witnessed as {w['kind']}"


def test_the_witness_reader_serves_a_borrowing_family():
    """v5 borrows v4.7's file, so it borrows its witnesses — measured on v4.7's source model, which
    `meta.witness.measured_on` is what says. The accessor must not pretend otherwise."""
    assert witness("⟨bow⟩the⟨eow⟩", 4.7) == witness("⟨bow⟩the⟨eow⟩", 5.0)
    assert pieces(5.0) == pieces(4.7)
    for fam in FAMILIES.values():
        if fam.pieces:
            meta = _doc(fam.pieces)["meta"]
            assert meta["witness"]["measured_on"] == FAMILIES[_family_of(fam.pieces)].source_model
            assert meta["witness"]["base"] > meta["message_overhead"], "BASE is one token above it"
    assert _family(5.0) == "v5"


# Measured 2026-08-05: v3 96.4%, v4.7 91.3%. The floor carries margin so ordinary churn passes,
# and the thing it exists to catch is a campaign that ships pieces with no evidence behind them —
# the error gates cannot see that, because an unwitnessed piece counts exactly like a witnessed one.
WITNESSED_FLOOR = {"v3": 0.95, "v4.7": 0.88}


@pytest.mark.parametrize("name", FILES)
def test_the_vocabulary_stays_backed_by_measurements(name):
    """What share of each vocabulary has a probe behind it, asserted rather than only reported."""
    from tests.gates import GAP_KINDS, totals, witness_coverage, witnessed

    family = _family_of(name)
    counts = totals(witness_coverage()[family])
    total, backed = sum(counts.values()), witnessed(counts)
    share = backed / total
    assert share >= WITNESSED_FLOOR[family], (
        f"{family}: only {backed:,} of {total:,} pieces ({share:.1%}) carry a witness, under the "
        f"{WITNESSED_FLOOR[family]:.0%} floor — run scripts/witness_pieces.py --live in the mining "
        f"repo, or lower the floor deliberately. Gaps: "
        f"{ {k: counts.get(k, 0) for k in GAP_KINDS if counts.get(k)} }")


@pytest.mark.parametrize("name", FILES)
def test_no_shipped_piece_is_one_its_own_probe_refutes(name):
    """`refuted` means the vocabulary claims a piece and the measurement says it is two tokens.

    Unlike the other gap kinds this is not a state to pass through: `unmeasured` is work not yet
    bought and `no-instrument` is a piece the inventory cannot reach, but a refuted piece is one we
    have already asked about and been told no. `scripts/retire_refuted.py` is what clears them — it
    judges the set on the mining corpus first, because a fabricated piece can be masking a missing
    one and dropping it blind trades a wrong tiling for a worse one.
    """
    from tests.gates import totals, witness_coverage

    family = _family_of(name)
    by_group = witness_coverage()[family]
    culprits = {g: c["refuted"] for g, c in by_group.items() if c.get("refuted")}
    assert not totals(by_group).get("refuted"), (
        f"{family} ships {totals(by_group)['refuted']} refuted pieces {culprits} — run "
        f"scripts/retire_refuted.py --family {family} --leave-one-out")


def test_a_witness_is_readable_without_reading_the_file():
    """The published API answers the question the file exists to answer."""
    assert witness("⟨bow⟩the⟨eow⟩", 4.7) == {"probe": "the", "raw": 12, "kind": "raw"}
    assert witness("00", 4.7) == {"probe": "a00b", "raw": 14, "kind": "glued"}
    assert witness("e0a4", 4.7)["kind"] == "prefix"
    with pytest.raises(KeyError):
        witness("this is not a piece", 4.7)
