"""
Выбор основного шрифта из списка кандидатов и запасных шрифтов для недостающих символов.
"""

from collections.abc import Sequence
from functools import cache

from termsnap.errors import FontNotFound
from termsnap.png.fonts.families import DEFAULT_FAMILIES, FALLBACK_FAMILIES
from termsnap.png.fonts.fontset import FontSet
from termsnap.png.fonts.glyphs import missing_glyphs
from termsnap.png.fonts.search import find_family

#: Как можно задать основной шрифт: готовый ``FontSet`` (``find_family``, ``from_files``), имя семейства или список
#: семейств в порядке предпочтения.
type FontSpec = FontSet | str | Sequence[str]


def resolve(families: Sequence[str] = DEFAULT_FAMILIES, *, covers: str = "") -> FontSet:
    """
    Первое из семейств, которое установлено и содержит все символы ``covers``; иначе ``FontNotFound`` с причиной
    отказа по каждому семейству.
    """
    problems = []
    for family in families:
        fontset = find_family(family)
        if fontset is None:
            problems.append(f"{family}: не установлен")
            continue
        missing = missing_glyphs(fontset.regular, covers)
        if missing:
            problems.append(f"{family}: нет символов {missing!r}")
            continue
        return fontset
    raise FontNotFound(problems)


def resolve_best(families: Sequence[str] = DEFAULT_FAMILIES, *, covers: str = "") -> FontSet:
    """
    Установленное семейство, в котором есть больше всего символов ``covers`` (при равенстве - более раннее в списке).
    Нужно, когда ни одно семейство не содержит все символы, а недостающие рисуются запасными шрифтами.
    """
    best: tuple[int, FontSet] | None = None  # (сколько символов не хватает, набор)
    problems = []
    for family in families:
        fontset = find_family(family)
        if fontset is None:
            problems.append(f"{family}: не установлен")
            continue
        missing = len(missing_glyphs(fontset.regular, covers))
        if best is None or missing < best[0]:
            best = (missing, fontset)
    if best is None:
        raise FontNotFound(problems)
    return best[1]


def resolve_spec(spec: FontSpec | None, *, covers: str = "") -> FontSet:
    """
    Основной шрифт по любому способу его задать (``FontSpec``); ``None`` - ``DEFAULT_FAMILIES``.

    Из списка берется первое установленное семейство, в котором есть все символы ``covers``; если такого нет (в
    тексте эмодзи или редкие знаки, которых нет ни в одном основном шрифте) - установленное семейство из списка с
    наибольшим числом нужных символов, а недостающие рисуются запасными шрифтами (``FALLBACK_FAMILIES``). Если не
    установлено ни одно семейство из списка - ``FontNotFound`` с причиной по каждому: подставлять шрифт по умолчанию
    вместо явно названного нельзя, документ вышел бы не таким, как просили. Нужен запасной вариант - допишите
    ``*DEFAULT_FAMILIES`` в конец списка.
    """
    if isinstance(spec, FontSet):
        return spec
    families = DEFAULT_FAMILIES if spec is None else (spec,) if isinstance(spec, str) else tuple(spec)
    if not families:
        raise ValueError("список семейств шрифта пуст")
    try:
        return resolve(families, covers=covers)
    except FontNotFound:
        return resolve_best(families, covers=covers)


@cache
def fallback_fontsets() -> tuple[FontSet, ...]:
    """
    Установленные запасные семейства из ``FALLBACK_FAMILIES`` в порядке предпочтения.
    """
    return tuple(fontset for family in FALLBACK_FAMILIES if (fontset := find_family(family)) is not None)
