import json

import psycopg
from pglast.parser import parse_sql_json

from db import (
    app_transaction,
    connect,
    insert_audit,
    require_user,
    validate_answer,
)

TABLES = {"customers", "products", "orders", "order_items"}
FUNCTIONS = {
    "count", "sum", "avg", "min", "max", "round",
    "lower", "upper", "length", "abs",
}
TYPES = {
    "int2", "int4", "int8", "numeric", "float4", "float8",
    "text", "varchar", "bpchar", "date", "timestamp",
    "timestamptz", "bool",
}


def name_parts(items):
    return [item["String"]["sval"] for item in items]


def inspect_tree(value):
    if isinstance(value, list):
        for item in value:
            inspect_tree(item)
        return

    if not isinstance(value, dict):
        return

    for tag, node in value.items():
        if tag.endswith("Stmt") and tag != "SelectStmt":
            raise ValueError("Only SELECT queries are allowed.")

        if tag == "SelectStmt":
            if node.get("intoClause") or node.get("lockingClause"):
                raise ValueError(
                    "SELECT INTO and row-locking queries are not allowed."
                )

        if tag == "RangeVar":
            if (
                node.get("catalogname")
                or node.get("schemaname") not in (None, "retail")
                or node.get("relname") not in TABLES
            ):
                raise ValueError(
                    "Query only the four tables in the retail schema."
                )

        if tag == "FuncCall":
            parts = name_parts(node["funcname"])
            if (
                len(parts) > 2
                or (len(parts) == 2 and parts[0] != "pg_catalog")
                or parts[-1] not in FUNCTIONS
            ):
                raise ValueError(
                    "That function is not supported by this quiz."
                )

        if tag == "TypeName":
            parts = name_parts(node.get("names", []))
            if (
                not parts
                or len(parts) > 2
                or (len(parts) == 2 and parts[0] != "pg_catalog")
                or parts[-1] not in TYPES
            ):
                raise ValueError("That data type is not supported.")

        if tag == "A_Expr":
            parts = name_parts(node.get("name", []))
            if len(parts) > 1:
                raise ValueError("Custom schema operators are not allowed.")

        inspect_tree(node)


def validate_query(sql_text):
    try:
        tree = json.loads(parse_sql_json(sql_text))
    except Exception:
        raise ValueError("Invalid PostgreSQL syntax. Check your query.") from None

    statements = tree.get("stmts", [])
    if (
        len(statements) != 1
        or "SelectStmt" not in statements[0]["stmt"]
    ):
        raise ValueError("Enter exactly one SELECT query.")

    inspect_tree(statements[0]["stmt"])


def run_query(access_token, question_id, sql_text):
    # Authentication is checked again on every Run action.
    user_id = require_user(access_token)
    validate_answer(question_id, sql_text)

    columns = []
    rows = []
    error = None

    try:
        validate_query(sql_text)

        with connect("TAKER") as conn:
            # Explicitly enforce read-only mode for this transaction.
            conn.read_only = True

            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout = '5s'")
                cur.execute("SET LOCAL lock_timeout = '2s'")
                cur.execute("SET LOCAL search_path = pg_catalog, retail")

                # This is deliberately student-authored SQL, not a value
                # interpolated into an application SQL statement.
                # Validation, restricted credentials, and read-only mode
                # apply before it runs.
                cur.execute(sql_text, prepare=True)

                columns = [column.name for column in cur.description]
                rows = cur.fetchmany(501)

                if len(rows) > 500:
                    raise ValueError(
                        "The result exceeds 500 rows. Add a LIMIT."
                    )

    except ValueError as exc:
        error = str(exc)
    except psycopg.Error as exc:
        error = (
            exc.diag.message_primary
            or "The database could not execute this query."
        )

    # Use the separate application account to record the attempt.
    # If logging fails, the function raises instead of reporting success.
    with app_transaction(user_id) as cur:
        insert_audit(
            cur=cur,
            user_id=user_id,
            question_id=question_id,
            action="run",
            sql_text=sql_text,
            success=error is None,
            row_count=len(rows) if error is None else None,
            error_message=error,
        )

    if error:
        raise ValueError(error)

    return columns, rows