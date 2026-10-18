import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


def connect(account):
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ[f"DB_{account}_USER"],
        password=os.environ[f"DB_{account}_PASSWORD"],
        sslmode="require",
        connect_timeout=10,
    )


def main():
    with connect("TAKER") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user")
            print("Query account:", cur.fetchone()[0])

            cur.execute("SELECT COUNT(*) FROM retail.products")
            count = cur.fetchone()[0]
            assert count == 6, f"Expected 6 products, got {count}"
            print("Products:", count)

            cur.execute(
                """
                SELECT
                    has_table_privilege(
                        current_user, c.oid, 'UPDATE'
                    ),
                    has_table_privilege(
                        current_user, c.oid, 'DELETE'
                    )
                FROM pg_catalog.pg_class AS c
                JOIN pg_catalog.pg_namespace AS n
                    ON n.oid = c.relnamespace
                WHERE n.nspname = 'quiz_private'
                  AND c.relname = 'audit_log'
                """
            )
            can_update, can_delete = cur.fetchone()
            assert not can_update and not can_delete
            print("Taker cannot update or delete audit entries: PASS")

    with connect("APP") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user")
            print("Application account:", cur.fetchone()[0])

            cur.execute(
                """
                SELECT has_table_privilege(
                    current_user,
                    'quiz_private.audit_log',
                    'INSERT'
                )
                """
            )
            assert cur.fetchone()[0]
            print("Application can insert audit entries: PASS")

    print("Both database connections passed!")


if __name__ == "__main__":
    main()