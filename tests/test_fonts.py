from pathlib import Path

import pytest

pytest.importorskip("PIL")

from PIL import ImageFont

from termsnap.errors import FontNotFound
from termsnap.png import fonts
from termsnap.png.fonts import Face, FontSet, fontconfig, parse_fc_list, registry_name_matches, resolution


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


def test_pick_uses_real_faces_and_marks_missing_bold_as_synthetic():
    full = FontSet.from_faces([face("Regular"), face("Bold"), face("Italic"), face("Bold Italic")])
    assert full is not None
    assert full.pick(bold=True, italic=True) == (full.bold_italic, False)
    assert full.pick(bold=True, italic=False) == (full.bold, False)
    assert full.pick(bold=False, italic=True) == (full.italic, False)
    assert full.pick(bold=False, italic=False) == (full.regular, False)

    only_regular = FontSet.from_faces([face("Regular")])
    assert only_regular is not None
    assert only_regular.pick(bold=True, italic=False) == (only_regular.regular, True)
    assert only_regular.pick(bold=True, italic=True) == (only_regular.regular, True)
    assert only_regular.pick(bold=False, italic=True) == (only_regular.regular, False)


def test_pick_bold_italic_falls_back_to_bold_then_italic():
    bold_only = FontSet.from_faces([face("Regular"), face("Bold")])
    assert bold_only is not None
    assert bold_only.pick(bold=True, italic=True) == (bold_only.bold, False)
    italic_only = FontSet.from_faces([face("Regular"), face("Italic")])
    assert italic_only is not None
    assert italic_only.pick(bold=True, italic=True) == (italic_only.italic, True)


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


def test_resolve_skips_missing_families_and_families_without_the_needed_glyphs(monkeypatch: pytest.MonkeyPatch):
    sets = {
        "Poor": FontSet.from_faces([face("Regular", "Poor")]),
        "Rich": FontSet.from_faces([face("Regular", "Rich")]),
    }
    monkeypatch.setattr(resolution, "find_family", sets.get)
    monkeypatch.setattr(resolution, "missing_glyphs", lambda face, chars: "Ж" if face.family == "Poor" else "")
    assert fonts.resolve(["Absent", "Poor", "Rich"], covers="Ж").family == "Rich"
    with pytest.raises(FontNotFound) as caught:
        fonts.resolve(["Absent", "Poor"], covers="Ж")
    assert caught.value.problems == ["Absent: не установлен", "Poor: нет символов 'Ж'"]


# - шрифты, установленные в системе -
@pytest.fixture(scope="module")
def system_fonts() -> FontSet:
    try:
        return fonts.resolve(covers="АЯабвёЖ")
    except FontNotFound as error:
        pytest.skip(f"в системе нет подходящего моноширинного шрифта: {error.problems}")


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


def test_glyph_check_tells_cyrillic_from_missing_symbols(system_fonts: FontSet):
    font = ImageFont.truetype(
        str(system_fonts.regular.path),
        size=24,
        index=system_fonts.regular.index,
    )
    assert fonts.has_glyph(font, "A")
    assert fonts.has_glyph(font, "Ж")
    assert not fonts.has_glyph(font, "\U0010ffff")
    assert fonts.missing_glyphs(system_fonts.regular, "A Ж\n\t") == ""
    assert fonts.missing_glyphs(system_fonts.regular, "A中") == "中"


def test_font_files_can_be_given_explicitly(system_fonts: FontSet):
    explicit = fonts.from_files(system_fonts.regular.path)
    assert explicit.family.casefold() == system_fonts.family.casefold()
    assert explicit.bold is None


def test_font_directories_are_absolute_paths():
    directories = fonts.font_directories()
    assert directories
    assert all(directory.is_absolute() for directory in directories)
