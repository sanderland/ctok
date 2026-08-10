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
#
# ``"exact": ALL`` is not a threshold at all — it asserts that EVERY document reproduces, and it is
# the right gate once a corpus is finished. A fraction, however tight, has to sit strictly below the
# real rate to leave room for churn, which means it silently permits the first regression it was
# meant to catch. Nothing to spare is the whole point: a corpus at 100% has one failure mode, and it
# is any document at all. ``mean`` and ``within1`` go ``None`` alongside it, since a corpus with no
# error has nothing left for them to measure.
ALL = "all"

# **v5 is not gated here, and that is a claim rather than an omission.** It reads v4.7's vocabulary
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
        # Re-measured 2026-08-07 against the readings this model actually produces: 313/501 exact
        # and 0.107% mean on v3, 363/501 and 0.064% on v4.7. The thresholds that stood here were set
        # before the terminal-mark spelling and had drifted a long way clear of the model — v3 was
        # gated at 53% while reading 62% — so they had stopped being able to catch anything. This is
        # the only corpus left with a residual, and it is unmined vocabulary rather than structure.
        "families": {
            "v3": {"version": 3.0, "mean": 0.0020, "within1": 0.94, "exact": 0.61},
            # Re-measured 2026-08-08 TWICE. The Goldfish word campaign took v4.7 to 448/501 exact
            # and 0.043% mean. Retiring `ownscript` then gave 439, and removing the five pieces
            # that glued a virama to a space gave 430. Both are deliberate steps backwards: a piece
            # that is not a token cannot stay because it happens to help. Each converts a hidden
            # error into an honest over-count, which is a thing that can be mined. UDHR selected
            # none of it either way.
            "v4.7": {"version": 4.7, "mean": 0.0011, "within1": 0.95, "exact": 0.86},
        },
    },
    "rosetta": {
        "title": "Rosetta Code",
        "unit": "documents",
        "key": "id",
        "weight": "chars",
        "n": 1741,
        # FINISHED, 2026-08-07: all three families reproduce all 1,741 documents, so the gate is
        # every document rather than a rate. v3 was the last to close — it carried a vocabulary tail
        # through the apostrophe and akshara work and reads exact since the terminal-mark spelling.
        # Still every document on all three families through the `ownscript` retirement. One file
        # did break when 439 refuted pieces were removed, and it came back when the single-codepoint
        # ones among them were re-asked on the `char` template instead of the ヲ grid — the `known`
        # allowlist in `assert_gate` held the gate up in between rather than lowering it to a rate.
        "families": {
            "v3": {"version": 3.0, "mean": None, "within1": None, "exact": ALL},
            "v4.7": {"version": 4.7, "mean": None, "within1": None, "exact": ALL},
        },
    },
    "rosetta_holdout": {
        "title": "Rosetta Code (held out)",
        "unit": "documents",
        "key": "id",
        "weight": "chars",
        "n": 250,
        # Documents that selected nothing: no piece in the vocabulary was probed because of them.
        # 249 of 250 since the apostrophe work, against 89.6% for the model before it; v3 has no
        # held-out sample measured yet. This is the one corpus NOT gated at every document, and the
        # remaining one is a Swift file of Unicode escapes where a combining mark sits on U+25CC
        # DOTTED CIRCLE. That is a stream-spelling question, not a missing piece — see LIMITS.md —
        # so the gate stays a rate until the spelling is settled rather than pretending a threshold
        # is a target.
        "families": {
            # `mean` sits at 0.00015 rather than hard against the 0.00009 reading: this corpus has
            # ONE failing document, so its mean is that document's error alone and a spelling change
            # anywhere moves it in whole tokens. A margin that tight measures the spelling, not a
            # regression. The `exact` floor is what actually guards this corpus.
            "v4.7": {"version": 4.7, "mean": 0.00015, "within1": 0.99, "exact": 0.99},
        },
    },
    "multipl_e": {
        "title": "MultiPL-E",
        "unit": "programming languages",
        "key": "lang",
        "weight": "chars",
        "n": 22,
        # FINISHED, 2026-08-07: every family reproduces all 22 files, so the gate is every file.
        # v4.7 closed first, with the word-opening apostrophe, the contraction's word-side anchor
        # and the space-spelled punct duplicates; v3 followed on the same vocabulary work that
        # closed Rosetta for it.
        "families": {
            "v3": {"version": 3.0, "mean": None, "within1": None, "exact": ALL},
            "v4.7": {"version": 4.7, "mean": None, "within1": None, "exact": ALL},
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


def _breaches(cov: dict[str, dict[str, dict[str, int]]], kind: str) -> list[tuple[str, str, int]]:
    """``(family, group, count)`` for every group holding pieces of one gap kind."""
    return [(fam, g, c[kind]) for fam, by_group in cov.items()
            for g, c in by_group.items() if c.get(kind)]


def report_vocabulary(markdown: bool = False) -> None:
    """Piece counts by group, and what share of each group carries a witness.

    Two regressions the error gates cannot name, in one table: a silently emptied or ballooning
    group, and a group whose pieces stopped being backed by measurements. They belong in the same
    table because the second is only actionable per group — an unwitnessed piece counts exactly like
    a witnessed one, so every accuracy number is identical either way and only this says so.

    The gap columns are two, not five. A reader needs to know whether evidence is ABSENT (missing:
    unbought, or unreachable by any template) or CONTRADICTORY (unresolved: the probe and the corpus
    disagree). Which kind, and where, is what the warnings underneath are for — a table cell cannot
    say "run this script" and a warning can.
    """
    cov = witness_coverage()
    groups = sorted({g for fam in cov.values() for g in fam})
    # Every kind the numerator withholds needs a column, or the table shows a rate below 100% with
    # nothing to explain it. `argued` was missing and `fitness` is the only thing in it, so
    # `word_pieces` read 99.96% with all three gap cells empty. `other` is the same guarantee for a
    # kind nobody has classified yet: unknown kinds used to fall through to the witnessed side,
    # which is the direction that flatters.
    cols = ("missing", "unresolved", "argued", "special", "other")
    known = known_kinds()

    def cells(counts: dict[str, int]) -> tuple[int, int, str, dict[str, int]]:
        total, w = sum(counts.values()), witnessed(counts)
        bucket = {"missing": sum(counts.get(k, 0) for k in MISSING),
                  "unresolved": sum(counts.get(k, 0) for k in UNRESOLVED),
                  "argued": sum(counts.get(k, 0) for k in ARGUED),
                  "special": sum(counts.get(k, 0) for k in SPECIAL),
                  "other": sum(n for k, n in counts.items() if k not in known)}
        pct = "100%" if w == total else (f"{100 * w / total:.2f}%" if total else "n/a")
        return total, w, pct, bucket

    refuted = _breaches(cov, "refuted")

    if markdown:
        print("\n## Vocabulary and witness coverage\n")
        print("Every piece must be witnessed or structural-special. Token witnesses carry the "
              "measurements that pin them; specials are reported separately. See PROBES.md.\n")
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
        argued = sum(tot.get(k, 0) for k in ARGUED)
        print(f"  [{fam}] {w:,} of {total:,} pieces on a fixed template or special ({pct})"
              + (f", plus {argued:,} argued from natural text (see LIMITS.md §6)" if argued else ""))
        for g in groups:
            if g not in by_group:
                continue
            total, w, pct, bucket = cells(by_group[g])
            gaps = "  ".join(f"{c}={n:,}" for c, n in bucket.items() if n)
            print(f"    {g:16} {total:>7,}  accounted {w:>7,} ({pct:>6})   {gaps}")
    if refuted:
        print(f"\n  !! {sum(n for *_, n in refuted)} pieces REFUTED by their own probe:")
        for fam, g, n in refuted:
            print(f"       {fam} {g} ({n})   -> scripts/retire_refuted.py --leave-one-out")
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


# The kinds that are NOT a witness, in two groups that mean different things to a reader.
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

# ARGUED is weaker than a witness and is reported apart from one.
#
# A template witness is a FIXED probe: `meta.witness.templates` holds the string, `verify` requires
# the probe to be that template applied to this exact piece, and the arithmetic lands on one token.
# There is nothing per-piece to choose, so a template witness cannot be shaped to fit its piece.
#
# `fitness` is not that. It is a bespoke per-piece argument over natural text — an intersection of
# tiling candidates that restore two or more exact probes — and it is true relative to the rest of
# the vocabulary rather than to the oracle alone. `ownscript` was the same kind of thing and is now
# retired: every piece it certified was re-asked on a fixed template, and 481 of 1,157 were refuted
# by it (LIMITS.md §6). The 22 `fitness` records that remain are counted, named, and kept out of the
# headline number rather than folded in with either a witness or a gap.
ARGUED = ("fitness",)


def known_kinds() -> frozenset[str]:
    """Every kind a witness record may carry, DERIVED from the files rather than listed here.

    `witnessed` subtracts the known non-witness kinds from the total, so a kind it has never heard
    of lands silently on the witnessed side — the one direction a coverage number must never round.
    The guard is only as good as its list, and a hand-written list is exactly the thing that goes
    stale. Writing one by hand missed `digit_bow` — a shipped template carrying 28 v3 punctuation
    pieces — so the template names now come from each vocabulary's own `meta.witness.templates`,
    the same place `verify` reads them. `prefix` is added on top because `verify` dispatches it
    before that lookup: 467 byte-fallback pieces per file rest on it and no template declares it.
    Anything outside the union is reported in the `other` column instead of passing as evidence.
    """
    import json
    from importlib.resources import files

    from ctok.main import FAMILIES

    # `verify` dispatches `prefix` before the template lookup — a byte-prefix piece is pinned by
    # three characters agreeing, not by a probe string, so it is a real witness with no template.
    # It is named here because `witness.verify` names it, which is the only authority on what a
    # witness kind is.
    names: set[str] = set(GAP_KINDS) | set(ARGUED) | {"prefix"}
    for key, owner in vocabulary_owners().items():
        if owner != key:
            continue
        doc = json.loads(
            files("ctok").joinpath("data", FAMILIES[key].pieces).read_text(encoding="utf-8"))
        names |= set(doc["meta"]["witness"]["templates"])
    return frozenset(names)


def witnessed(counts: dict[str, int]) -> int:
    """Pieces resting on a fixed approved template, plus the structural-special marker atoms."""
    return sum(counts.values()) - sum(counts.get(k, 0) for k in MISSING + UNRESOLVED + ARGUED)


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
