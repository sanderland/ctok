"""UDHR reproduction gate for the Universal Declaration of Human Rights in 501 natural languages,
scored against recorded ``count_tokens`` values. See ``tests/gates.py`` for the thresholds."""

import pytest

from gates import GATES, assert_gate, score


@pytest.mark.parametrize("family", list(GATES["udhr"]["families"]))
def test_udhr_reproduction_gate(family: str):
    assert_gate("udhr", family, score("udhr", family))
