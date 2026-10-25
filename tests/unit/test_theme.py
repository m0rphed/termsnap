"""
Тема: откуда берутся цвета клеток, как из готовой темы делается своя и как темы находятся по имени.
"""

from collections.abc import Iterator

import pytest

from termsnap import DARK, LIGHT, THEMES, Indexed, Rgb, Style, Theme, get_theme, register_theme
from termsnap.theme.palette import extended_color


@pytest.fixture
def isolated_themes() -> Iterator[None]:
    """
    Реестр тем возвращается в исходное состояние после теста: зарегистрированная тема не должна жить дальше него.
    """
    saved = dict(THEMES)
    yield
    THEMES.clear()
    THEMES.update(saved)


# --- откуда берется цвет клетки ---


@pytest.mark.parametrize("theme", [DARK, LIGHT], ids=["dark", "light"])
@pytest.mark.parametrize("number", [1, 15])
def test_basic_colors_come_from_the_theme(theme: Theme, number: int):
    assert theme.resolve(Indexed(number)) == theme.ansi[number]


@pytest.mark.parametrize("theme", [DARK, LIGHT], ids=["dark", "light"])
@pytest.mark.parametrize("number", [16, 21, 196, 231, 232, 255])
def test_cube_and_grayscale_colors_follow_xterm_in_any_theme(theme: Theme, number: int):
    assert theme.resolve(Indexed(number)) == extended_color(number)


def test_truecolor_resolves_to_itself():
    assert LIGHT.resolve(Rgb(1, 2, 3)) == Rgb(1, 2, 3)


def test_default_cell_colors_are_the_foreground_and_background_of_the_theme():
    assert DARK.colors_of(Style()) == (DARK.foreground, DARK.background)


def test_cell_colors_come_from_the_style():
    assert DARK.colors_of(Style(fg=Indexed(1))) == (DARK.ansi[1], DARK.background)


def test_inverse_swaps_the_colors_of_the_cell():
    assert DARK.colors_of(Style(fg=Indexed(1), inverse=True)) == (DARK.background, DARK.ansi[1])


def test_theme_needs_exactly_sixteen_basic_colors():
    with pytest.raises(ValueError, match="16"):
        Theme(foreground=Rgb(0, 0, 0), background=Rgb(255, 255, 255), ansi=(Rgb(0, 0, 0),) * 8)


# --- своя тема: derive и словарь ---


def test_derive_changes_only_what_is_given():
    custom = DARK.derive(background="#101010", ansi={"red": "#ff5555", 4: (0, 0, 255), "Bright-Green": "0f0"})
    assert custom.background == Rgb(16, 16, 16)
    assert custom.foreground == DARK.foreground
    assert (custom.ansi[1], custom.ansi[4], custom.ansi[10]) == (Rgb(0xFF, 0x55, 0x55), Rgb(0, 0, 255), Rgb(0, 255, 0))


def test_derive_keeps_the_other_basic_colors_and_the_original_theme():
    custom = DARK.derive(ansi={"red": "#ff5555", 4: (0, 0, 255), "Bright-Green": "0f0"})
    assert [c for i, c in enumerate(custom.ansi) if i not in (1, 4, 10)] == [
        c for i, c in enumerate(DARK.ansi) if i not in (1, 4, 10)
    ]
    assert DARK.ansi[1] != custom.ansi[1]
    assert DARK.background == Rgb(0x1E, 0x1E, 0x1E)


def test_derive_keeps_the_name_unless_a_new_one_is_given():
    assert (DARK.derive(background="#000").name, DARK.derive(name="mine").name) == ("dark", "mine")


def test_derive_can_replace_all_sixteen_colors_at_once():
    colors = [f"#{index:02x}{index:02x}{index:02x}" for index in range(16)]
    assert DARK.derive(ansi=colors).ansi == tuple(Rgb(index, index, index) for index in range(16))


def test_derive_rejects_a_list_of_the_wrong_length():
    with pytest.raises(ValueError, match="16 базовых"):
        DARK.derive(ansi=["#000000"] * 15)


@pytest.mark.parametrize("key", [16, -1, "orange", "bright_orange"])
def test_derive_rejects_unknown_basic_colors(key):
    with pytest.raises(ValueError, match="базов"):
        DARK.derive(ansi={key: "#fff"})


def test_derived_theme_is_used_when_colours_are_resolved():
    custom = DARK.derive(foreground="#eeeeee", ansi={"red": "#ff0000"})
    assert custom.resolve(Indexed(1)) == Rgb(255, 0, 0)
    assert custom.colors_of(Style(fg=Indexed(1))) == (Rgb(255, 0, 0), DARK.background)
    assert custom.colors_of(Style()) == (Rgb(0xEE, 0xEE, 0xEE), DARK.background)


def test_theme_from_a_mapping_starts_from_a_base_theme():
    custom = Theme.from_mapping(
        {"base": "light", "background": "#fafafa", "ansi": {"blue": "#0000ff"}, "name": "paper"}
    )
    assert custom.foreground == LIGHT.foreground
    assert custom.background == Rgb(0xFA, 0xFA, 0xFA)
    assert custom.ansi[4] == Rgb(0, 0, 255)
    assert custom.name == "paper"


def test_theme_from_a_mapping_without_a_base_starts_from_dark():
    assert Theme.from_mapping({}) == DARK


def test_theme_mapping_with_a_misspelled_key_is_an_error():
    with pytest.raises(ValueError, match="foregrund"):
        Theme.from_mapping({"foregrund": "#fff"})


# --- темы по имени ---


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (None, DARK),
        (LIGHT, LIGHT),
        ("light", LIGHT),
        ("  Dark ", DARK),
    ],
    ids=["nothing", "theme object", "name", "name with spaces and capital"],
)
def test_get_theme_accepts_every_way_to_name_a_theme(spec, expected: Theme):
    assert get_theme(spec) is expected


def test_get_theme_without_arguments_is_dark():
    assert get_theme() is DARK


def test_get_theme_accepts_a_mapping():
    assert get_theme({"base": "light", "foreground": "#000"}).foreground == Rgb(0, 0, 0)


def test_get_theme_reports_unknown_names_with_the_known_ones():
    with pytest.raises(ValueError, match="dark, light"):
        get_theme("solarized")


def test_get_theme_reports_a_wrong_type():
    with pytest.raises(TypeError, match="словарь"):
        get_theme(42)  # pyright: ignore[reportArgumentType]


def test_registered_theme_is_found_by_name_in_any_spelling(isolated_themes: None):
    mine = DARK.derive(background="#000000", name="mine")
    register_theme("  Mine ", mine)
    assert get_theme("mine") is mine
    assert get_theme({"base": "MINE"}).background == Rgb(0, 0, 0)
