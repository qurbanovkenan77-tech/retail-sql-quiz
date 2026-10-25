"""Compare result values with the selected quiz's expected table."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def cells_equal(actual, expected):
    if actual is None or expected is None:
        return actual is None and expected is None
    if isinstance(actual, (date, datetime)):
        actual = actual.isoformat()
    if isinstance(actual, (int, float, Decimal)) and not isinstance(actual, bool):
        try:
            return abs(Decimal(str(actual)) - Decimal(str(expected))) <= Decimal("0.000001")
        except InvalidOperation:
            return False
    return actual == expected


def validate_result(columns, rows, expected):
    if not expected:
        return not rows
    expected_rows = [list(row.values()) for row in expected]
    if len(columns) != len(expected_rows[0]) or len(rows) != len(expected_rows):
        return False
    # All five prompts request an order. Compare values in column/row order;
    # column aliases do not have to match and SQL text is never compared.
    return all(
        len(actual) == len(wanted)
        and all(cells_equal(a, b) for a, b in zip(actual, wanted))
        for actual, wanted in zip(rows, expected_rows)
    )
