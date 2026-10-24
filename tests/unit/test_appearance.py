"""
Внешний вид PNG, который можно переопределить: тема, основной шрифт и поля.
"""

from pathlib import Path

import pytest

pytest.importorskip("PIL")

from picture import picture
from PIL import Image

from termsnap import DARK, LIGHT, Indexed, Line, Rgb, Span, Style
from termsnap.errors import FontNotFound
from termsnap.png import DEFAULT_FAMILIES, Face, FontSet, fonts, from_files, render_image, render_png, resolve_spec
from termsnap.png.fonts import resolution


def face(family: str) -> Face:
    return Face(family, "Regular", Path(f"{family}.ttf"))


def fontset(family: str) -> FontSet:
    result = FontSet.from_faces([face(family)])
    assert result is not None
    return result


def rgb(color: Rgb) -> tuple[int, int, int]:
    return color.red, color.green, color.blue


@pytest.fixture(scope="module")
def system_fonts() -> FontSet:
    try:
        return fonts.resolve(covers="АЯабвёЖ")
    except FontNotFound as error:
        pytest.skip(f"в системе нет подходящего моноширинного шрифта: {error.problems}")


# --- выбор основного шрифта по описанию, без настоящих шрифтов ---


@pytest.fixture
def fake_families(monkeypatch: pytest.MonkeyPatch) -> dict[str, FontSet]:
    installed = {name: fontset(name) for name in ("Poor", "Rich", "Other")}
    monkeypatch.setattr(resolution, "find_family", installed.get)
    monkeypatch.setattr(resolution, "missing_glyphs", lambda face, chars: "Ж" if face.family == "Poor" else "")
    return installed


def test_a_ready_font_set_is_used_as_it_is(fake_families: dict[str, FontSet]):
    assert resolve_spec(fake_families["Other"], covers="Ж") is fake_families["Other"]


def test_a_family_name_and_a_list_of_names_are_resolved_in_order(fake_families: dict[str, FontSet]):
    assert resolve_spec("Rich").family == "Rich"
    assert resolve_spec(["Absent", "Rich", "Other"]).family == "Rich"
    assert resolve_spec(("Other", "Rich")).family == "Other"


def test_a_family_without_the_needed_glyphs_is_skipped_for_the_next_one(fake_families: dict[str, FontSet]):
    assert resolve_spec(["Poor", "Rich"], covers="Ж").family == "Rich"


def test_when_no_family_has_all_glyphs_the_best_installed_one_is_used(fake_families: dict[str, FontSet]):
    # эмодзи и подобное нужно рисовать запасными шрифтами, а не отказываться из-за выбранного основного
    assert resolve_spec("Poor", covers="Ж").family == "Poor"


def test_a_family_that_is_not_installed_is_an_error_not_a_silent_default(fake_families: dict[str, FontSet]):
    with pytest.raises(FontNotFound) as caught:
        resolve_spec(["Absent", "Missing"])
    assert caught.value.problems == ["Absent: не установлен", "Missing: не установлен"]


def test_an_empty_list_is_rejected(fake_families: dict[str, FontSet]):
    with pytest.raises(ValueError, match="пуст"):
        resolve_spec([])


def test_the_defaults_are_used_without_a_spec(monkeypatch: pytest.MonkeyPatch):
    asked: list[str] = []
    monkeypatch.setattr(resolution, "find_family", lambda family: asked.append(family))
    with pytest.raises(FontNotFound):
        resolve_spec(None)
    assert tuple(asked[: len(DEFAULT_FAMILIES)]) == DEFAULT_FAMILIES  # дальше те же семейства пробует resolve_best


def test_user_families_can_be_followed_by_the_defaults(
    fake_families: dict[str, FontSet], monkeypatch: pytest.MonkeyPatch
):
    installed = {**fake_families, DEFAULT_FAMILIES[0]: fontset(DEFAULT_FAMILIES[0])}
    monkeypatch.setattr(resolution, "find_family", installed.get)
    assert resolve_spec(["Absent", *DEFAULT_FAMILIES]).family == DEFAULT_FAMILIES[0]


# --- тема в рисовании ---


def line_with_background(color: Indexed) -> list[Line]:
    return [Line((Span("    ", Style(bg=color)),))]


def test_custom_theme_object_colours_the_picture(bundled_fonts: FontSet):
    custom = DARK.derive(background="#101010", ansi={"red": "#12ab34"})
    image = render_image(line_with_background(Indexed(1)), theme=custom, fonts=bundled_fonts, scale=1, padding=4)
    assert image.getpixel((0, 0)) == (16, 16, 16)  # фон темы в поле
    middle = (image.width // 2, image.height // 2)
    assert image.getpixel(middle) == (0x12, 0xAB, 0x34)  # красный из темы, а не из DARK


def test_theme_can_be_given_by_name_or_as_a_mapping(bundled_fonts: FontSet):
    lines = line_with_background(Indexed(2))
    by_name = render_image(lines, theme="light", fonts=bundled_fonts, scale=1)
    by_object = render_image(lines, theme=LIGHT, fonts=bundled_fonts, scale=1)
    assert by_name.tobytes() == by_object.tobytes()
    by_mapping = render_image(lines, theme={"base": "light", "background": "#fafafa"}, fonts=bundled_fonts, scale=1)
    assert by_mapping.getpixel((0, 0)) == (0xFA, 0xFA, 0xFA)
    assert by_mapping.getpixel((by_mapping.width // 2, by_mapping.height // 2)) == rgb(LIGHT.ansi[2])


def test_unknown_theme_name_is_reported_before_drawing(bundled_fonts: FontSet):
    with pytest.raises(ValueError, match="solarized"):
        render_image([Line((Span("x"),))], theme="solarized", fonts=bundled_fonts)


def test_theme_reaches_png_bytes_too(bundled_fonts: FontSet):
    data = render_png(line_with_background(Indexed(1)), theme={"background": "#010203"}, fonts=bundled_fonts, scale=1)
    import io

    assert Image.open(io.BytesIO(data)).convert("RGB").getpixel((0, 0)) == (1, 2, 3)


# --- шрифт в рисовании ---


def test_font_family_name_gives_the_same_picture_as_the_font_set(system_fonts: FontSet):
    lines = [Line((Span("Привет, hello"),))]
    by_set = render_image(lines, fonts=system_fonts, scale=1)
    by_name = render_image(lines, fonts=system_fonts.family, scale=1)
    by_list = render_image(lines, fonts=["Not A Font At All", system_fonts.family], scale=1)
    assert by_set.tobytes() == by_name.tobytes() == by_list.tobytes()


def test_font_from_files_is_accepted_like_any_other_spec(bundled_fonts: FontSet):
    lines = [Line((Span("hello"),))]
    custom = from_files(bundled_fonts.regular.path)
    assert (
        render_image(lines, fonts=custom, scale=1).tobytes()
        == render_image(lines, fonts=bundled_fonts, scale=1).tobytes()
    )


def test_missing_family_is_an_error_with_the_reason():
    with pytest.raises(FontNotFound, match="Not A Font At All: не установлен"):
        render_image([Line((Span("x"),))], fonts="Not A Font At All")


@pytest.mark.parametrize("symbol", ["✅", "\N{RIGHTWARDS ARROW}", "日"])
def test_overriding_the_main_font_keeps_the_automatic_fallback_for_other_symbols(system_fonts: FontSet, symbol: str):
    # символа нет в основном шрифте: пока запасной шрифт не найден, на его месте рисуется знак "нет глифа" (как у
    # символа с кодом, которого нет ни в одном шрифте); найден - картинка другая
    def cell_of(text: str) -> bytes:
        return render_image([Line((Span(text),))], fonts=system_fonts.family, scale=1, padding=0).tobytes()

    assert cell_of(symbol) != cell_of("􏿿"), f"для {symbol!r} не нашлось запасного шрифта"


# --- поля ---


def test_padding_is_in_screen_pixels_and_multiplied_by_the_scale(bundled_fonts: FontSet):
    lines = [Line((Span("abc"),))]
    bare = render_image(lines, fonts=bundled_fonts, scale=2, padding=0)
    padded = render_image(lines, fonts=bundled_fonts, scale=2, padding=5)
    assert (padded.width - bare.width, padded.height - bare.height) == (20, 20)


def test_the_cell_background_starts_right_after_the_padding_and_without_padding_touches_the_edge(
    bundled_fonts: FontSet,
):
    legend = {".": DARK.background.channels, "R": DARK.ansi[1].channels}
    lines = [Line((Span("   ", Style(bg=Indexed(1))),))]
    flush = render_image(lines, fonts=bundled_fonts, scale=1, padding=0)
    assert picture(flush, legend, box=(0, 0, flush.width, 1)) == "R" * flush.width  # фон доходит до самого угла
    padded = render_image(lines, fonts=bundled_fonts, scale=1, padding=6)
    above, first_row = (picture(padded, legend, box=(0, y, padded.width, y + 1)) for y in (5, 6))
    assert above == "." * padded.width  # строка над полем: только фон картинки
    assert first_row == "." * 6 + "R" * (padded.width - 12) + "." * 6


def test_negative_padding_is_rejected(bundled_fonts: FontSet):
    with pytest.raises(ValueError, match="отрицательн"):
        render_image([Line((Span("x"),))], fonts=bundled_fonts, padding=-1)
