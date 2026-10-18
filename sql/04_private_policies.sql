BEGIN;

ALTER TABLE quiz_private.saved_answers
ENABLE ROW LEVEL SECURITY;

ALTER TABLE quiz_private.audit_log
ENABLE ROW LEVEL SECURITY;

CREATE POLICY read_own_answers
ON quiz_private.saved_answers
FOR SELECT TO quiz_app
USING (
    user_id = NULLIF(
        current_setting('app.user_id', true), ''
    )::uuid
);

CREATE POLICY insert_own_answers
ON quiz_private.saved_answers
FOR INSERT TO quiz_app
WITH CHECK (
    user_id = NULLIF(
        current_setting('app.user_id', true), ''
    )::uuid
);

CREATE POLICY update_own_answers
ON quiz_private.saved_answers
FOR UPDATE TO quiz_app
USING (
    user_id = NULLIF(
        current_setting('app.user_id', true), ''
    )::uuid
)
WITH CHECK (
    user_id = NULLIF(
        current_setting('app.user_id', true), ''
    )::uuid
);

CREATE POLICY insert_own_audit_entries
ON quiz_private.audit_log
FOR INSERT TO quiz_app
WITH CHECK (
    user_id = NULLIF(
        current_setting('app.user_id', true), ''
    )::uuid
);

COMMIT;