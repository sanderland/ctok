"""Public marker notation stays unambiguous when input contains the notation brackets."""

from ctok.constants import BOW_G, EOW_G, L, R
from ctok.notation import parse_marked, render_marked


def test_render_marked_escapes_literal_brackets_before_translating_markers():
    marked = BOW_G + f"a{L}b{R}" + EOW_G
    public = render_marked(marked)

    assert public == (
        "⟨bow⟩a⟨0xE2⟩⟨0x9F⟩⟨0xA8⟩b⟨0xE2⟩⟨0x9F⟩⟨0xA9⟩⟨eow⟩"
    )
    assert parse_marked(public) == marked
