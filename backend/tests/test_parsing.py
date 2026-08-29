from app.services.parsing import parse_codes


def test_splits_on_whitespace_comma_semicolon():
    assert parse_codes("T1566.001, T1078; T1021.001\nT1059.001") == [
        "T1566.001",
        "T1078",
        "T1021.001",
        "T1059.001",
    ]


def test_uppercases_and_dedupes_preserving_order():
    assert parse_codes("t1078, T1078, t1078") == ["T1078"]


def test_empty_input_returns_empty_list():
    assert parse_codes("   ") == []
