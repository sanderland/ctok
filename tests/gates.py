"""The two offline reproduction gates: score this tokenizer against recorded ``count_tokens`` values
over two parallel corpora, and assert the aggregate accuracy holds.

A *parallel* corpus holds the same content expressed in every language, so content is constant and
the counts vary only with the language:

  * **UDHR** — the Universal Declaration of Human Rights in 501 natural languages.
  * **MultiPL-E** — the same 25 HumanEval problems in 22 programming languages, translated by
    MultiPL-E's own translators (https://huggingface.co/datasets/nuprl/MultiPL-E).

Plus one corpus that is not parallel at all, and is here for the opposite reason — it is real,
unedited source in hundreds of languages, so it exercises the whole model rather than one axis:

  * **Rosetta Code** — 1,741 documents sampled from ``christopher/rosetta-code``, and a further 250
    drawn from blocks the first sample never touched. Every campaign bisects against the first, so
    its rate is in-sample by construction: pieces are accepted on membership probes rather than on
    documents, but the documents choose which candidates get probed. The 250 are out-of-sample for
    anything the 1,741 chose, which makes them the sharper accuracy reading; the in-sample gate is
    the sharper regression detector, and both are asserted.

**UDHR and MultiPL-E are the held-out gates and Rosetta is not.** Mining may bisect Rosetta freely;
nothing may select, accept or reject a piece because of UDHR or MultiPL-E. The dev repo's
``CLAUDE.md`` carries the same table, and it is the reason these two numbers mean anything.

Each fixture ships the corpus once (``<name>.jsonl.gz``) plus one recorded count per family
(``<name>_counts.json``) — the corpus text is identical across families, only the counts differ. No
API and no network: the counts were measured once against each family's source model.

    relative error per document = (ours - recorded) / recorded

Run directly for a report: ``python tests/gates.py`` (or ``--markdown`` for a CI step summary).
"""

from __future__ import annotations

import gzip
import json
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ctok.main import FAMILIES, token_count

FIXTURES = Path(__file__).parent / "fixtures"

# Thresholds carry margin so ordinary per-piece churn passes but a real regression trips. ``None``
# means the metric is reported but not asserted.
GATES: dict[str, dict] = {
    "udhr": {
        "title": "UDHR",
        "unit": "natural languages",
        "key": "f",
        "weight": "speakers",
        "n": 501,
        # Measured 2026-08-01, after the akshara law and the cluster re-spelling. The law took the
        # Brahmic/South-East-Asian under-count out structurally — no document in either family is
        # over 5% now, where 15 in each were — and the re-spelling took most of what was left. These
        # are four times tighter than the thresholds that preceded both, and a revert of either
        # trips every one of them. What remains is unmined vocabulary.
        "families": {
            "v3": {"version": 3.0, "mean": 0.0022, "within1": 0.95, "exact": 0.53},
            "v4.7": {"version": 4.7, "mean": 0.0020, "within1": 0.95, "exact": 0.57},
            # v5 reads the v4.7 vocabulary through its own measured frame and lands on the SAME
            # documents: the residual here is the Brahmic/South-East-Asian one, shared whole.
            "v5": {"version": 5.0, "mean": 0.0020, "within1": 0.95, "exact": 0.57},
        },
    },
    "rosetta": {
        "title": "Rosetta Code",
        "unit": "documents",
        "key": "id",
        "weight": "chars",
        "n": 1741,
        # Measured 2026-08-01. v4.7 reproduces every document; the floor is set just under so that
        # a single regressing document trips it. v3 still carries a vocabulary tail.
        "families": {
            "v3": {"version": 3.0, "mean": 0.0009, "within1": 0.96, "exact": 0.87},
            "v4.7": {"version": 4.7, "mean": 0.0001, "within1": 0.995, "exact": 0.995},
            # v5 reproduces every document too, once its own frame rules are modelled — the two
            # families differ at the message edges and nowhere else this corpus can see.
            "v5": {"version": 5.0, "mean": 0.0001, "within1": 0.995, "exact": 0.995},
        },
    },
    "rosetta_holdout": {
        "title": "Rosetta Code (held out)",
        "unit": "documents",
        "key": "id",
        "weight": "chars",
        "n": 250,
        # Documents that selected nothing: no piece in the vocabulary was probed because of them.
        # Measured 2026-08-01 at 99.6% exact / 0.006% mass, against 89.6% / 0.096% for the model
        # shipped before the apostrophe work. v3 has no held-out sample measured yet. The akshara
        # law moved this by exactly one document, which is all it could move: two of the 250 hold a
        # killer at all, and one of those two is the document that flipped. `►⟨eow⟩` took the
        # second, leaving one — a Unicode-notation file where the same marked span costs 3 after a
        # word boundary and 2 after a symbol's last byte, which no single piece covers.
        "families": {
            "v4.7": {"version": 4.7, "mean": 0.0002, "within1": 0.99, "exact": 0.97},
            # The same documents as v4.7, and no others.
            "v5": {"version": 5.0, "mean": 0.0002, "within1": 0.99, "exact": 0.97},
        },
    },
    "multipl_e": {
        "title": "MultiPL-E",
        "unit": "programming languages",
        "key": "lang",
        "weight": "chars",
        "n": 22,
        # Measured 2026-08-01. v4.7 reproduces all 22 files exactly since the word-opening
        # apostrophe, the contraction's word-side anchor and the space-spelled punct duplicates
        # landed, so ``exact`` is asserted there — it used to be one file, where asserting it would
        # have measured luck. v3 (15/22) still carries a vocabulary tail. Thresholds are compared
        # with a STRICT >, so a perfect corpus cannot be gated at 1.0.
        "families": {
            "v3": {"version": 3.0, "mean": 0.0012, "within1": 0.95, "exact": 0.55},
            "v4.7": {"version": 4.7, "mean": 0.0005, "within1": 0.99, "exact": 0.90},
            "v5": {"version": 5.0, "mean": 0.0005, "within1": 0.99, "exact": 0.90},
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
    """family -> the family whose vocabulary FILE it counts with (itself, unless it borrows one).

    Two families sharing a file is what borrowing IS, so this is derived rather than declared. The
    first family listed for a file owns it; v5 reads v4.7's."""
    from ctok.main import FAMILIES

    owner: dict[str, str] = {}
    for key, fam in FAMILIES.items():
        if fam.pieces is None:
            continue
        owner[key] = next(k for k, f in FAMILIES.items() if f.pieces == fam.pieces)
    return owner


def vocabulary_sizes() -> dict[str, dict[str, int]]:
    """Piece counts per group, per vocabulary FILE — keyed by the family that owns it.

    A borrowing family is deliberately absent rather than listed with a copy of the lender's row:
    repeating the numbers reads as two vocabularies that happen to agree, when there is one file
    and no second measurement behind the second row."""
    import json

    from ctok.main import FAMILIES
    from importlib.resources import files

    out: dict[str, dict[str, int]] = {}
    for key, owner in vocabulary_owners().items():
        if owner != key:
            continue
        doc = json.loads(
            files("ctok").joinpath("data", FAMILIES[key].pieces).read_text(encoding="utf-8"))
        out[key] = {g: len(v) for g, v in doc["tokens"].items()}
    return out


def _borrowers() -> list[str]:
    """One line per family that counts with someone else's file — so the report says so out loud
    rather than leaving a family it never mentioned to look like an omission."""
    from ctok.main import FAMILIES

    return [f"{key} counts with {owner}'s vocabulary ({FAMILIES[key].pieces})"
            for key, owner in vocabulary_owners().items() if owner != key]


def report_vocabulary(markdown: bool = False) -> None:
    """Piece counts by group, and what share of each group carries a witness.

    Two regressions the error gates cannot name, in one table: a silently emptied or ballooning
    group, and a group whose pieces stopped being backed by measurements. They belong in the same
    table because the second is only actionable per group — an unwitnessed piece counts exactly like
    a witnessed one, so every accuracy number is identical either way and only this says so.
    """
    cov = witness_coverage()
    groups = sorted({g for fam in cov.values() for g in fam})
    # Every gap kind, so each row adds up: pieces = witnessed + the columns. `structural` is the
    # byte fallback, which shows 0 witnessed and always will — prefixes are not tokens.
    cols = GAP_KINDS

    def cells(counts: dict[str, int]) -> tuple[int, int, str]:
        total, w = sum(counts.values()), witnessed(counts)
        return total, w, f"{100 * w / total:.1f}%" if total else "n/a"

    if markdown:
        print("\n## Vocabulary and witness coverage by group\n")
        print("Every piece carries the probe that pins it at one token "
              "(`cost = raw − base + 1 − overhead`, and `cost == 1` is membership). See PROBES.md.\n")
        print("| family | group | pieces | witnessed | " + " | ".join(cols) + " |")
        print("|---" * (len(cols) + 4) + "|")
        for fam, by_group in cov.items():
            whole = totals(by_group)
            total, w, pct = cells(whole)
            gaps = " | ".join(f"{whole.get(c, 0):,}" for c in cols)
            print(f"| **{fam}** | *all groups* | **{total:,}** | **{w:,}** ({pct}) | {gaps} |")
            for g in groups:
                if g not in by_group:
                    continue
                total, w, pct = cells(by_group[g])
                gaps = " | ".join(f"{by_group[g].get(c, 0):,}" for c in cols)
                print(f"| {fam} | {g} | {total:,} | {w:,} ({pct}) | {gaps} |")
        for line in _borrowers():
            print(f"\n{line}.")
        return
    print("Vocabulary and witness coverage by group\n")
    for fam, by_group in cov.items():
        total, w, pct = cells(totals(by_group))
        print(f"  [{fam}] {w:,} of {total:,} pieces witnessed ({pct})")
        for g in groups:
            if g not in by_group:
                continue
            total, w, pct = cells(by_group[g])
            gaps = "  ".join(f"{c}={by_group[g][c]:,}" for c in cols if by_group[g].get(c))
            print(f"    {g:16} {total:>7,}  witnessed {w:>7,} ({pct:>6})   {gaps}")
    for line in _borrowers():
        print(f"  {line}")
    print()


def witness_coverage() -> dict[str, dict[str, dict[str, int]]]:
    """family -> group -> {witness kind: pieces}, per vocabulary FILE.

    Keyed like ``vocabulary_sizes``: one row per file, so a borrowing family is absent rather than
    listed with a copy of the lender's numbers it did not measure. Broken down by GROUP because that
    is where a gap is actionable — "845 unwitnessed" is a number, "845 of them in word_pieces" is a
    campaign.
    """
    import json
    from importlib.resources import files

    from ctok.main import FAMILIES

    out: dict[str, dict[str, dict[str, int]]] = {}
    for key, owner in vocabulary_owners().items():
        if owner != key:
            continue
        doc = json.loads(
            files("ctok").joinpath("data", FAMILIES[key].pieces).read_text(encoding="utf-8"))
        out[key] = {}
        for group, entries in doc["tokens"].items():
            counts: dict[str, int] = {}
            for w in entries.values():
                kind = "structural" if w is None else w.get("kind", "?")
                counts[kind] = counts.get(kind, 0) + 1
            out[key][group] = counts
    return out


# The kinds that are NOT a witness. `structural` is the byte fallback — prefixes rather than tokens,
# so there is nothing to ask about and never will be; the rest are gaps with a reason attached.
GAP_KINDS = ("unmeasured", "no-instrument", "context-bound", "refuted", "structural")


def witnessed(counts: dict[str, int]) -> int:
    """How many of ``counts`` carry a probe."""
    return sum(counts.values()) - sum(counts.get(k, 0) for k in GAP_KINDS)


def totals(by_group: dict[str, dict[str, int]]) -> dict[str, int]:
    """One family's per-kind counts, summed over its groups."""
    return {k: sum(g.get(k, 0) for g in by_group.values())
            for k in {k for g in by_group.values() for k in g}}


def _score_one(job: tuple[str, str]) -> tuple[str, str, dict]:
    name, family = job
    return name, family, score(name, family)


def report(markdown: bool = False) -> None:
    """Print every gate's numbers, applying the thresholds as we go.

    The corpora are scored in a process pool: there are eight independent (corpus, family) replays
    and the biggest of them is most of the wall clock, so running them sequentially is the slowest
    thing in CI for no reason. Results are collected into a dict and printed in GATES order, so the
    report is byte-identical to the sequential one.
    """
    jobs = [(name, family) for name, cfg in GATES.items() for family in cfg["families"]]
    with ProcessPoolExecutor() as pool:
        scored = {(n, f): a for n, f, a in pool.map(_score_one, jobs)}
    if markdown:
        print("## Reproduction gates\n")
        print("Documents by absolute error against recorded `count_tokens` values.\n")
        print("| corpus | family | docs | error mass | mean \\|err\\| "
              "| exact | ≤1% | 1–5% | >5% | worst |")
        print("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for name, cfg in GATES.items():
        for family in cfg["families"]:
            a = scored[(name, family)]
            assert_gate(name, family, a)
            def label(row: dict) -> str:
                """A parallel corpus names its rows (`Bash`, `lang_ru`); Rosetta's are anonymous
                documents, so fall back to the key the counts are stored under."""
                return str(row.get("name") or row[cfg["key"]])

            w = a["worst"]
            worst = f"{label(w)} {100 * w['rel']:+.1f}%"
            if markdown:
                print(f"| {cfg['title']} | {family} | {a['n']} | {100 * a['mass']:.3f}% "
                      f"| {100 * a['mean']:.3f}% | {a['exact']} | {a['under1']} | {a['mid']} "
                      f"| {a['over5']} | {worst} |")
                continue
            print(f"{cfg['title']} [{family}] — {a['n']} {cfg['unit']}\n")
            print(f"  error mass          {100 * a['mass']:.3f}%")
            print(f"  mean |err|          {100 * a['mean']:.3f}%")
            print(f"  {cfg['weight']}-weighted  {100 * a['weighted']:.3f}%")
            print(f"  exact {a['exact']}   ≤1% {a['under1']}   1–5% {a['mid']}   >5% {a['over5']}\n")
            print("  worst documents:")
            for r in sorted(a["rows"], key=lambda r: -r["abs"])[:8]:
                print(f"    {label(r)[:28]:28} ours={r['ours']:6} recorded={r['api']:6} "
                      f"rel={100 * r['rel']:+6.2f}%")
            print()


if __name__ == "__main__":
    import sys

    md = "--markdown" in sys.argv
    report(markdown=md)
    report_vocabulary(markdown=md)
