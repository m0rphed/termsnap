"""
Имена семейств шрифтов, которые библиотека пробует по умолчанию.
"""

#: Семейства по умолчанию: сначала самые подходящие для кода (без лигатур и с кириллицей), потом штатные шрифты
#: платформ (Windows, macOS, Linux) и запасной вариант.
DEFAULT_FAMILIES = (
    "JetBrains Mono NL",  # вариант без лигатур, поэтому первый
    "JetBrains Mono",
    "Cascadia Mono",  # Windows Terminal
    "Consolas",  # Windows
    "Menlo",  # macOS
    "DejaVu Sans Mono",  # Linux
    "Liberation Mono",
    "Noto Sans Mono",
    "Courier New",  # есть почти везде, но кириллицы и псевдографики может не хватать
)

#: Запасные семейства для символов, которых нет в основном шрифте (эмодзи, стрелки, математические и прочие знаки);
#: они не обязаны быть моноширинными: каждый символ ставится в свою клетку. Порядок важен: первое семейство, в
#: котором есть глиф, и рисует символ.
FALLBACK_FAMILIES = (
    # эмодзи и символы
    "Segoe UI Emoji",
    "Segoe UI Symbol",
    "Noto Color Emoji",
    "Apple Color Emoji",
    "Noto Sans Symbols 2",
    "Noto Sans Symbols",
    "Symbola",
    "DejaVu Sans",
    "Arial Unicode MS",
    "Segoe UI",
    # иероглифы
    "MS Gothic",
    "Microsoft YaHei",
    "Yu Gothic",
    "Malgun Gothic",
    "Noto Sans Mono CJK SC",
    "Noto Sans CJK SC",
    "PingFang SC",
    "Hiragino Sans GB",
    "WenQuanYi Micro Hei",
)
