import pytest

pytest.importorskip("PIL")

from PIL import Image, ImageDraw

from termsnap.png.boxes import Arms, arms_of, draw_cell, is_box_char

FG = (240, 10, 10)
BG = (0, 0, 0)
WIDTH, HEIGHT = 11, 21
CX, CY = WIDTH // 2, HEIGHT // 2


def draw(char: str, *, light: int = 1) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    assert draw_cell(ImageDraw.Draw(image), char, (0, 0, WIDTH, HEIGHT), FG, BG, light)
    return image


def lit(image: Image.Image, x: int, y: int) -> bool:
    return image.getpixel((x, y)) == FG


@pytest.mark.parametrize(
    ("char", "expected"),
    [
        ("─", Arms(left=1, right=1)),
        ("│", Arms(up=1, down=1)),
        ("┌", Arms(down=1, right=1)),
        ("┼", Arms(up=1, down=1, left=1, right=1)),
        ("━", Arms(left=2, right=2)),
        ("┏", Arms(down=2, right=2)),
        ("═", Arms(left=3, right=3)),
        ("╔", Arms(down=3, right=3)),
        ("╠", Arms(up=3, down=3, right=3)),
        ("┍", Arms(down=1, right=2)),
        ("╒", Arms(down=1, right=3)),
        ("╴", Arms(left=1)),
        ("╸", Arms(left=2)),
        ("╼", Arms(left=1, right=2)),
        ("╭", Arms(down=1, right=1, arc=True)),
        ("╰", Arms(up=1, right=1, arc=True)),
        ("╌", Arms(left=1, right=1)),
        ("┆", Arms(up=1, down=1)),
    ],
)
def test_box_characters_are_decoded_from_their_unicode_names(char, expected):
    assert arms_of(char) == expected


@pytest.mark.parametrize("char", ["A", "╱", "█", " "])
def test_other_characters_have_no_arms(char):
    assert arms_of(char) is None


def test_which_characters_are_drawn_by_the_library():
    assert is_box_char("│")
    assert is_box_char("█")
    assert is_box_char("⣿")
    assert not is_box_char("A")
    assert not is_box_char("╱")
    assert not is_box_char("ab")


def test_vertical_line_runs_through_the_whole_cell_height_so_rows_join():
    image = draw("│")
    assert all(lit(image, CX, y) for y in range(HEIGHT))
    assert not lit(image, 0, CY)


def test_horizontal_line_runs_through_the_whole_cell_width():
    image = draw("─")
    assert all(lit(image, x, CY) for x in range(WIDTH))
    assert not lit(image, CX, 0)


def test_corner_joins_two_edges_through_the_centre():
    image = draw("┌")
    assert lit(image, CX, CY)
    assert lit(image, WIDTH - 1, CY)
    assert lit(image, CX, HEIGHT - 1)
    assert not lit(image, 0, CY)
    assert not lit(image, CX, 0)


def test_heavy_line_is_thicker_than_light():
    light = sum(lit(draw("│", light=2), x, 3) for x in range(WIDTH))
    heavy = sum(lit(draw("┃", light=2), x, 3) for x in range(WIDTH))
    assert heavy > light


def test_double_line_has_two_strokes_with_a_gap_between():
    image = draw("║", light=1)
    columns = [x for x in range(WIDTH) if lit(image, x, 3)]
    assert len(columns) == 2
    assert columns[1] - columns[0] >= 3
    assert not lit(image, CX, 3)


def test_double_corner_closes_the_outer_edge():
    image = draw("╔", light=1)
    left = min(x for x in range(WIDTH) if lit(image, x, HEIGHT - 1))
    top = min(y for y in range(HEIGHT) if lit(image, WIDTH - 1, y))
    assert lit(image, left, top)  # внешний угол замкнут


def test_rounded_corner_is_not_square():
    square = draw("┌")
    rounded = draw("╭")
    assert lit(square, CX, CY)
    assert not lit(rounded, CX, CY)
    assert lit(rounded, CX, HEIGHT - 1)
    assert any(lit(rounded, WIDTH - 1, y) for y in range(HEIGHT))


@pytest.mark.parametrize("light", [1, 2, 3])
@pytest.mark.parametrize(
    ("char", "vertical_row", "horizontal_column"),
    [("╭", HEIGHT - 1, WIDTH - 1), ("╮", HEIGHT - 1, 0), ("╰", 0, WIDTH - 1), ("╯", 0, 0)],
)
def test_rounded_corner_ends_join_the_straight_lines_of_the_neighbours(char, vertical_row, horizontal_column, light):
    corner = draw(char, light=light)
    vertical = draw("│", light=light)
    horizontal = draw("─", light=light)
    assert [corner.getpixel((x, vertical_row)) for x in range(WIDTH)] == [
        vertical.getpixel((x, vertical_row)) for x in range(WIDTH)
    ]
    assert [corner.getpixel((horizontal_column, y)) for y in range(HEIGHT)] == [
        horizontal.getpixel((horizontal_column, y)) for y in range(HEIGHT)
    ]


def test_rounded_corner_is_antialiased_and_symmetric_to_its_mirror():
    corner = draw("╭")
    assert len({corner.getpixel((x, y)) for x in range(WIDTH) for y in range(HEIGHT)}) > 3
    mirrored = draw("╮").transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    assert corner.tobytes() == mirrored.tobytes()


def test_full_block_and_halves_fill_the_expected_part():
    full = draw("█")
    assert all(lit(full, x, y) for x in range(WIDTH) for y in range(HEIGHT))
    upper = draw("▀")
    assert lit(upper, 0, 0)
    assert not lit(upper, 0, HEIGHT - 1)
    lower = draw("▄")
    assert lit(lower, 0, HEIGHT - 1)
    assert not lit(lower, 0, 0)
    left = draw("▌")
    assert lit(left, 0, CY)
    assert not lit(left, WIDTH - 1, CY)
    right = draw("▐")
    assert lit(right, WIDTH - 1, CY)
    assert not lit(right, 0, CY)


def test_eighth_blocks_grow_from_the_bottom():
    heights = [sum(lit(draw(chr(code)), 0, y) for y in range(HEIGHT)) for code in range(0x2581, 0x2589)]
    assert heights == sorted(heights)
    assert heights[-1] == HEIGHT


def test_quadrants():
    upper_left = draw("▘")
    assert lit(upper_left, 0, 0)
    assert not lit(upper_left, WIDTH - 1, 0)
    assert not lit(upper_left, 0, HEIGHT - 1)
    lower_right = draw("▗")
    assert lit(lower_right, WIDTH - 1, HEIGHT - 1)
    assert not lit(lower_right, 0, 0)
    assert all(lit(draw("▛"), x, 0) for x in range(WIDTH))


def test_shades_blend_the_foreground_with_the_background():
    for char, share in (("░", 0.25), ("▒", 0.5), ("▓", 0.75)):
        pixel = draw(char).getpixel((0, 0))
        assert pixel == tuple(round(c * share) for c in FG)


def test_braille_draws_the_requested_dots_only():
    assert draw("⠀").getcolors() == [(WIDTH * HEIGHT, BG)]
    one = draw("⠁")
    assert any(lit(one, x, y) for x in range(WIDTH // 2) for y in range(HEIGHT // 4))
    assert not any(lit(one, x, y) for x in range(WIDTH // 2 + 1, WIDTH) for y in range(HEIGHT))
    full = draw("⣿")
    assert sum(lit(full, x, y) for x in range(WIDTH) for y in range(HEIGHT)) > sum(
        lit(one, x, y) for x in range(WIDTH) for y in range(HEIGHT)
    )


def test_other_characters_are_left_to_the_font():
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    assert not draw_cell(ImageDraw.Draw(image), "A", (0, 0, WIDTH, HEIGHT), FG, BG, 1)
    assert not draw_cell(ImageDraw.Draw(image), "╱", (0, 0, WIDTH, HEIGHT), FG, BG, 1)
    assert not draw_cell(ImageDraw.Draw(image), "ab", (0, 0, WIDTH, HEIGHT), FG, BG, 1)
    assert image.getcolors() == [(WIDTH * HEIGHT, BG)]
