from datetime import date, datetime
from decimal import Decimal

import psycopg

from db import connect, load_answers, save_answer
from query_runner import run_query, validate_query
from questions import QUESTIONS


def normalize(value):
    """Compare equivalent database and expected-result values."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    return value


def check_expected_results():
    assert sum(q["points"] for q in QUESTIONS) == 20

    with connect("TAKER") as conn:
        conn.read_only = True

        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute("SET LOCAL search_path = pg_catalog, retail")

            for question in QUESTIONS:
                validate_query(question["expected_sql"])
                cur.execute(question["expected_sql"], prepare=True)

                columns = [column.name for column in cur.description]
                actual = [
                    {
                        column: normalize(value)
                        for column, value in zip(columns, row)
                    }
                    for row in cur.fetchall()
                ]

                expected = [
                    {
                        column: normalize(value)
                        for column, value in row.items()
                    }
                    for row in question["expected_result"]
                ]

                assert actual == expected, (
                    f"Question {question['id']} result mismatch: "
                    f"{actual!r}"
                )
                print(f"PASS: Question {question['id']} expected result")


def expect_permission_denied(account, statement):
    with connect(account) as conn:
        # Test actual permissions, not just the read-only default.
        conn.read_only = False

        try:
            with conn.cursor() as cur:
                cur.execute(statement)
        except psycopg.errors.InsufficientPrivilege:
            print(f"PASS: {account} denied: {statement}")
        else:
            raise AssertionError(
                f"{account} unexpectedly permitted: {statement}"
            )
        finally:
            # Never retain changes made by a permission test.
            conn.rollback()


def check_integrity():
    # WHERE false avoids changing rows even if permissions are wrong.
    for account in ("TAKER", "APP"):
        expect_permission_denied(
            account,
            """
            UPDATE quiz_private.audit_log
            SET success = false
            WHERE false
            """,
        )

        expect_permission_denied(
            account,
            "DELETE FROM quiz_private.audit_log WHERE false",
        )

    expect_permission_denied(
        "TAKER",
        """
        UPDATE retail.products
        SET price = 1
        WHERE false
        """,
    )

    # TRUNCATE requires its own privilege, separate from DELETE.
    with connect("TAKER") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT has_table_privilege(
                    current_user, c.oid, 'TRUNCATE'
                )
                FROM pg_catalog.pg_class AS c
                JOIN pg_catalog.pg_namespace AS n
                    ON n.oid = c.relnamespace
                WHERE n.nspname = 'quiz_private'
                  AND c.relname = 'audit_log'
                """
            )
            result = cur.fetchone()
            assert result is not None and result[0] is False
            print("PASS: TAKER has no audit-log TRUNCATE permission")


def check_signed_out_access():
    actions = [
        lambda: load_answers(None),
        lambda: save_answer(None, 1, "SELECT 1"),
        lambda: run_query(None, 1, "SELECT 1"),
    ]

    for action in actions:
        try:
            action()
        except PermissionError:
            pass
        else:
            raise AssertionError("Signed-out access was allowed.")

    print("PASS: Signed-out loading, saving, and running are blocked")


def check_query_validation():
    blocked_queries = [
        "DELETE FROM retail.products",
        "SELECT 1; SELECT 2",
        "SELECT * FROM quiz_private.audit_log",
        "SELECT pg_sleep(10)",
        "SELECT * INTO copied_products FROM retail.products",
        """
        WITH removed AS (
            DELETE FROM retail.products RETURNING *
        )
        SELECT * FROM removed
        """,
    ]

    for query in blocked_queries:
        try:
            validate_query(query)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Unsafe query accepted: {query}")

    print("PASS: Prohibited SQL is rejected")


if __name__ == "__main__":
    check_signed_out_access()
    check_query_validation()
    check_expected_results()
    check_integrity()
    print("\nALL CHECKS PASSED")