from pathlib import Path

import pytest
from fakes import InstalledFonts
from support import require_module

require_module("PIL")

from PIL import ImageFont

from termsnap.errors import FontNotFound
from termsnap.png import fonts
from termsnap.png.fonts import Face, FontSet, fontconfig, parse_fc_list, registry_name_matches


def face(style: str, family: str = "Fam", name: str | None = None) -> Face:
    return Face(family, style, Path(name or f"{family}-{style.replace(' ', '')}.ttf"))


@pytest.mark.parametrize(
    ("style", "bold", "italic", "rank"),
    [
        ("Regular", False, False, 0),
        ("Roman", False, False, 1),
        ("Book", False, False, 1),
        ("Light", False, False, 9),
        ("ExtraBold", False, False, 9),
        ("Bold", True, False, 0),
        ("Italic", False, True, 0),
        ("Oblique", False, True, 0),
        ("Bold Italic", True, True, 0),
        ("Bold-Oblique", True, True, 0),
        ("ExtraBold Italic", False, True, 9),
        ("Light Italic", False, True, 9),
    ],
)
def test_style_words_define_the_role_and_how_basic_the_face_is(style, bold, italic, rank):
    result = face(style)
    assert (result.bold, result.italic, result.rank) == (bold, italic, rank)


def test_font_set_takes_the_most_basic_face_for_each_role():
    faces = [
        face("Light"),
        face("Regular"),
        face("ExtraBold Italic"),
        face("Italic"),
        face("Bold"),
        face("Bold Italic"),
        face("ExtraBold"),
    ]
    fontset = FontSet.from_faces(faces)
    assert fontset is not None
    assert [f.style if f else None for f in (fontset.regular, fontset.bold, fontset.italic, fontset.bold_italic)] == [
        "Regular",
        "Bold",
        "Italic",
        "Bold Italic",
    ]


def test_font_set_without_a_regular_face_does_not_exist():
    assert FontSet.from_faces([face("Bold"), face("Italic")]) is None
    assert FontSet.from_faces([]) is None


def test_font_set_accepts_roman_as_the_regular_face():
    fontset = FontSet.from_faces([face("Roman")])
    assert fontset is not None
    assert fontset.regular.style == "Roman"


REGULAR, BOLD, ITALIC, BOLD_ITALIC = "Regular", "Bold", "Italic", "Bold Italic"


@pytest.mark.parametrize(
    ("available", "bold", "italic", "chosen", "synthetic"),
    [
        ([REGULAR, BOLD, ITALIC, BOLD_ITALIC], True, True, BOLD_ITALIC, False),
        ([REGULAR, BOLD, ITALIC, BOLD_ITALIC], True, False, BOLD, False),
        ([REGULAR, BOLD, ITALIC, BOLD_ITALIC], False, True, ITALIC, False),
        ([REGULAR, BOLD, ITALIC, BOLD_ITALIC], False, False, REGULAR, False),
        ([REGULAR], True, False, REGULAR, True),  # жирного начертания нет: жирность рисуется наложением
        ([REGULAR], True, True, REGULAR, True),
        ([REGULAR], False, True, REGULAR, False),  # курсива нет: обычное начертание без наложения
        ([REGULAR, BOLD], True, True, BOLD, False),  # жирный курсив без своего начертания: берется жирное
        ([REGULAR, ITALIC], True, True, ITALIC, True),  # ... или курсивное, и жирность наложением
    ],
    ids=[
        "all faces, bold italic",
        "all faces, bold",
        "all faces, italic",
        "all faces, regular",
        "regular only, bold is synthetic",
        "regular only, bold italic is synthetic",
        "regular only, italic is not synthetic",
        "no bold italic: falls back to bold",
        "no bold italic, no bold: falls back to italic with synthetic bold",
    ],
)
def test_pick_chooses_the_closest_real_face_and_says_whether_bold_is_synthetic(
    available: list[str], bold: bool, italic: bool, chosen: str, synthetic: bool
):
    fontset = FontSet.from_faces([face(style) for style in available])
    assert fontset is not None
    picked, is_synthetic = fontset.pick(bold=bold, italic=italic)
    assert (picked.style if picked else None, is_synthetic) == (chosen, synthetic)


@pytest.mark.parametrize(
    ("name", "family", "expected"),
    [
        ("Consolas (TrueType)", "Consolas", True),
        ("Consolas Bold Italic (TrueType)", "consolas", True),
        ("Cascadia Mono Regular (TrueType)", "Cascadia Mono", True),
        ("JetBrainsMonoNL-Regular (TrueType)", "JetBrains Mono NL", True),
        ("JetBrains Mono NL Bold (OpenType)", "JetBrains Mono NL", True),
        ("Cambria & Cambria Math (TrueType)", "Cambria Math", True),
        ("Courier 10,12,15", "Consolas", False),
        ("Consolas (TrueType)", "Consolas Nerd Font", False),
    ],
)
def test_registry_names_are_matched_loosely_and_checked_against_the_file_later(name, family, expected):
    assert registry_name_matches(name, family) is expected


FC_OUTPUT = (
    "/usr/share/fonts/TTF/JetBrainsMono-Light.ttf\t0\tJetBrains Mono,JetBrains Mono Light\tLight,Regular\n"
    "/usr/share/fonts/TTF/JetBrainsMono-Regular.ttf\t0\tJetBrains Mono\tRegular\n"
    "/usr/share/fonts/TTF/JetBrainsMono-Italic.ttf\t0\tJetBrains Mono\tItalic\n"
    "/usr/share/fonts/TTF/JetBrainsMono[wght].ttf\t65536\tJetBrains Mono\tBold\n"
    "/usr/share/fonts/truetype/other/Other.ttf\t0\tJetBrains Mono Other\tRegular\n"
    "/usr/share/fonts/Menlo.ttc\t3\tMenlo\tBold Italic\n"
    "broken line\n"
)


def test_fc_list_output_is_parsed_per_family():
    faces = parse_fc_list(FC_OUTPUT, "jetbrains mono")
    assert [(f.path.name, f.style, f.index) for f in faces] == [
        ("JetBrainsMono-Light.ttf", "Light", 0),
        ("JetBrainsMono-Regular.ttf", "Regular", 0),
        ("JetBrainsMono-Italic.ttf", "Italic", 0),
    ]
    assert {f.family for f in faces} == {"jetbrains mono"}


def test_fc_list_keeps_the_face_number_inside_a_collection():
    (menlo,) = parse_fc_list(FC_OUTPUT, "Menlo")
    assert (menlo.index, menlo.bold, menlo.italic) == (3, True, True)


def test_fc_pattern_escapes_special_characters():
    assert fontconfig.escape_value("Noto Sans Mono-Bold:1,2=3") == r"Noto Sans Mono\-Bold\:1\,2\=3"


def test_unreadable_file_has_no_faces(tmp_path: Path):
    broken = tmp_path / "broken.ttf"
    broken.write_bytes(b"not a font")
    assert fonts.read_faces(broken) == []
    assert fonts.read_faces(tmp_path / "missing.ttf") == []


def test_from_files_reports_an_unreadable_regular_file(tmp_path: Path):
    with pytest.raises(FontNotFound, match="не удалось прочитать"):
        fonts.from_files(tmp_path / "missing.ttf")


def test_resolve_skips_missing_families_and_families_without_the_needed_glyphs():
    fake = InstalledFonts(["Poor", "Rich"], lacking={"Poor": "Ж"})
    options = {"covers": "Ж", "lookup": fake.lookup, "missing_of": fake.missing_of}
    assert fonts.resolve(["Absent", "Poor", "Rich"], **options).family == "Rich"
    with pytest.raises(FontNotFound) as caught:
        fonts.resolve(["Absent", "Poor"], **options)
    assert caught.value.problems == ["Absent: не установлен", "Poor: нет символов 'Ж'"]


# - шрифты, установленные в системе -
def test_the_default_family_is_found_in_the_system_and_loads(system_fonts: FontSet):
    assert system_fonts.family
    font = ImageFont.truetype(
        str(system_fonts.regular.path),
        size=20,
        index=system_fonts.regular.index,
    )
    assert font.getname()[0].casefold() == system_fonts.family.casefold()
    assert not system_fonts.regular.bold
    assert not system_fonts.regular.italic


def test_every_face_of_the_found_family_belongs_to_it(system_fonts: FontSet):
    for found in (
        system_fonts.regular,
        system_fonts.bold,
        system_fonts.italic,
        system_fonts.bold_italic,
    ):
        if found is not None:
            assert found.family.casefold() == system_fonts.family.casefold()
            assert found.path.is_file()


def test_find_family_is_case_insensitive_and_unknown_family_is_none(system_fonts: FontSet):
    assert fonts.find_family(system_fonts.family.upper()) is not None
    assert fonts.find_family("No Such Family termsnap") is None


@pytest.fixture
def system_font(system_fonts: FontSet) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(system_fonts.regular.path), size=24, index=system_fonts.regular.index)


@pytest.mark.parametrize("char", ["A", "Ж"])
def test_the_glyph_check_finds_latin_and_cyrillic_letters(system_font: ImageFont.FreeTypeFont, char: str):
    assert fonts.has_glyph(system_font, char)


def test_the_glyph_check_does_not_find_a_symbol_that_no_font_has(system_font: ImageFont.FreeTypeFont):
    assert not fonts.has_glyph(system_font, chr(0x10FFFF))


def test_missing_glyphs_are_empty_for_text_the_font_covers_and_whitespace(system_fonts: FontSet):
    assert fonts.missing_glyphs(system_fonts.regular, "A Ж\n\t") == ""


def test_missing_glyphs_name_the_symbols_the_font_lacks(system_fonts: FontSet):
    assert fonts.missing_glyphs(system_fonts.regular, "A中") == "中"


def test_font_files_can_be_given_explicitly(system_fonts: FontSet):
    explicit = fonts.from_files(system_fonts.regular.path)
    assert explicit.family.casefold() == system_fonts.family.casefold()
    assert explicit.bold is None


def test_font_directories_are_absolute_paths():
    directories = fonts.font_directories()
    assert directories
    assert all(directory.is_absolute() for directory in directories)
