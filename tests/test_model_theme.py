import pytest

from termsnap import DARK, LIGHT, Indexed, Line, Rgb, Span, Style, Theme


def test_indexed_and_rgb_validate_their_ranges():
    with pytest.raises(ValueError, match="от 0 до 255"):
        Indexed(256)
    with pytest.raises(ValueError, match="от 0 до 255"):
        Indexed(-1)
    with pytest.raises(ValueError, match="от 0 до 255"):
        Rgb(0, 256, 0)


def test_rgb_hex():
    assert Rgb(255, 46, 151).hex == "#ff2e97"
    assert Rgb(0, 0, 0).hex == "#000000"


def test_line_text_and_length():
    line = Line((Span("ab"), Span("cd", Style(bold=True))))
    assert line.text == "abcd"
    assert len(line) == 4


def test_values_are_hashable_and_comparable():
    assert Style(fg=Indexed(1)) == Style(fg=Indexed(1))
    assert len({Style(fg=Indexed(1)), Style(fg=Indexed(1)), Style()}) == 2


@pytest.mark.parametrize("theme", [DARK, LIGHT])
def test_basic_colors_come_from_the_theme(theme: Theme):
    assert theme.resolve(Indexed(1)) == theme.ansi[1]
    assert theme.resolve(Indexed(15)) == theme.ansi[15]


def test_color_cube_and_grayscale_follow_xterm():
    assert DARK.resolve(Indexed(16)) == Rgb(0, 0, 0)
    assert DARK.resolve(Indexed(21)) == Rgb(0, 0, 255)
    assert DARK.resolve(Indexed(196)) == Rgb(255, 0, 0)
    assert DARK.resolve(Indexed(202)) == Rgb(255, 95, 0)
    assert DARK.resolve(Indexed(231)) == Rgb(255, 255, 255)
    assert DARK.resolve(Indexed(232)) == Rgb(8, 8, 8)
    assert DARK.resolve(Indexed(255)) == Rgb(238, 238, 238)


def test_rgb_resolves_to_itself():
    assert LIGHT.resolve(Rgb(1, 2, 3)) == Rgb(1, 2, 3)


def test_colors_of_uses_defaults_and_inverse():
    assert DARK.colors_of(Style()) == (DARK.foreground, DARK.background)
    assert DARK.colors_of(Style(fg=Indexed(1))) == (DARK.ansi[1], DARK.background)
    assert DARK.colors_of(Style(fg=Indexed(1), inverse=True)) == (DARK.background, DARK.ansi[1])


def test_theme_needs_exactly_sixteen_basic_colors():
    with pytest.raises(ValueError, match="16"):
        Theme(foreground=Rgb(0, 0, 0), background=Rgb(255, 255, 255), ansi=(Rgb(0, 0, 0),) * 8)
