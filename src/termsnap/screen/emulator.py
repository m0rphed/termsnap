"""
Экран терминала на ``pyte`` с поправками, которые нужны, чтобы не терять оформление и текст.
"""

import pyte
from pyte import modes

from termsnap.ansi import codes
from termsnap.model import PALETTE_SIZE
from termsnap.width import cluster_width, clusters

#: Приставка, которой помечается индекс палитры в поле цвета ячейки: ``"#208"``. Обычно в этом поле лежит имя цвета
#: (``"red"``) или шесть цифр RGB (``"ff8800"``), так что ``#`` ни с чем не спутать.
PALETTE_MARK = "#"


#: Коды, которые задают цвет из 16 базовых или сбрасывают его: 30-37, 90-97 и 39 для текста, 40-47, 100-107 и 49 для
#: фона. pyte запишет такой цвет сам, поэтому метка палитры от прошлого цвета должна исчезнуть.
_PLAIN_FOREGROUND = (*codes.FG_BASIC, *codes.FG_BRIGHT, codes.FG_DEFAULT)
_PLAIN_BACKGROUND = (*codes.BG_BASIC, *codes.BG_BRIGHT, codes.BG_DEFAULT)


class TerminalScreen(pyte.HistoryScreen):
    """
    Экран pyte с историей прокрутки и двумя поправками.

    Оформление. Атрибут "тусклый" хранится в поле ``blink`` ячейки (настоящее мигание на показ в документе не
    влияет, а у ``Char`` для тусклого поля нет). Цвет из палитры хранится индексом (``PALETTE_MARK``), а не готовым
    RGB, иначе тему уже не применить.

    Текст. ``pyte`` на первом же символе нулевой ширины (селектор эмодзи, соединитель ZWJ) бросает остаток строки,
    а здесь текст делится на те же клеточные группы, что и в ``termsnap.width``.
    """

    def __init__(self, columns: int, lines: int, history: int) -> None:
        super().__init__(columns, lines, history=history)
        #: Ответы на запросы программы (позиция курсора и т.п.), которые терминал должен вернуть ей на вход.
        self.replies: list[str] = []

    def write_process_input(self, data: str) -> None:
        self.replies.append(data)

    def draw(self, data: str) -> None:
        """
        Печатает текст в позиции курсора, как ``pyte.Screen.draw``, но по клеточным группам.
        """
        data = data.translate(self.g1_charset if self.charset else self.g0_charset)
        for cluster in clusters(data):
            width = cluster_width(cluster)
            if width == 0:
                continue
            if self.cursor.x == self.columns:  # конец строки: перенос или замена последнего символа
                if modes.DECAWM in self.mode:
                    self.dirty.add(self.cursor.y)
                    self.carriage_return()
                    self.linefeed()
                else:
                    self.cursor.x -= width
            if modes.IRM in self.mode:
                self.insert_characters(width)
            line = self.buffer[self.cursor.y]
            line[self.cursor.x] = self.cursor.attrs._replace(data=cluster)
            if width == 2 and self.cursor.x + 1 < self.columns:  # у широкого символа вторая клетка пуста
                line[self.cursor.x + 1] = self.cursor.attrs._replace(data="")
            self.cursor.x = min(self.cursor.x + width, self.columns)
        self.dirty.add(self.cursor.y)

    def select_graphic_rendition(self, *attrs: int) -> None:
        """
        Обрабатывает SGR: все, что умеет ``pyte``, делает он сам, а мы поверх запоминаем тусклость и индексы палитры.

            dim = текущая тусклость;  marks = {}   # поле -> "#индекс" для цветов, заданных в этом вызове
            для каждого кода:
                0, 22          -> dim = False (код 0 еще и забывает marks)
                2              -> dim = True
                обычный цвет   -> убрать метку этого поля (цвет задан базовым, pyte запишет его сам)
                38/48;5;n      -> marks[поле] = "#n"
                38/48;2;r;g;b  -> убрать метку (24-битный цвет pyte запишет сам)
            pyte обрабатывает те же коды;  затем в ячейку пишем dim и marks поверх
        """
        dim = self.cursor.attrs.blink
        marks: dict[str, str] = {}
        sequence = attrs or (codes.RESET,)
        position = 0
        while position < len(sequence):
            code = sequence[position]
            position += 1
            if code == codes.RESET:
                dim = False
                marks.clear()
            elif code == codes.DIM:
                dim = True
            elif code == codes.NORMAL_INTENSITY:
                dim = False
            elif code in _PLAIN_FOREGROUND:
                marks.pop("fg", None)
            elif code in _PLAIN_BACKGROUND:
                marks.pop("bg", None)
            elif code in (codes.FG_EXTENDED, codes.BG_EXTENDED):
                field = "fg" if code == codes.FG_EXTENDED else "bg"
                kind = sequence[position] if position < len(sequence) else None
                if kind == codes.COLOR_PALETTE and position + 1 < len(sequence):
                    if sequence[position + 1] < PALETTE_SIZE:
                        marks[field] = f"{PALETTE_MARK}{sequence[position + 1]}"
                    position += codes.EXTENDED_LENGTH[codes.COLOR_PALETTE]
                elif kind == codes.COLOR_TRUECOLOR:
                    marks.pop(field, None)
                    position += codes.EXTENDED_LENGTH[codes.COLOR_TRUECOLOR]
        super().select_graphic_rendition(*attrs)
        self.cursor.attrs = self.cursor.attrs._replace(blink=dim, **marks)
