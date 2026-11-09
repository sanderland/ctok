"""Recorded single-user request policy on explicit model IDs."""

import pytest
from gates import corpus

from ctok import token_count, tokenize

# The 18 gate misses, measured November 8–9, 2026. The four later models
# all returned the Opus 5 count plus two for each of these documents.
OPUS_5_REGRESSIONS = {
    "rosetta": {
        "rc3a33d50c2d": 424,
        "rc6ca36be034": 619,
        "rc6d23dedb28": 35,
        "rc6e5eb8546b": 160,
        "rc70d4c1cee1": 601,
        "rc70d6620a8b": 141,
        "rc816378d3ef": 96,
        "rc90289f00d1": 308,
        "rcae3736e5b8": 710,
        "rcafef4807e8": 1159,
        "rcb57cd8c158": 537,
        "rcbfa8e5a1a4": 53,
        "rccbe13bd396": 1081,
        "rccbe8d1c3ee": 396,
        "rce139a3ae00": 141,
        "rcea85d8cf3c": 58,
    },
    "rosetta_holdout": {"rh954933be90": 107, "rhac47bc6bba": 62},
}


@pytest.mark.parametrize(
    "model,frame_offset",
    [
        ("claude-opus-5", 0),
        ("claude-opus-5-5", 2),
        ("claude-sonnet-5-5", 2),
        ("claude-haiku-5-5", 2),
        ("claude-fable-5-1", 2),
    ],
)
def test_trailing_whitespace_gate_regressions(model, frame_offset):
    for name, expected in OPUS_5_REGRESSIONS.items():
        texts = {row["id"]: row["text"] for row in corpus(name)}
        for case, count in expected.items():
            assert token_count(texts[case], model=model) == count + frame_offset, case


@pytest.mark.parametrize(
    "text,expected",
    [
        ("a", 7),
        ("a ", 7),
        ("a\t", 7),
        ("a \v", 7),
        ("a \x1f", 8),
        ("a\xa0", 8),
    ],
)
def test_opus_5_trims_only_raw_ascii_whitespace(text, expected):
    assert token_count(text, model="claude-opus-5") == expected
    assert len(tokenize(text, model="claude-opus-5")) == expected


@pytest.mark.parametrize(
    "model", ["claude-opus-4-8", "claude-sonnet-5", "claude-fable-5"]
)
def test_other_v4_8_models_charge_for_trailing_space_and_tab(model):
    assert token_count("a ", model=model) == token_count("a\t", model=model) == 8
    assert token_count("a ", "4.8") == 8
