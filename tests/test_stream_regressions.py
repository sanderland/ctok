"""Published regressions from crelliscmu/ctok commit 90c5f54.

https://github.com/crelliscmu/ctok/commit/90c5f54fb8b462dab2bab416a824a28a54523621
"""

import pytest

from ctok import marked_stream, token_count, tokenize
from ctok.constants import ASSISTANT_G, HUMAN_G
from ctok.notation import parse_marked, render_marked


MIXED_DIGIT_ROWS = [
    ("3.0", "a  ⅔︀ .", 10), ("3.0", "a ⅔︀ .", 9), ("3.0", "a  ①໒ .", 8), ("3.0", "a १︀ .", 6),
    ("4.7", "a  ⅔︀ .", 10), ("4.7", "a ⅔︀ .", 9), ("4.7", "a  ①໒ .", 8), ("4.7", "a  ²️ .", 7),
    ("4.8", " ⅔︀ .", 9), ("4.8", "⅔︀ .", 7), ("4.8", " ①໒ .", 7), ("4.8", "a  ⅔︀ .", 10),
    # ...and ⟨eow⟩ when it closes on one, which shows before a run that writes no ⟨bow⟩ (an ideograph).
    ("3.0", "௰໒ 中 .", 10), ("3.0", "⅔６ 鋼 .", 12),
    ("4.7", "௰໒ 中 .", 10), ("4.7", "⅔６ 鋼 .", 12), ("4.8", "௰໒ 中 .", 9),
]

TONE_MARK_ROWS = [
    ("3.0", "〬 䦜 .", 9), ("3.0", "a  〬 .", 6),
    ("4.7", "〬 䦜 .", 9), ("4.7", "a  〬 .", 6),
    ("4.8", "〬 䦜 .", 8), ("4.8", " 〮 .", 5), ("4.8", "a  〬 .", 6),
]

SHARP_S_ROWS = [
    ("3.0", "Aẞ", 5), ("3.0", "Ỳẞ", 7), ("3.0", "ẞa", 4), ("3.0", "AẞA", 4),
    ("4.7", "Aẞ", 5), ("4.7", "Ỳẞ", 7), ("4.7", "ẞa", 4), ("4.7", "AẞA", 4),
    ("4.8", "Aẞ", 5), ("4.8", "Yẞa", 5),
]

NS = "ant" + "ml:"

NAMESPACE_ROWS = [
    ("3.0", f"<{NS}invoke>", 3), ("4.7", f"<{NS}invoke>", 5), ("4.8", f"<{NS}invoke>", 5),
    ("3.0", f"</{NS}invoke>", 3), ("4.7", f"</{NS}invoke>", 5), ("4.8", f"</{NS}invoke>", 5),
    ("3.0", f"x <{NS} y", 3), ("4.7", f"x <{NS} y", 3), ("4.8", f"x <{NS} y", 3),
    ("3.0", f"x </{NS} y", 4), ("4.7", f"x </{NS} y", 4), ("4.8", f"x </{NS} y", 4),
    ("3.0", f"x <{NS}/", 2), ("4.7", f"x <{NS}/", 2), ("4.8", f"x <{NS}/", 2),
    ("3.0", f"x <//{NS}y", 3), ("4.7", f"x <//{NS}y", 3), ("4.8", f"x <//{NS}y", 3),
    ("4.7", f"x <{NS.upper()}y", 3), ("4.8", f"x <{NS.upper()}y", 3),
    # Not the namespace: `>` or the end follows, or a third slash.
    ("3.0", f"x <{NS}>", 6), ("4.7", f"x <{NS}>", 6), ("4.8", f"x <{NS}>", 6),
    ("4.7", f"x <{NS}", 5), ("4.8", f"x <{NS}", 5),
    ("3.0", f"x <///{NS}y", 7), ("4.7", f"x <///{NS}y", 7), ("4.8", f"x <///{NS}y", 7),
]

TURN_MARKER_ROWS = [
    ("3.0", "x\n\nHuman: y", 5), ("4.7", "x\n\nHuman: y", 5), ("4.8", "x\n\nHuman: y", 6),
    ("3.0", "x\n\nASSISTANT: y", 5), ("4.7", "x\n\nASSISTANT: y", 5),
    ("4.8", "x\n\nASSISTANT: y", 11),
    ("3.0", "x\n\n\nassistant:y", 5), ("4.7", "x\n\n\nassistant:y", 5),
    ("4.7", "x\n\nHuman:: y", 6), ("4.7", "x\nHuman: y", 6), ("4.7", "x\n\nUser: y", 5),
]

UNICODE_16_ROWS = [
    ("3.0", "x \ua7cc .", 8), ("4.7", "x \ua7cc .", 8), ("4.8", "x \ua7cc .", 8),
    ("3.0", "1\ua7cc2", 9), ("4.7", "1\ua7cc2", 9), ("4.8", "1\ua7cc2", 8),
    ("4.7", "ab\ua7da", 5), ("4.7", "\ua7dc\ua7db", 8),
    ("3.0", "x \ua7cd's", 7), ("4.7", "x \ua7cd's", 7), ("4.8", "x \u1c8a's", 7),
]


@pytest.mark.parametrize(
    "version,text,content",
    MIXED_DIGIT_ROWS + TONE_MARK_ROWS + SHARP_S_ROWS + NAMESPACE_ROWS
    + TURN_MARKER_ROWS + UNICODE_16_ROWS,
)
def test_published_stream_counts(version, text, content):
    frame = {"3.0": 7, "4.7": 11, "4.8": 6}[version]
    assert token_count(text, version) == frame + content


@pytest.mark.parametrize("glyph,atom", [(HUMAN_G, "⟨human⟩"), (ASSISTANT_G, "⟨assistant⟩")])
def test_turn_marker_notation_round_trips(glyph, atom):
    assert render_marked(glyph) == atom
    assert parse_marked(atom) == glyph


@pytest.mark.parametrize("version", ["3.0", "4.7", "4.8"])
@pytest.mark.parametrize("glyph", [HUMAN_G, ASSISTANT_G])
def test_literal_turn_marker_codepoints_are_escaped(version, glyph):
    assert "⟨human⟩" not in marked_stream(glyph, version)
    assert "⟨assistant⟩" not in marked_stream(glyph, version)
    assert tokenize(glyph, version)


@pytest.mark.parametrize("version", ["3.0", "4.7", "4.8"])
@pytest.mark.parametrize(
    "text,rewritten",
    [("<antml:antml:x", "<x"), ("<antml:/antml:/", "</"),
     ("</antml:/antml:/", "<//"), ("<antml:antml:>", "<antml:>"),
     ("<antml:antml:", "<antml:"), ("<antml:\x1f", "<"),
     ("<antml:\ue000", "<")],
)
def test_namespace_rewrite_precedes_unicode_normalization(version, text, rewritten):
    assert marked_stream(text, version) == marked_stream(rewritten, version)
    assert token_count(text, version) == token_count(rewritten, version)


@pytest.mark.parametrize("version", ["3.0", "4.7", "4.8"])
def test_normalization_does_not_create_a_reserved_namespace(version):
    assert "antml" in marked_stream("<ant\x1fml:x", version)
    assert "antml" not in marked_stream("<antml:x", version)


@pytest.mark.parametrize("version", ["3.0", "4.7"])
@pytest.mark.parametrize(
    "text", ["x\n\nHu\x1fman: y", "x\n\nHuman\x1f: y", "x\n\r\nHuman: y"]
)
def test_normalization_does_not_create_a_reserved_turn_marker(version, text):
    assert "⟨human⟩" not in marked_stream(text, version)
    assert "⟨human⟩" in marked_stream("x\n\nHuman: y", version)
