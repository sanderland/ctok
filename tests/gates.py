"""Offline reproduction gates: score this tokenizer against recorded ``count_tokens`` values and
assert the aggregate accuracy holds. No API and no network — each fixture ships the corpus once
(``<name>.jsonl.gz``) plus one recorded count per family (``<name>_counts.json``).

Corpora:

  * UDHR — the Universal Declaration of Human Rights in 501 natural languages (parallel).
  * MultiPL-E — the same 25 HumanEval problems in 22 programming languages (parallel, held out:
    nothing may select, accept or reject a piece because of it).
  * Rosetta Code — 1,741 documents of real multi-language source (in-sample: mining bisects it),
    plus 250 from blocks the first sample never touched (out-of-sample for anything it chose).

UDHR was held out until 2026-08-12, when its last nine non-exact readings were closed by bisecting
the documents themselves; its rate is in-sample from that date and labeled so wherever quoted.

    relative error per document = (ours - recorded) / recorded

Run directly for a report: ``python tests/gates.py`` (or ``--markdown`` for a CI step summary).
"""

from __future__ import annotations

import gzip
import json
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tabulate import tabulate

from ctok.main import FAMILIES, _vocabulary, token_count

FIXTURES = Path(__file__).parent / "fixtures"

# Thresholds carry margin so ordinary per-piece churn passes but a real regression trips. ``None``
# means the metric is reported but not asserted. ``"exact": ALL`` asserts every document
# reproduces — the right gate once a corpus is finished, since any fractional threshold silently
# permits the first regression it was meant to catch.
ALL = "all"

# v5 is deliberately not gated here: it reads v4.7's vocabulary and differs only in its message
# frame, so it lands on the same documents with the same errors. The frame rules are pinned in
# `test_api.py`, and `test_v5_tracks_v4_7_document_for_document` asserts the equality this rests
# on; if v5 ever stops tracking v4.7, that test fails and v5 comes back into this table.
GATES: dict[str, dict] = {
    "udhr": {
        "title": "UDHR",
        "unit": "natural languages",
        "key": "f",
        "weight": "speakers",
        "n": 501,
        # Finished 2026-08-12: both families reproduce all 501 documents. In-sample from that
        # date (see the module docstring), but each of the final six pieces carries its own
        # fixed-template membership witness.
        "families": {
            "v3": {"version": "3.0", "mean": None, "within1": None, "exact": ALL},
            "v4.7": {"version": "4.7", "mean": None, "within1": None, "exact": ALL},
        },
    },
    "rosetta": {
        "title": "Rosetta Code",
        "unit": "documents",
        "key": "id",
        "weight": "chars",
        "n": 1741,
        # Finished: all families reproduce all 1,741 documents. When a deliberate change breaks
        # a file, the `known` allowlist in `assert_gate` holds the gate up while it is repaired.
        "families": {
            "v3": {"version": "3.0", "mean": None, "within1": None, "exact": ALL},
            "v4.7": {"version": "4.7", "mean": None, "within1": None, "exact": ALL},
        },
    },
    "rosetta_holdout": {
        "title": "Rosetta Code (held out)",
        "unit": "documents",
        "key": "id",
        "weight": "chars",
        "n": 250,
        # Documents that selected nothing: no piece in the vocabulary was probed because of
        # them. Finished.
        "families": {
            "v3": {"version": "3.0", "mean": None, "within1": None, "exact": ALL},
            "v4.7": {"version": "4.7", "mean": None, "within1": None, "exact": ALL},
        },
    },
    "multipl_e": {
        "title": "MultiPL-E",
        "unit": "programming languages",
        "key": "lang",
        "weight": "chars",
        "n": 22,
        # Finished: every family reproduces all 22 files.
        "families": {
            "v3": {"version": "3.0", "mean": None, "within1": None, "exact": ALL},
            "v4.7": {"version": "4.7", "mean": None, "within1": None, "exact": ALL},
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
    """Run this tokenizer over the corpus and aggregate the error against the recorded counts."""
    cfg = GATES[name]
    rows = corpus(name)
    counts = recorded(name, family)
    assert counts["model"] == FAMILIES[family].source_model, (
        f"{name} counts were measured on {counts['model']!r} but family {family!r} reconstructs "
        f"{FAMILIES[family].source_model!r} — wrong fixture for this family")

    version = cfg["families"][family]["version"]
    for r in rows:
        r["api"] = counts["counts"][r[cfg["key"]]]
        r["ours"] = token_count(r["text"], version=version)
        r["rel"] = (r["ours"] - r["api"]) / r["api"]
        r["abs"] = abs(r["rel"])

    total = sum(r[cfg["weight"]] for r in rows) or 1
    # The error buckets PARTITION the corpus, so the four counts always sum to n. Bounds are
    # inclusive on the right, which keeps ``exact + under1`` identical to the old |err| <= 1% gate.
    return {
        "rows": rows,
        "n": len(rows),
        "mass": sum(abs(r["ours"] - r["api"]) for r in rows) / sum(r["api"] for r in rows),
        "mean": statistics.mean(r["abs"] for r in rows),
        "weighted": sum(r[cfg["weight"]] * r["abs"] for r in rows) / total,
        "exact": sum(r["rel"] == 0 for r in rows),
        "under1": sum(0 < r["abs"] <= 0.01 for r in rows),
        "mid": sum(0.01 < r["abs"] <= 0.05 for r in rows),
        "over5": sum(r["abs"] > 0.05 for r in rows),
        "worst": max(rows, key=lambda r: r["abs"]),
    }


def assert_gate(name: str, family: str, agg: dict) -> None:
    """Apply the thresholds — shared by pytest and the standalone report. Thresholds stay
    *fractions* of the corpus, so they do not have to move when a corpus gains a document."""
    cfg = GATES[name]
    limits = cfg["families"][family]
    assert agg["n"] == cfg["n"], f"[{name}/{family}] corpus size changed: {agg['n']} != {cfg['n']}"
    assert agg["exact"] + agg["under1"] + agg["mid"] + agg["over5"] == agg["n"], "buckets must partition"
    exact, within1 = agg["exact"] / agg["n"], (agg["exact"] + agg["under1"]) / agg["n"]
    if limits["exact"] is ALL:
        # Failures are named, not counted. `known` is an allowlist of documents already understood
        # to fail, so a corpus keeps an every-document gate while carrying an open defect; a
        # document that starts reproducing again is also reported, so the list cannot rot.
        known = set(limits.get("known", ()))
        bad = [str(r.get("name") or r[cfg["key"]]) for r in agg["rows"] if r["rel"]]
        fixed = known - set(bad)
        assert not fixed, (f"[{name}/{family}] {sorted(fixed)} reproduce again — "
                           f"drop them from `known`")
        new = [b for b in bad if b not in known]
        assert not new, (f"[{name}/{family}] {len(new)} of {agg['n']} documents no longer "
                         f"reproduce: {', '.join(new[:8])}{' …' if len(new) > 8 else ''}")
        return
    if limits["mean"] is not None:
        assert agg["mean"] < limits["mean"], \
            f"[{name}/{family}] mean |rel err| regressed to {100 * agg['mean']:.3f}%"
    if limits["within1"] is not None:
        assert within1 > limits["within1"], \
            f"[{name}/{family}] within-1% dropped to {100 * within1:.1f}%"
    if limits["exact"] is not None:
        assert exact > limits["exact"], \
            f"[{name}/{family}] exact-match rate dropped to {100 * exact:.1f}%"


def vocabulary_owners() -> dict[str, str]:
    """family -> the family whose vocabulary file it counts with. Derived: two families borrow
    when they share a file, and the first family listed for a file owns it (v5 reads v4.7's)."""
    owner: dict[str, str] = {}
    for key, fam in FAMILIES.items():
        if fam.pieces is None:
            continue
        owner[key] = next(k for k, f in FAMILIES.items() if f.pieces == fam.pieces)
    return owner


def _owned_vocabularies():
    """Yield each physical vocabulary once, under the family that owns it."""
    for key, owner in vocabulary_owners().items():
        if owner == key:
            yield key, _vocabulary(key)


def vocabulary_sizes() -> dict[str, dict[str, int]]:
    """Piece counts per group, per vocabulary file — keyed by the family that owns it. A
    borrowing family is absent rather than listed with a copy of the lender's row."""
    return {key: {group: len(entries) for group, entries in doc["tokens"].items()}
            for key, doc in _owned_vocabularies()}


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
            print(f"* **{fam}** — {total:,} pieces, every one on a fixed template or "
                  f"structural-special.")
    else:
        print("Every piece must be witnessed or structural-special; specials are reported "
              "separately. See README.md.\n")
        for fam, by_group in cov.items():
            total, w, pct, _ = cells_of(totals(by_group))
            print(f"### {fam} — {w:,} of {total:,} witnessed or special ({pct})\n")
            rows = [[g, f"{total:,}", f"{w:,} ({pct})"]
                    + [f"{bucket[c]:,}" if bucket[c] else "·" for c in cols]
                    for g, counts in by_group.items()
                    for total, w, pct, bucket in [cells_of(counts)]]
            _table(rows, ["group", "pieces", "witnessed or special", *cols])
        if refuted:
            print(f"⚠️ {sum(n for *_, n in refuted)} pieces are refuted by their own probe — "
                  f"remove them or replace them with fixed-template witnesses.\n")
    for line in _borrowers():
        print(f"* {line}.")
    print()


def witness_coverage() -> dict[str, dict[str, dict[str, int]]]:
    """family -> group -> {witness kind: pieces}, per vocabulary file. Keyed like
    ``vocabulary_sizes``, and broken down by group because that is where a gap is actionable."""
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
    """Print every gate's numbers, applying the thresholds as we go. GitHub-flavored markdown is
    the one output format, for terminals and the CI step summary alike.

    A corpus every family reproduces document for document collapses into a single grid row; only
    a corpus with a residual gets its own table, so a corpus leaving the grid is itself the
    signal. Scored in a process pool — the (corpus, family) replays are independent.
    """
    jobs = [(name, family) for name, cfg in GATES.items() for family in cfg["families"]]
    with ProcessPoolExecutor() as pool:
        scored = {(n, f): a for n, f, a in pool.map(_score_one, jobs)}
    for name, family in jobs:
        assert_gate(name, family, scored[(name, family)])

    finished = [n for n, cfg in GATES.items()
                if all(scored[(n, f)]["exact"] == scored[(n, f)]["n"] for f in cfg["families"])]
    families = list(dict.fromkeys(f for _, f in jobs))
    cov = {fam: cells_of(totals(by_group)) for fam, by_group in witness_coverage().items()}

    def cell(name: str, family: str) -> str:
        if family not in GATES[name]["families"]:
            return "—"                        # no recorded counts for that family on that corpus
        return f"✅ {scored[(name, family)]['n']:,}"

    def wcell(family: str) -> str:
        if family not in cov:
            return "—"
        total, w, pct, _ = cov[family]
        return f"✅ {total:,}" if w == total else f"⚠️ {pct} of {total:,}"

    print("## Reproduction gates\n")
    print("Every document reproduced, against recorded `count_tokens` values.\n")
    _table([[fam] + [cell(n, fam) for n in finished] + [wcell(fam)] for fam in families],
           ["family"] + [GATES[n]["title"] for n in finished] + ["witness coverage"])

    for name in GATES:
        if name in finished:
            continue
        cfg = GATES[name]
        print(f"### {cfg['title']} — not finished\n")
        rows = []
        for family in cfg["families"]:
            a = scored[(name, family)]
            w = a["worst"]
            worst = str(w.get("name") or w[cfg["key"]])
            rows.append([family, a["n"], f"{100 * a['mass']:.3f}%", f"{100 * a['mean']:.3f}%",
                         a["exact"], a["under1"], a["mid"], a["over5"],
                         f"{worst} {100 * w['rel']:+.1f}%"])
        _table(rows, ["family", "docs", "error mass", "mean |err|",
                      "exact", "≤1%", "1–5%", ">5%", "worst"])


if __name__ == "__main__":
    report()                    # `--markdown` is accepted and ignored: markdown is the one format
    report_vocabulary()
