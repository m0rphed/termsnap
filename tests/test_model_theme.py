import pytest

from termsnap import (
    ANSI_NAMES,
    DARK,
    LIGHT,
    THEMES,
    Indexed,
    Line,
    Rgb,
    Span,
    Style,
    Theme,
    get_theme,
    parse_color,
    register_theme,
)


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
    assert line.width == 4


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


# --- свои темы: цвета в любой записи, derive, словарь, имена ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("#ff2e97", Rgb(255, 46, 151)),
        ("FF2E97", Rgb(255, 46, 151)),
        ("  #f00 ", Rgb(255, 0, 0)),
        ("abc", Rgb(0xAA, 0xBB, 0xCC)),
        ((1, 2, 3), Rgb(1, 2, 3)),
        (Rgb(9, 8, 7), Rgb(9, 8, 7)),
    ],
)
def test_colors_can_be_written_in_several_ways(value, expected):
    assert parse_color(value) == expected


@pytest.mark.parametrize("bad", ["", "#12", "#12345", "#gggggg", "red"])
def test_bad_color_strings_are_rejected(bad: str):
    with pytest.raises(ValueError, match="#rrggbb"):
        parse_color(bad)


def test_color_of_a_wrong_kind_or_out_of_range_is_rejected():
    with pytest.raises(TypeError):
        parse_color(15)  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValueError, match="от 0 до 255"):
        parse_color((0, 0, 300))


def test_derive_changes_only_what_is_given_and_keeps_the_original():
    custom = DARK.derive(background="#101010", ansi={"red": "#ff5555", 4: (0, 0, 255), "Bright-Green": "0f0"})
    assert custom.background == Rgb(16, 16, 16)
    assert custom.foreground == DARK.foreground
    assert custom.ansi[1] == Rgb(0xFF, 0x55, 0x55)
    assert custom.ansi[4] == Rgb(0, 0, 255)
    assert custom.ansi[10] == Rgb(0, 255, 0)
    assert [c for i, c in enumerate(custom.ansi) if i not in (1, 4, 10)] == [
        c for i, c in enumerate(DARK.ansi) if i not in (1, 4, 10)
    ]
    assert DARK.background == Rgb(0x1E, 0x1E, 0x1E)  # исходная тема не тронута
    assert custom.name == "dark"
    assert DARK.derive(name="mine").name == "mine"


def test_derive_can_replace_all_sixteen_colors_at_once():
    colors = [f"#{index:02x}{index:02x}{index:02x}" for index in range(16)]
    assert DARK.derive(ansi=colors).ansi == tuple(Rgb(index, index, index) for index in range(16))
    with pytest.raises(ValueError, match="16 базовых"):
        DARK.derive(ansi=colors[:15])


@pytest.mark.parametrize("key", [16, -1, "orange", "bright_orange"])
def test_derive_rejects_unknown_basic_colors(key):
    with pytest.raises(ValueError, match="базов"):
        DARK.derive(ansi={key: "#fff"})


def test_names_cover_all_sixteen_basic_colors_in_order():
    assert len(ANSI_NAMES) == 16
    assert ANSI_NAMES[0] == "black"
    assert ANSI_NAMES[1] == "red"
    assert ANSI_NAMES[8] == "bright_black"
    assert ANSI_NAMES[15] == "bright_white"


def test_derived_theme_is_used_when_colours_are_resolved():
    custom = DARK.derive(foreground="#eeeeee", ansi={"red": "#ff0000"})
    assert custom.resolve(Indexed(1)) == Rgb(255, 0, 0)
    assert custom.colors_of(Style(fg=Indexed(1))) == (Rgb(255, 0, 0), DARK.background)
    assert custom.colors_of(Style()) == (Rgb(0xEE, 0xEE, 0xEE), DARK.background)
    assert custom.resolve(Indexed(196)) == DARK.resolve(Indexed(196))  # куб и серые ступени общие


def test_theme_from_a_mapping_starts_from_a_base_theme():
    custom = Theme.from_mapping(
        {"base": "light", "background": "#fafafa", "ansi": {"blue": "#0000ff"}, "name": "paper"}
    )
    assert custom.foreground == LIGHT.foreground
    assert custom.background == Rgb(0xFA, 0xFA, 0xFA)
    assert custom.ansi[4] == Rgb(0, 0, 255)
    assert custom.name == "paper"
    assert Theme.from_mapping({}) == DARK  # без base берется dark


def test_theme_mapping_with_a_misspelled_key_is_an_error():
    with pytest.raises(ValueError, match="foregrund"):
        Theme.from_mapping({"foregrund": "#fff"})


def test_get_theme_accepts_every_way_to_name_a_theme():
    assert get_theme() is DARK
    assert get_theme(None) is DARK
    assert get_theme(LIGHT) is LIGHT
    assert get_theme("light") is LIGHT
    assert get_theme("  Dark ") is DARK
    assert get_theme({"base": "light", "foreground": "#000"}).foreground == Rgb(0, 0, 0)


def test_get_theme_reports_unknown_names_and_wrong_types():
    with pytest.raises(ValueError, match="dark, light"):
        get_theme("solarized")
    with pytest.raises(TypeError, match="словарь"):
        get_theme(42)  # pyright: ignore[reportArgumentType]


def test_registered_theme_is_found_by_name(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("termsnap.theme.THEMES", dict(THEMES))  # чтобы не оставлять тему на другие тесты
    mine = DARK.derive(background="#000000", name="mine")
    register_theme("  Mine ", mine)
    assert get_theme("mine") is mine
    assert get_theme({"base": "MINE"}).background == Rgb(0, 0, 0)
    assert "mine" not in THEMES  # исходный словарь не тронут
