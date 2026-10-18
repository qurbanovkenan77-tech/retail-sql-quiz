import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).with_name(".env"))


def connect(account):
    """Open a separate connection using the requested database role."""
    if account not in {"TAKER", "APP"}:
        raise ValueError("Unknown database account.")

    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ[f"DB_{account}_USER"],
        password=os.environ[f"DB_{account}_PASSWORD"],
        sslmode="require",
        connect_timeout=10,
    )


def require_user(access_token):
    """Verify the token with Supabase before accessing quiz data."""
    if not access_token:
        raise PermissionError("Sign in before using the quiz.")

    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_PUBLISHABLE_KEY"],
    )

    try:
        response = client.auth.get_user(access_token)
        if response.user is None:
            raise ValueError("No authenticated user.")
        return str(response.user.id)
    except Exception:
        raise PermissionError(
            "Your sign-in could not be verified. Please sign in again."
        ) from None


def validate_answer(question_id, sql_text):
    if question_id not in {1, 2, 3, 4, 5}:
        raise ValueError("Unknown question.")

    if not isinstance(sql_text, str) or not sql_text.strip():
        raise ValueError("Enter a SQL query first.")

    if len(sql_text) > 10000:
        raise ValueError("Keep your query under 10,000 characters.")


@contextmanager
def app_transaction(user_id):
    """Set the verified identity for this transaction's RLS policies."""
    with connect("APP") as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.user_id', %s, true)",
                (user_id,),
            )
            yield cur


def insert_audit(
    cur,
    user_id,
    question_id,
    action,
    sql_text,
    success,
    row_count=None,
    error_message=None,
):
    """Insert an audit entry using parameters, never SQL interpolation."""
    cur.execute(
        """
        INSERT INTO quiz_private.audit_log (
            user_id,
            question_id,
            action,
            sql_text,
            success,
            row_count,
            error_message
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            question_id,
            action,
            sql_text,
            success,
            row_count,
            error_message,
        ),
    )


def load_answers(access_token):
    """Return only the verified user's saved answers."""
    user_id = require_user(access_token)

    with app_transaction(user_id) as cur:
        cur.execute(
            """
            SELECT question_id, sql_text
            FROM quiz_private.saved_answers
            WHERE user_id = %s
            ORDER BY question_id
            """,
            (user_id,),
        )
        return dict(cur.fetchall())


def save_answer(access_token, question_id, sql_text):
    """Save an answer and its audit entry in the same transaction."""
    user_id = require_user(access_token)
    validate_answer(question_id, sql_text)

    with app_transaction(user_id) as cur:
        cur.execute(
            """
            INSERT INTO quiz_private.saved_answers (
                user_id, question_id, sql_text
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, question_id)
            DO UPDATE SET
                sql_text = EXCLUDED.sql_text,
                saved_at = now()
            """,
            (user_id, question_id, sql_text),
        )

        insert_audit(
            cur=cur,
            user_id=user_id,
            question_id=question_id,
            action="save",
            sql_text=sql_text,
            success=True,
        )