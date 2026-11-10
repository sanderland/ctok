"""Count regressions fixed by vocabulary additions in PR37."""

import pytest

from ctok import token_count


@pytest.mark.parametrize("text,expected", [(".hegységヲ.", 14), ("hegység", 9)])
def test_v3_interior_yseg(text, expected):
    # The bare word was already exact; its prefix context needs the interior ység piece.
    assert token_count(text, "3.0") == expected
