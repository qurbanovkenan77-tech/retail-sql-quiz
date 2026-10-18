BEGIN;

-- Create separate accounts without putting passwords in this file.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'quiz_taker'
    ) THEN
        CREATE ROLE quiz_taker LOGIN
            NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOINHERIT NOREPLICATION NOBYPASSRLS;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'quiz_app'
    ) THEN
        CREATE ROLE quiz_app LOGIN
            NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOINHERIT NOREPLICATION NOBYPASSRLS;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE postgres TO quiz_taker, quiz_app;

-- Student queries can read only our retail dataset.
REVOKE ALL ON SCHEMA retail FROM quiz_taker, quiz_app;
REVOKE ALL ON ALL TABLES IN SCHEMA retail
FROM quiz_taker, quiz_app;

GRANT USAGE ON SCHEMA retail TO quiz_taker;

GRANT SELECT ON
    retail.customers,
    retail.products,
    retail.orders,
    retail.order_items
TO quiz_taker;

ALTER ROLE quiz_taker SET search_path = retail, pg_catalog;
ALTER ROLE quiz_taker SET default_transaction_read_only = on;
ALTER ROLE quiz_taker SET statement_timeout = '5s';
ALTER ROLE quiz_taker SET lock_timeout = '2s';

-- Store application records outside the retail dataset.
CREATE SCHEMA IF NOT EXISTS quiz_private;

REVOKE ALL ON SCHEMA quiz_private
FROM PUBLIC, anon, authenticated, quiz_taker, quiz_app;

CREATE TABLE IF NOT EXISTS quiz_private.saved_answers (
    user_id UUID NOT NULL,
    question_id INTEGER NOT NULL
        CHECK (question_id BETWEEN 1 AND 5),
    sql_text TEXT NOT NULL
        CHECK (length(sql_text) <= 10000),
    saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, question_id)
);

CREATE TABLE IF NOT EXISTS quiz_private.audit_log (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL,
    question_id INTEGER NOT NULL
        CHECK (question_id BETWEEN 1 AND 5),
    action TEXT NOT NULL CHECK (action IN ('run', 'save')),
    sql_text TEXT NOT NULL
        CHECK (length(sql_text) <= 10000),
    success BOOLEAN NOT NULL,
    row_count INTEGER CHECK (row_count >= 0),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Remove automatically assigned privileges.
REVOKE ALL ON ALL TABLES IN SCHEMA quiz_private
FROM PUBLIC, anon, authenticated, quiz_taker, quiz_app;

REVOKE ALL ON ALL SEQUENCES IN SCHEMA quiz_private
FROM PUBLIC, anon, authenticated, quiz_taker, quiz_app;

-- Only the application's separate connection can save or log.
GRANT USAGE ON SCHEMA quiz_private TO quiz_app;

GRANT SELECT, INSERT, UPDATE
ON quiz_private.saved_answers TO quiz_app;

GRANT INSERT
ON quiz_private.audit_log TO quiz_app;

GRANT USAGE
ON SEQUENCE quiz_private.audit_log_audit_id_seq
TO quiz_app;

ALTER ROLE quiz_app SET statement_timeout = '5s';

COMMIT;

-- Check the intended permissions.
SELECT
    has_table_privilege(
        'quiz_taker', 'retail.products', 'SELECT'
    ) AS taker_can_read_products,

    has_table_privilege(
        'quiz_taker', 'retail.products', 'UPDATE'
    ) AS taker_can_edit_products,

    has_table_privilege(
        'quiz_taker', 'quiz_private.audit_log', 'INSERT'
    ) AS taker_can_insert_audit,

    has_table_privilege(
        'quiz_taker', 'quiz_private.audit_log', 'UPDATE'
    ) AS taker_can_edit_audit,

    has_table_privilege(
        'quiz_taker', 'quiz_private.audit_log', 'DELETE'
    ) AS taker_can_delete_audit,

    has_table_privilege(
        'quiz_app', 'quiz_private.audit_log', 'INSERT'
    ) AS app_can_insert_audit,

    has_table_privilege(
        'quiz_app', 'quiz_private.audit_log', 'UPDATE'
    ) AS app_can_edit_audit;