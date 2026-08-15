"""Rosetta Code reproduction gates — real, unedited source in hundreds of languages.

Where UDHR and MultiPL-E hold content constant and vary one axis, this corpus varies everything at
once, so it is the gate that exercises the encoder rewrites, the vocabulary and the byte floor
together. Two samples, and the distinction between them is the point:

  * ``rosetta`` — the 1,741 documents every campaign bisects against. Pieces are accepted on
    membership probes rather than on documents, but the documents choose which candidates get
    probed, so this rate is IN SAMPLE. It is the sharpest regression detector there is (v4.7
    reproduces all 1,741), which is what it is kept for.
  * ``rosetta_holdout`` — 250 documents drawn from blocks the first sample never touched. Nothing
    in the vocabulary was probed because of them, so this accuracy number is unbiased.
"""

import pytest

from gates import GATES, assert_gate, score


@pytest.mark.parametrize("family", list(GATES["rosetta"]["families"]))
def test_rosetta_reproduction_gate(family: str):
    assert_gate("rosetta", family, score("rosetta", family))


@pytest.mark.parametrize("family", list(GATES["rosetta_holdout"]["families"]))
def test_rosetta_held_out_reproduction_gate(family: str):
    """The number to quote. A piece fitted to the in-sample documents shows up here as no gain."""
    assert_gate("rosetta_holdout", family, score("rosetta_holdout", family))
