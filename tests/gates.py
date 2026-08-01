"""The two offline reproduction gates: score this tokenizer against recorded ``count_tokens`` values
over two parallel corpora, and assert the aggregate accuracy holds.

A *parallel* corpus holds the same content expressed in every language, so content is constant and
the counts vary only with the language:

  * **UDHR** — the Universal Declaration of Human Rights in 501 natural languages.
  * **MultiPL-E** — the same 25 HumanEval problems in 22 programming languages, translated by
    MultiPL-E's own translators (https://huggingface.co/datasets/nuprl/MultiPL-E).

Plus one corpus that is not parallel at all, and is here for the opposite reason — it is real,
unedited source in hundreds of languages, so it exercises the whole model rather than one axis:

  * **Rosetta Code** — 1,741 documents sampled from ``christopher/rosetta-code``, and a **held-out**
    250 drawn from blocks the first sample never touched. Every campaign bisects against the first
    one, so its rate is in-sample by construction: pieces are accepted on membership probes rather
    than on documents, but the documents choose which candidates get probed. The held-out gate is
    the honest one; the in-sample gate is the sharp regression detector, and both are asserted.

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
        # Measured 2026-08-01. The honest residual is a Brahmic/South-East-Asian under-count: the
        # vocabulary has no pieces for those scripts and the byte floor is the entire model there.
        "families": {
            "v3": {"version": 3.0, "mean": 0.005, "within1": 0.91, "exact": 0.45},
            "v4.7": {"version": 4.7, "mean": 0.005, "within1": 0.90, "exact": 0.52},
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
        },
    },
    "rosetta_holdout": {
        "title": "Rosetta Code (held out)",
        "unit": "documents",
        "key": "id",
        "weight": "chars",
        "n": 250,
        # Documents that selected nothing: no piece in the vocabulary was probed because of them.
        # Measured 2026-08-01 at 98.8% exact / 0.013% mass, against 89.6% / 0.096% for the model
        # shipped before the apostrophe work. v3 has no held-out sample measured yet.
        "families": {
            "v4.7": {"version": 4.7, "mean": 0.0003, "within1": 0.98, "exact": 0.95},
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


def vocabulary_sizes() -> dict[str, dict[str, int]]:
    """Piece counts per group per family, straight from the shipped files."""
    import json

    from ctok.main import FAMILIES
    from importlib.resources import files

    out: dict[str, dict[str, int]] = {}
    for key, fam in FAMILIES.items():
        if fam.pieces is None:
            continue
        doc = json.loads(files("ctok").joinpath("data", fam.pieces).read_text(encoding="utf-8"))
        out[key] = {g: len(v) for g, v in doc["tokens"].items()}
    return out


def report_vocabulary(markdown: bool = False) -> None:
    """Report each family's piece counts by group — a silently emptied or ballooning group is a
    vocabulary regression the error gates alone would not name."""
    sizes = vocabulary_sizes()
    groups = sorted({g for fam in sizes.values() for g in fam})
    if markdown:
        print("\n## Vocabulary size by group\n")
        print("| family | " + " | ".join(groups) + " | total |")
        print("|---" * (len(groups) + 2) + "|")
        for fam, counts in sizes.items():
            cells = " | ".join(f"{counts.get(g, 0):,}" for g in groups)
            print(f"| {fam} | {cells} | {sum(counts.values()):,} |")
        return
    print("Vocabulary size by group\n")
    for fam, counts in sizes.items():
        print(f"  [{fam}] total {sum(counts.values()):,}")
        for g in groups:
            print(f"    {g:16} {counts.get(g, 0):>7,}")
    print()


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
            w = a["worst"]
            # A parallel corpus names its rows (`Bash`, `lang_ru`); Rosetta's are anonymous
            # documents, so fall back to the key the counts are stored under.
            worst = f"{w.get('name') or w[cfg['key']]} {100 * w['rel']:+.1f}%"
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

    md = "--markdown" in sys.argv
    report(markdown=md)
    report_vocabulary(markdown=md)
