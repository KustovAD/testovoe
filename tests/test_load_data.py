from datetime import datetime

from app.load_data import parse_row, parse_rubrics


def test_parse_rubrics():
    assert parse_rubrics("['VK-1', 'VK-2']") == ["VK-1", "VK-2"]
    assert parse_rubrics("[]") == []
    assert parse_rubrics("") == []
    assert parse_rubrics("a, b") == ["a", "b"]


def test_parse_row():
    row = {"text": "hello", "created_date": "2019-07-04 19:30:46", "rubrics": "['VK-1']"}
    assert parse_row(row) == {
        "text": "hello",
        "created_date": datetime(2019, 7, 4, 19, 30, 46),
        "rubrics": ["VK-1"],
    }
    assert parse_row({**row, "id": "7"})["id"] == 7
