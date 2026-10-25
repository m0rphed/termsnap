def test_addition():
    assert 1 + 1 == 2


def test_dict_diff():
    expected = {"name": "Иван", "age": 30, "tags": ["a", "b"]}
    actual = {"name": "Иван", "age": 31, "tags": ["a", "c"]}
    assert actual == expected


def test_text():
    assert "термин" in "словарь"
