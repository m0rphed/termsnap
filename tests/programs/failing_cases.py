def test_addition():
    assert 1 + 1 == 2


def test_list_diff():
    expected = [1, 2, 3]
    actual = [1, 2, 4]
    assert actual == expected


def test_text():
    assert "термин" in "словарь"
