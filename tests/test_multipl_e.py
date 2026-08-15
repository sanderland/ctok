"""MultiPL-E reproduction gate for the same 25 HumanEval problems in 22 programming languages,
scored against recorded ``count_tokens`` values. The code-domain twin of the UDHR gate:
natural-language validation alone misses punctuation, indentation, operators and string literals.
"""

import pytest

from gates import GATES, assert_gate, score


@pytest.mark.parametrize("family", list(GATES["multipl_e"]["families"]))
def test_multipl_e_reproduction_gate(family: str):
    assert_gate("multipl_e", family, score("multipl_e", family))
