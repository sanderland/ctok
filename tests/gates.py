"""The two offline reproduction gates: score this tokenizer against recorded ``count_tokens`` values
over two parallel corpora, and assert the aggregate accuracy holds.

A *parallel* corpus holds the same content expressed in every language, so content is constant and
the counts vary only with the language:

  * **UDHR** — the Universal Declaration of Human Rights in 501 natural languages.
  * **MultiPL-E** — the same 25 HumanEval problems in 22 programming languages, translated by
    MultiPL-E's own translators (https://huggingface.co/datasets/nuprl/MultiPL-E).

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
        # Measured 2026-07-28. The honest residual is a Brahmic/South-East-Asian under-count: the
        # vocabulary has no pieces for those scripts and the byte floor is the entire model there.
        "families": {
            "v3": {"version": 3.0, "mean": 0.005, "within1": 0.91, "exact": 0.45},
            "v4.7": {"version": 4.7, "mean": 0.006, "within1": 0.88, "exact": 0.42},
        },
    },
    "multipl_e": {
        "title": "MultiPL-E",
        "unit": "programming languages",
        "key": "lang",
        "weight": "chars",
        "n": 22,
        # Measured 2026-07-28. v4.7 is well behind v3 here because its vocabulary is sparser, not
        # because it runs a different mechanism; ``exact`` is one file there, so asserting it would
        # measure luck.
        "families": {
            "v3": {"version": 3.0, "mean": 0.0012, "within1": 0.95, "exact": 0.35},
            "v4.7": {"version": 4.7, "mean": 0.006, "within1": 0.77, "exact": None},
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


def report(markdown: bool = False) -> None:
    """Print every gate's numbers, applying the thresholds as we go."""
    if markdown:
        print("## Reproduction gates\n")
        print("Documents by absolute error against recorded `count_tokens` values.\n")
        print("| corpus | family | docs | error mass | mean \\|err\\| "
              "| exact | ≤1% | 1–5% | >5% | worst |")
        print("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for name, cfg in GATES.items():
        for family in cfg["families"]:
            a = score(name, family)
            assert_gate(name, family, a)
            w = a["worst"]
            worst = f"{w['name']} {100 * w['rel']:+.1f}%"
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
                print(f"    {r['name'][:28]:28} ours={r['ours']:6} recorded={r['api']:6} "
                      f"rel={100 * r['rel']:+6.2f}%")
            print()


if __name__ == "__main__":
    import sys

    report(markdown="--markdown" in sys.argv)
