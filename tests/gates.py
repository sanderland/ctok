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

MultiPL-E is the held-out gate and Rosetta is not. Mining may bisect Rosetta freely; nothing may
select, accept or reject a piece because of MultiPL-E. UDHR was held out until 2026-08-12, when its
last nine non-exact readings were closed by bisecting the documents themselves — six pieces selected
off the gate, each accepted on its own fixed-template membership witness. Its rate is in-sample from
that date, and is labeled so wherever it is quoted. The dev repo's ``CLAUDE.md`` carries the same
table, and it is the reason these numbers mean what they say.

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

from ctok.main import FAMILIES, _vocabulary, token_count

FIXTURES = Path(__file__).parent / "fixtures"

# Thresholds carry margin so ordinary per-piece churn passes but a real regression trips. ``None``
# means the metric is reported but not asserted.
#
# ``"exact": ALL`` asserts that every document reproduces, the right gate once a corpus is
# finished. A fraction, however tight, has to sit strictly below the real rate to leave room for
# churn, which means it silently permits the first regression it was meant to catch. ``mean`` and ``within1`` go ``None`` alongside it, since a corpus with no
# error has nothing left for them to measure.
ALL = "all"

# v5 is deliberately not gated here. It reads v4.7's vocabulary
# and differs only in its message frame, so on every corpus below it lands on exactly the same
# documents with exactly the same errors — scoring it doubled the gate's cost to re-derive numbers
# that were equal by construction. What actually guards it is cheaper and more direct: the frame
# rules are pinned on constructed strings in `test_api.py`, and
# `test_v5_tracks_v4_7_document_for_document` asserts the equality this omission rests on, over real
# documents of the corpora below and against both families' recorded counts. If v5 ever stops
# tracking v4.7, that test fails and v5 comes back into this table.
GATES: dict[str, dict] = {
    "udhr": {
        "title": "UDHR",
        "unit": "natural languages",
        "key": "f",
        "weight": "speakers",
        "n": 501,
        # Finished 2026-08-12: both families reproduce all 501 documents, so the gate is every
        # document. The final six pieces were selected by bisecting the gate's own documents —
        # UDHR is in-sample from that date (see the module docstring) — but selection is not
        # acceptance: each piece carries its own fixed-template membership witness in
        # `pieces_*.json`, and the corpus court passed it (65 cached rows repaired, none broken,
        # none pushed below).
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
        # Finished: all three families reproduce all 1,741 documents, so the gate is every document
        # rather than a rate. When a deliberate change does break a file, the `known` allowlist in
        # `assert_gate` holds the gate up while it is repaired — the gate is never lowered to a
        # rate, which would silently permit the next regression as well.
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
        # Documents that selected nothing: no piece in the vocabulary was probed because of them.
        # Finished, and gated at every document: `exact: 0.99` on 250 documents would silently
        # permit the next two regressions.
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
        # Finished: every family reproduces all 22 files, so the gate is every file.
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
        # Named rather than counted: "3 of 1741 documents regressed" is the report a reader wants,
        # and an exact-rate percentage rounds the first regression out of sight.
        #
        # `known` is an allowlist of documents already understood to fail, named one by one. It is
        # how a corpus keeps an every-document gate while carrying an open defect: dropping the gate
        # to a rate to accommodate one document would silently readmit the next eight. A document
        # that starts reproducing is also reported, so the list cannot rot into a wish.
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
    """family -> the family whose vocabulary file it counts with (itself, unless it borrows one).

    Derived rather than declared: two families borrow when they share a file. The
    first family listed for a file owns it; v5 reads v4.7's."""
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
    """Piece counts per group, per vocabulary file — keyed by the family that owns it.

    A borrowing family is deliberately absent rather than listed with a copy of the lender's row:
    repeating the numbers reads as two vocabularies that happen to agree, when there is one file
    and no second measurement behind the second row."""
    return {key: {group: len(entries) for group, entries in doc["tokens"].items()}
            for key, doc in _owned_vocabularies()}


def _borrowers() -> list[str]:
    """One line per family that counts with someone else's file, so the report says so
    rather than leaving that family to look like an omission."""
    return [f"{key} counts with {owner}'s vocabulary ({FAMILIES[key].pieces})"
            for key, owner in vocabulary_owners().items() if owner != key]


def _breaches(cov: dict[str, dict[str, dict[str, int]]], kind: str) -> list[tuple[str, str, int]]:
    """``(family, group, count)`` for every group holding pieces of one gap kind."""
    return [(fam, g, c[kind]) for fam, by_group in cov.items()
            for g, c in by_group.items() if c.get(kind)]


def cells_of(counts: dict[str, int]) -> tuple[int, int, str, dict[str, int]]:
    """``(pieces, witnessed-or-special, percentage, the gaps by kind)`` for one set of counts.

    Module level rather than a closure because :func:`report` needs the same arithmetic for the
    single coverage cell it prints, and two copies of it would be free to drift apart.
    """
    known = known_kinds()
    total, w = sum(counts.values()), witnessed(counts)
    bucket = {"missing": sum(counts.get(k, 0) for k in MISSING),
              "unresolved": sum(counts.get(k, 0) for k in UNRESOLVED),
              "special": sum(counts.get(k, 0) for k in SPECIAL),
              "other": sum(n for k, n in counts.items() if k not in known)}
    pct = "100%" if w == total else (f"{100 * w / total:.2f}%" if total else "n/a")
    return total, w, pct, bucket


def report_vocabulary(markdown: bool = False) -> None:
    """Piece counts by group, and what share of each group carries a witness.

    Two regressions the error gates cannot name, in one table: a silently emptied or ballooning
    group, and a group whose pieces stopped being backed by measurements. They belong in the same
    table because the second is only actionable per group — an unwitnessed piece counts exactly like
    a witnessed one, so every accuracy number is identical either way and only this says so.

    The two evidence gaps are ABSENT (missing: unbought, or unreachable by any template) and
    CONTRADICTORY (unresolved: the probe and the corpus disagree). ``special`` and ``other`` keep
    structural atoms and unknown kinds visible without presenting either as token evidence.
    """
    cov = witness_coverage()
    groups = sorted({g for fam in cov.values() for g in fam})
    # Every kind the numerator withholds needs a column, or the table shows a rate below 100% with
    # nothing to explain it. `other` is the same guarantee for a kind nobody has classified yet:
    # unknown kinds used to fall through to the witnessed side, which is the direction that
    # flatters.
    cols = ("missing", "unresolved", "special", "other")
    cells = cells_of
    refuted = _breaches(cov, "refuted")

    # At 100% on every file this table is one number per group and four columns of dots, and
    # `report` already prints that number. Print the breakdown when it has something to say — a gap
    # anywhere, or a piece its own probe refutes — and the summary line otherwise.
    gap = refuted or any(cells(totals(by_group))[0] != cells(totals(by_group))[1]
                         for by_group in cov.values())
    if not gap:
        if markdown:
            print("\n## Vocabulary\n")
            for fam, by_group in cov.items():
                total, w, pct, _ = cells(totals(by_group))
                print(f"* **{fam}** — {total:,} pieces, every one on a fixed template or "
                      f"structural-special.")
            for line in _borrowers():
                print(f"* {line}.")
            print()
        else:
            for fam, by_group in cov.items():
                total, _, _, _ = cells(totals(by_group))
                print(f"  [{fam}] {total:,} pieces, all witnessed or special")
            for line in _borrowers():
                print(f"  {line}")
            print()
        return

    if markdown:
        print("\n## Vocabulary and witness coverage\n")
        print("Every piece must be witnessed or structural-special. Token witnesses carry the "
              "measurements that pin them; specials are reported separately. See README.md.\n")
        for fam, by_group in cov.items():
            total, w, pct, bucket = cells(totals(by_group))
            print(f"### {fam} — {w:,} of {total:,} witnessed or special ({pct})\n")
            print("| group | pieces | witnessed or special | " + " | ".join(cols) + " |")
            print("|---" * (len(cols) + 3) + "|")
            for g in groups:
                if g not in by_group:
                    continue
                total, w, pct, bucket = cells(by_group[g])
                gaps = " | ".join(f"{bucket[c]:,}" if bucket[c] else "·" for c in cols)
                print(f"| {g} | {total:,} | {w:,} ({pct}) | {gaps} |")
            print()
        for line in _borrowers():
            print(f"\n{line}.")
        return

    print("Vocabulary and witness coverage by group\n")
    for fam, by_group in cov.items():
        tot = totals(by_group)
        total, w, pct, _ = cells(tot)
        print(f"  [{fam}] {w:,} of {total:,} pieces on a fixed template or special ({pct})")
        for g in groups:
            if g not in by_group:
                continue
            total, w, pct, bucket = cells(by_group[g])
            gaps = "  ".join(f"{c}={n:,}" for c, n in bucket.items() if n)
            print(f"    {g:16} {total:>7,}  accounted {w:>7,} ({pct:>6})   {gaps}")
    if refuted:
        print(f"\n  !! {sum(n for *_, n in refuted)} pieces REFUTED by their own probe:")
        for fam, g, n in refuted:
            print(f"       {fam} {g} ({n})   -> remove or replace with a fixed-template witness")
    for line in _borrowers():
        print(f"  {line}")
    print()


def witness_coverage() -> dict[str, dict[str, dict[str, int]]]:
    """family -> group -> {witness kind: pieces}, per vocabulary file.

    Keyed like ``vocabulary_sizes``: one row per file, so a borrowing family is absent rather than
    listed with a copy of the lender's numbers it did not measure. Broken down by GROUP because that
    is where a gap is actionable — "845 unwitnessed" is a number, "845 of them in word_pieces" is a
    campaign.
    """
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


# The kinds that are not a witness, in two groups that mean different things to a reader.
#
# MISSING is an absence of evidence: nobody has bought the measurement (`unmeasured`) or no template
# in the inventory reaches the piece (`no-instrument`). Both are work.
#
# UNRESOLVED is a CONFLICT of evidence: the probe refuses a piece outright and nothing has retired
# it yet (`refuted`). That means a second error is hiding nearby, which is why it is not folded in
# with the merely unmeasured.
# Neither evidence nor a gap: a marker atom (`⟨bow⟩`) is not text, so no probe can contain it.
SPECIAL = ("special",)
MISSING = ("unmeasured", "no-instrument")
UNRESOLVED = ("refuted",)
GAP_KINDS = MISSING + UNRESOLVED + SPECIAL


def known_kinds() -> frozenset[str]:
    """Every kind a witness record may carry, derived from the files rather than listed here.

    `witnessed` subtracts the known non-witness kinds from the total, so a kind it has never heard
    of lands silently on the witnessed side — the one direction a coverage number must never round.
    The guard is only as good as its list, and a hand-written list goes stale: one missed
    `digit_bow` — a shipped template carrying 28 v3 punctuation
    pieces — so the template names now come from each vocabulary's own `meta.witness.templates`,
    the same place `verify` reads them. `prefix` is added on top because `verify` dispatches it
    before that lookup: 467 byte-fallback pieces per file rest on it and no template declares it.
    Anything outside the union is reported in the `other` column instead of passing as evidence.
    """
    # `verify` dispatches `prefix` before the template lookup — a byte-prefix piece is pinned by
    # three characters agreeing, not by a probe string, so it is a real witness with no template.
    # It is named here because `witness.verify` names it, which is the only authority on what a
    # witness kind is.
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


def report(markdown: bool = False) -> None:
    """Print every gate's numbers, applying the thresholds as we go.

    A corpus every family reproduces document for document gets one cell, not a table. Three of
    the four are finished, and a finished corpus has exactly one thing to say — a per-document error
    breakdown of a corpus with no error is nine columns of zeroes, and the one line that still
    carries information (UDHR's) was buried under them. So the finished corpora collapse into a
    single grid, one row per family, and only a corpus with a residual gets its documents listed.

    A corpus leaving the grid is itself the signal: it means some document stopped reproducing.

    The corpora are scored in a process pool: there are eight independent (corpus, family) replays
    and the biggest of them is most of the wall clock, so running them sequentially is the slowest
    thing in CI for no reason.
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

    head = [GATES[n]["title"] for n in finished] + ["witness coverage"]
    rows = [[fam] + [cell(n, fam) for n in finished] + [wcell(fam)] for fam in families]
    if markdown:
        print("## Reproduction gates\n")
        print("Every document reproduced, against recorded `count_tokens` values.\n")
        print("| family | " + " | ".join(head) + " |")
        print("|---" * (len(head) + 1) + "|")
        for r in rows:
            print("| " + " | ".join(r) + " |")
        print()
    else:
        # ✅ and ⚠️ are one character to `len` and two columns to a terminal, so pad on the
        # rendered width or the grid comes out ragged exactly where the marks are.
        def shown(s: str) -> int:
            return len(s) + sum(c in "✅⚠️" for c in s)

        def pad(s: str, w: int) -> str:
            return s + " " * max(w - shown(s), 0)

        width = max(max(shown(h) for h in head), max(shown(c) for r in rows for c in r[1:])) + 2
        print("Reproduction gates — every document exact\n")
        print("  " + " " * 7 + "".join(pad(h, width) for h in head).rstrip())
        for r in rows:
            print("  " + pad(r[0], 7) + "".join(pad(c, width) for c in r[1:]).rstrip())
        print()

    for name in GATES:
        if name in finished:
            continue
        cfg = GATES[name]
        if markdown:
            print(f"### {cfg['title']} — not finished\n")
            print("| family | docs | error mass | mean \\|err\\| | exact | ≤1% | 1–5% | >5% | worst |")
            print("|---|---:|---:|---:|---:|---:|---:|---:|---|")
        for family in cfg["families"]:
            a = scored[(name, family)]

            def label(row: dict) -> str:
                """A parallel corpus names its rows (`Bash`, `lang_ru`); Rosetta's are anonymous
                documents, so fall back to the key the counts are stored under."""
                return str(row.get("name") or row[cfg["key"]])

            w = a["worst"]
            worst = f"{label(w)} {100 * w['rel']:+.1f}%"
            if markdown:
                print(f"| {family} | {a['n']} | {100 * a['mass']:.3f}% "
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
