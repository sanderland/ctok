"""Offline reproduction gates against recorded ``count_tokens`` values.

Each fixture contains a corpus and one recorded count per family. Every document must reproduce
exactly. The tests make no API calls and need no network access.

Corpora:

  * UDHR: the Universal Declaration of Human Rights in 501 natural languages (parallel).
  * MultiPL-E: the same 25 HumanEval problems in 22 programming languages (parallel, held out:
    nothing may select, accept or reject a piece because of it).
  * Rosetta Code: 1,741 documents of real multi-language source (in-sample: mining bisects it),
    plus 250 from blocks the first sample never touched (out-of-sample for anything it chose).

UDHR was held out until 2026-08-12, when its last nine non-exact readings were closed by bisecting
the documents themselves; its rate is in-sample from that date and labeled so wherever quoted.

Run ``python tests/gates.py`` for a Markdown report.
"""

from __future__ import annotations

import gzip
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tabulate import tabulate

from ctok.main import FAMILIES, _vocabulary, token_count

FIXTURES = Path(__file__).parent / "fixtures"

# v4.8+ borrows v4.7's vocabulary. The gate table covers each physical vocabulary once; frame
# behavior is pinned in `test_api.py`.
GATES: dict[str, dict] = {
    "udhr": {
        "title": "UDHR",
        "key": "f",
        "n": 501,
        # Finished 2026-08-12: both families reproduce all 501 documents. In-sample from that
        # date (see the module docstring), but each of the final six pieces carries its own
        # fixed-template membership witness.
        "families": {
            "v3": "3.0",
            "v4.7": "4.7",
        },
    },
    "rosetta": {
        "title": "Rosetta Code",
        "key": "id",
        "n": 1741,
        "families": {
            "v3": "3.0",
            "v4.7": "4.7",
        },
    },
    "rosetta_holdout": {
        "title": "Rosetta Code (held out)",
        "key": "id",
        "n": 250,
        # Documents that selected nothing: no piece in the vocabulary was probed because of
        # them. Finished.
        "families": {
            "v3": "3.0",
            "v4.7": "4.7",
        },
    },
    "multipl_e": {
        "title": "MultiPL-E",
        "key": "lang",
        "n": 22,
        # Finished: every family reproduces all 22 files.
        "families": {
            "v3": "3.0",
            "v4.7": "4.7",
        },
    },
}


def corpus(name: str) -> list[dict]:
    """The shared corpus rows for a gate."""
    with gzip.open(FIXTURES / f"{name}.jsonl.gz", "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def recorded(name: str, family: str) -> dict:
    """The recorded ``count_tokens`` values for one family: ``{"model": ..., "counts": {...}}``."""
    return json.loads((FIXTURES / f"{name}_counts.json").read_text(encoding="utf-8"))[family]


def score(name: str, family: str) -> dict:
    """Compare one family with the recorded counts for one corpus."""
    cfg = GATES[name]
    rows = corpus(name)
    counts = recorded(name, family)
    assert counts["model"] == FAMILIES[family].source_model, (
        f"{name} counts were measured on {counts['model']!r} but family {family!r} reconstructs "
        f"{FAMILIES[family].source_model!r}; wrong fixture for this family")

    version = cfg["families"][family]
    for r in rows:
        r["api"] = counts["counts"][r[cfg["key"]]]
        r["ours"] = token_count(r["text"], version=version)
    return {
        "rows": rows,
        "n": len(rows),
        "exact": sum(r["ours"] == r["api"] for r in rows),
    }


def assert_gate(name: str, family: str, agg: dict) -> None:
    """Require every document to reproduce exactly."""
    cfg = GATES[name]
    assert agg["n"] == cfg["n"], f"[{name}/{family}] corpus size changed: {agg['n']} != {cfg['n']}"
    bad = [str(r.get("name") or r[cfg["key"]])
           for r in agg["rows"] if r["ours"] != r["api"]]
    assert not bad, (f"[{name}/{family}] {len(bad)} of {agg['n']} documents no longer "
                     f"reproduce: {', '.join(bad[:8])}{' ...' if len(bad) > 8 else ''}")


def vocabulary_owners() -> dict[str, str]:
    """family -> the family whose vocabulary file it counts with. Derived: two families borrow
    when they share a file, and the first family listed for a file owns it (v4.8 reads v4.7's)."""
    owner: dict[str, str] = {}
    for key, fam in FAMILIES.items():
        owner[key] = next(k for k, f in FAMILIES.items() if f.pieces == fam.pieces)
    return owner


def _owned_vocabularies():
    """Yield each physical vocabulary once, under the family that owns it."""
    for key, owner in vocabulary_owners().items():
        if owner == key:
            yield key, _vocabulary(key)


def _borrowers() -> list[str]:
    """One line per family that counts with someone else's file."""
    return [f"{key} counts with {owner}'s vocabulary ({FAMILIES[key].pieces})"
            for key, owner in vocabulary_owners().items() if owner != key]


def _breaches(cov: dict[str, dict[str, dict[str, int]]], kind: str) -> list[tuple[str, str, int]]:
    """``(family, group, count)`` for every group holding pieces of one gap kind."""
    return [(fam, g, c[kind]) for fam, by_group in cov.items()
            for g, c in by_group.items() if c.get(kind)]


def cells_of(counts: dict[str, int]) -> tuple[int, int, str, dict[str, int]]:
    """``(pieces, witnessed-or-special, percentage, the gaps by kind)`` for one set of counts.
    Module level because :func:`report` needs the same arithmetic for its coverage cell."""
    known = known_kinds()
    total, w = sum(counts.values()), witnessed(counts)
    bucket = {"missing": sum(counts.get(k, 0) for k in MISSING),
              "unresolved": sum(counts.get(k, 0) for k in UNRESOLVED),
              "special": sum(counts.get(k, 0) for k in SPECIAL),
              "other": sum(n for k, n in counts.items() if k not in known)}
    pct = "100%" if w == total else (f"{100 * w / total:.2f}%" if total else "n/a")
    return total, w, pct, bucket


def _table(rows, headers) -> None:
    print(tabulate(rows, headers=headers, tablefmt="github"), end="\n\n")


def report_vocabulary() -> None:
    """Piece counts by group, and what share of each group carries a witness.

    Catches two regressions the error gates cannot: a silently emptied or ballooning group, and a
    group whose pieces stopped being backed by measurements (an unwitnessed piece counts exactly
    like a witnessed one, so only this table can tell). Gap kinds: ``missing`` (unbought or
    unreachable), ``unresolved`` (probe and corpus disagree), plus ``special``/``other`` to keep
    structural atoms and unknown kinds visible. Collapses to one line per family at full coverage.
    """
    cov = witness_coverage()
    cols = ("missing", "unresolved", "special", "other")
    refuted = _breaches(cov, "refuted")

    print("\n## Vocabulary\n")
    gap = refuted or any(cells_of(totals(by_group))[0] != cells_of(totals(by_group))[1]
                         for by_group in cov.values())
    if not gap:
        for fam, by_group in cov.items():
            total, _w, _pct, _ = cells_of(totals(by_group))
            print(f"* **{fam}**: {total:,} pieces, all witnessed or structural.")
    else:
        print("Every piece must be witnessed or structural-special; specials are reported "
              "separately. See README.md.\n")
        for fam, by_group in cov.items():
            total, w, pct, _ = cells_of(totals(by_group))
            print(f"### {fam}: {w:,} of {total:,} witnessed or special ({pct})\n")
            rows = [[g, f"{total:,}", f"{w:,} ({pct})"]
                    + [f"{bucket[c]:,}" if bucket[c] else "·" for c in cols]
                    for g, counts in by_group.items()
                    for total, w, pct, bucket in [cells_of(counts)]]
            _table(rows, ["group", "pieces", "witnessed or special", *cols])
        if refuted:
            print(f"{sum(n for *_, n in refuted)} pieces are refuted by their own probe; "
                  f"remove them or replace them with fixed-template witnesses.\n")
    for line in _borrowers():
        print(f"* {line}.")
    print()


def witness_coverage() -> dict[str, dict[str, dict[str, int]]]:
    """Witness-kind counts by family and vocabulary group."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for key, doc in _owned_vocabularies():
        out[key] = {}
        for group, entries in doc["tokens"].items():
            counts: dict[str, int] = {}
            for w in entries.values():
                kind = w.get("kind", "?")
                counts[kind] = counts.get(kind, 0) + 1
            out[key][group] = counts
    return out


# The kinds that are not a witness. MISSING is an absence of evidence (unbought, or no template
# reaches the piece); UNRESOLVED is a conflict of evidence (the probe refutes the piece, so a
# second error is hiding nearby); SPECIAL is a marker atom, which is not text.
SPECIAL = ("special",)
MISSING = ("unmeasured", "no-instrument")
UNRESOLVED = ("refuted",)
GAP_KINDS = MISSING + UNRESOLVED + SPECIAL


def known_kinds() -> frozenset[str]:
    """Every kind a witness record may carry, derived from each vocabulary's own
    ``meta.witness.templates`` (a hand-written list goes stale, and an unknown kind must land in
    the `other` column, never on the witnessed side). `prefix` is added on top because `verify`
    dispatches it before the template lookup.
    """
    names: set[str] = set(GAP_KINDS) | {"prefix"}
    for _key, doc in _owned_vocabularies():
        names |= set(doc["meta"]["witness"]["templates"])
    return frozenset(names)


def witnessed(counts: dict[str, int]) -> int:
    """Pieces resting on a fixed approved template, plus the structural-special marker atoms."""
    accepted = known_kinds() - set(MISSING + UNRESOLVED)
    return sum(n for kind, n in counts.items() if kind in accepted)


def totals(by_group: dict[str, dict[str, int]]) -> dict[str, int]:
    """One family's per-kind counts, summed over its groups."""
    return {k: sum(g.get(k, 0) for g in by_group.values())
            for k in {k for g in by_group.values() for k in g}}


def _score_one(job: tuple[str, str]) -> tuple[str, str, dict]:
    name, family = job
    return name, family, score(name, family)


def report() -> None:
    """Check every gate and print a Markdown summary."""
    jobs = [(name, family) for name, cfg in GATES.items() for family in cfg["families"]]
    with ProcessPoolExecutor() as pool:
        scored = {(n, f): a for n, f, a in pool.map(_score_one, jobs)}
    for name, family in jobs:
        assert_gate(name, family, scored[(name, family)])

    families = list(dict.fromkeys(f for _, f in jobs))
    cov = {fam: cells_of(totals(by_group)) for fam, by_group in witness_coverage().items()}

    def cell(name: str, family: str) -> str:
        if family not in GATES[name]["families"]:
            return "n/a"
        return f"{scored[(name, family)]['exact']:,}"

    def wcell(family: str) -> str:
        if family not in cov:
            return "n/a"
        total, w, pct, _ = cov[family]
        return f"{total:,}" if w == total else f"{pct} of {total:,}"

    print("## Reproduction gates\n")
    print("Every document reproduced, against recorded `count_tokens` values.\n")
    _table([[fam] + [cell(n, fam) for n in GATES] + [wcell(fam)] for fam in families],
           ["family"] + [GATES[n]["title"] for n in GATES] + ["witness coverage"])


if __name__ == "__main__":
    report()
    report_vocabulary()
