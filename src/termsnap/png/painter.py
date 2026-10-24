"""
Рисование строк на готовом изображении.
"""

from PIL import Image, ImageDraw, features

from termsnap.model import Line, Span
from termsnap.png import proportions
from termsnap.png.boxes import draw_cell
from termsnap.png.fonts import FontSet
from termsnap.png.layout import Layout
from termsnap.png.pixels import blend, fill_rect
from termsnap.png.text import choose_face, drawn_text, load_font
from termsnap.theme import Theme
from termsnap.width import cluster_width, clusters


class Painter:
    """
    Рисует строки на картинке по раскладке: для каждого фрагмента фон, затем символы клеточными группами, затем
    подчеркивание и зачеркивание. Каждая группа ставится в свою клетку сетки, поэтому ширина глифов на выравнивание
    не влияет.
    """

    def __init__(self, image: Image.Image, layout: Layout, theme: Theme, fonts: FontSet) -> None:
        self._draw = ImageDraw.Draw(image)
        self._layout = layout
        self._theme = theme
        self._fonts = fonts
        self._text_features = proportions.NO_LIGATURES if features.check("raqm") else None

    def paint_line(self, row: int, line: Line) -> None:
        """
        Рисует строку ``row`` (номер строки сверху, с нуля).
        """
        column = 0
        for span in line.spans:
            self._paint_span(row, column, span)
            column += span.width

    def _paint_span(self, row: int, column: int, span: Span) -> None:
        layout = self._layout
        top = layout.row_top(row)
        left = layout.column_x(column)
        right = layout.column_x(column + span.width)
        foreground, background = (color.channels for color in self._theme.colors_of(span.style))
        if span.style.dim:
            foreground = blend(foreground, background, proportions.DIM_SHARE)
        if background != self._theme.background.channels:
            fill_rect(self._draw, left, top, right, top + layout.row_height, background)

        offset = column
        for cluster in clusters(span.text):
            self._paint_cluster(cluster, row, offset, span, foreground, background)
            offset += cluster_width(cluster)

        baseline = layout.baseline(row)
        thickness = layout.thickness
        if span.style.underline:
            y = baseline + proportions.underline_offset(layout.descent)
            fill_rect(self._draw, left, y, right, y + thickness, foreground)
        if span.style.strike:
            y = baseline - proportions.strike_offset(layout.ascent)
            fill_rect(self._draw, left, y, right, y + thickness, foreground)

    def _paint_cluster(
        self,
        cluster: str,
        row: int,
        column: int,
        span: Span,
        foreground: tuple[int, int, int],
        background: tuple[int, int, int],
    ) -> None:
        """
        Одна клеточная группа: пробелы пропускаются, псевдографику рисует библиотека, остальное - шрифт.
        """
        if not cluster.strip():
            return
        layout = self._layout
        top = layout.row_top(row)
        x = layout.column_x(column)
        box = (x, top, x + layout.cell, top + layout.row_height)
        if draw_cell(self._draw, cluster, box, foreground, background, layout.thickness):
            return
        choice = choose_face(self._fonts, layout.size, cluster[0], bold=span.style.bold, italic=span.style.italic)
        font = load_font(choice.face, layout.size)
        # жирности нет в семействе: рисуем дважды со сдвигом на пиксель-другой
        shifts = (0, proportions.bold_shift(layout.size)) if choice.synthetic_bold else (0,)
        for shift in shifts:
            self._draw.text(
                (x + shift, layout.baseline(row)),
                drawn_text(cluster),
                font=font,
                fill=foreground,
                anchor="ls",  # левый край и базовая линия: положение не зависит от высоты конкретного глифа
                features=self._text_features,
                embedded_color=choice.fallback,
            )
