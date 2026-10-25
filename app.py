import pandas as pd

from db import load_answers, save_answer
from query_runner import run_query
from questions import QUESTIONS
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).with_name(".env"))

st.set_page_config(page_title="Retail SQL Quiz", page_icon="🛒")
st.title("Retail SQL Quiz")
st.caption("5 questions • 20 points • Live PostgreSQL database")
st.caption("Now with RAG: ask a question, generate SQL, and validate its results.")

# Each browser session gets its own authentication client.
# Do not put this client in a shared cache.
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_PUBLISHABLE_KEY"],
    )

supabase = st.session_state.supabase


def verified_user():
    """Ask Supabase to verify the current user's token."""
    try:
        session = supabase.auth.get_session()
        if session is None:
            return None
        return supabase.auth.get_user(session.access_token).user
    except Exception:
        return None


user = verified_user()

if user is None:
    st.info("Sign in to run SQL queries and save your answers.")

    sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Create account"])

    with sign_in_tab:
        with st.form("sign_in", clear_on_submit=True):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in")

        if submitted:
            try:
                supabase.auth.sign_in_with_password(
                    {"email": email.strip(), "password": password}
                )
            except Exception:
                st.error(
                    "Sign-in failed. Check your email, password, "
                    "and whether your email is confirmed."
                )
            else:
                st.rerun()

    with sign_up_tab:
        with st.form("sign_up", clear_on_submit=True):
            new_email = st.text_input("Email address")
            new_password = st.text_input(
                "Choose a password", type="password"
            )
            confirm_password = st.text_input(
                "Confirm password", type="password"
            )
            create_account = st.form_submit_button("Create account")

        if create_account:
            if not new_email.strip():
                st.error("Enter your email address.")
            elif len(new_password) < 12:
                st.error("Use a password with at least 12 characters.")
            elif new_password != confirm_password:
                st.error("The passwords do not match.")
            else:
                try:
                    response = supabase.auth.sign_up(
                        {
                            "email": new_email.strip(),
                            "password": new_password,
                        }
                    )
                except Exception:
                    st.error(
                        "Account creation failed. Check your details "
                        "and try again."
                    )
                else:
                    if response.session:
                        st.rerun()
                    else:
                        st.success(
                            "Check your email for a confirmation link, "
                            "then return here and sign in."
                        )

    # Nothing below this line runs for signed-out visitors.
    st.stop()

st.success(f"Signed in as {user.email}")

if st.button("Sign out"):
    try:
        supabase.auth.sign_out({"scope": "local"})
    except Exception:
        pass
    st.session_state.clear()
    st.rerun()

with st.expander("Database tables and columns"):
    st.markdown(
        """
- **retail.customers:** customer_id, customer_name, city
- **retail.products:** product_id, product_name, category, price
- **retail.orders:** order_id, customer_id, order_date, status
- **retail.order_items:** order_id, product_id, quantity, unit_price

Join customers to orders using **customer_id**.
Join orders to order_items using **order_id**.
Join order_items to products using **product_id**.

Order status is either **completed** or **cancelled**.
For historical spending, use **order_items.unit_price**.
"""
    )


def current_token():
    session = supabase.auth.get_session()
    if session is None:
        raise PermissionError("Please sign in again.")
    return session.access_token


question_id = st.selectbox(
    "Choose a question",
    options=[q["id"] for q in QUESTIONS],
    format_func=lambda qid: (
        f"Question {qid}: {QUESTIONS[qid - 1]['title']} — 4 points"
    ),
)

question = QUESTIONS[question_id - 1]

st.subheader(question["title"])
st.write(question["prompt"])

with st.expander("Hint, expected SQL, and expected result"):
    st.write(question["hint"])
    st.code(question["expected_sql"], language="sql")
    st.dataframe(
        pd.DataFrame(question["expected_result"]),
        hide_index=True,
    )

editor_key = f"answer_{user.id}_{question_id}"

if editor_key not in st.session_state:
    try:
        saved_answers = load_answers(current_token())
        st.session_state[editor_key] = saved_answers.get(question_id, "")
    except Exception:
        st.error(
            "Could not load saved answers. Check the terminal and "
            "database configuration before continuing."
        )
        st.stop()

sql_text = st.text_area(
    "Write your SQL",
    key=editor_key,
    height=220,
    placeholder="SELECT ... FROM retail.products;",
)

run_column, save_column = st.columns(2)

with run_column:
    run_clicked = st.button("Run SQL", type="primary")

with save_column:
    save_clicked = st.button("Save answer")

if run_clicked:
    try:
        columns, rows = run_query(
            current_token(), question_id, sql_text
        )
    except (ValueError, PermissionError) as exc:
        st.error(str(exc))
    except Exception:
        st.error(
            "Could not complete the query and audit logging. "
            "Check your database connection and permissions."
        )
    else:
        st.success(f"Query completed: {len(rows)} row(s).")
        st.dataframe(
            pd.DataFrame(rows, columns=columns),
            hide_index=True,
        )

if save_clicked:
    try:
        save_answer(current_token(), question_id, sql_text)
    except (ValueError, PermissionError) as exc:
        st.error(str(exc))
    except Exception:
        st.error(
            "Your answer was not saved. Check your database "
            "connection and permissions."
        )
    else:
        st.success("Answer saved to your account.")

st.divider()
st.header("AI SQL assistant")
st.write("Ask the selected quiz question in plain English. The assistant retrieves relevant knowledge from ChromaDB and sends it to Gemini.")
natural_question = st.text_area(
    "Your question in plain English",
    value=question["prompt"],
    key=f"natural_{user.id}_{question_id}",
    max_chars=2000,
)
auto_execute = st.checkbox("Automatically run generated SQL and validate the result", value=True)
st.caption(f"Validation compares the result with Quiz Question {question_id}. If you change what the question asks, its expected result may no longer apply.")
rag_key = f"rag_{user.id}_{question_id}"

if st.button("Generate SQL", type="primary"):
    st.session_state.pop(rag_key, None)
    try:
        # Lazy import keeps the original quiz usable before RAG is initialized.
        from rag import generate_sql

        with st.spinner("Retrieving knowledge and asking Gemini…"):
            generated = generate_sql(current_token(), natural_question)
        st.session_state[rag_key] = generated
        if auto_execute:
            try:
                from result_validation import validate_result

                with st.spinner("Running read-only SQL and checking results…"):
                    result_columns, result_rows = run_query(
                        current_token(), question_id, generated["sql"]
                    )
                generated["columns"] = result_columns
                generated["rows"] = result_rows
                generated["matches"] = validate_result(
                    result_columns, result_rows, question["expected_result"]
                )
            except (ValueError, PermissionError) as exc:
                generated["execution_error"] = str(exc)
            except Exception:
                generated["execution_error"] = "Execution or audit logging failed. Check database configuration and permissions."
    except (ValueError, PermissionError) as exc:
        st.error(str(exc))
    except Exception:
        st.error("Could not initialize RAG. Check that the new requirements are installed, then check your app logs.")

if rag_key in st.session_state:
    generated = st.session_state[rag_key]
    st.write("**Question:**", generated["question"])
    st.subheader("Generated SQL")
    st.code(generated["sql"], language="sql")
    st.caption(f"AI API: Gemini • Model: {generated['model']}")
    with st.expander("Retrieved knowledge — ChromaDB vector search"):
        st.caption("TF-IDF vectors with cosine distance. Lower distance means closer vocabulary. These documents were retrieved before the API call.")
        for document in generated["context"]:
            st.markdown(f"**{document['title']}** — distance {document['distance']:.4f}")
            st.text(document["text"])
    if "execution_error" in generated:
        st.error(generated["execution_error"])
        st.info("SQL generation completed, but execution did not. You can edit the SQL in the quiz editor above and run it manually.")
    elif "rows" in generated:
        st.subheader("Executed result")
        st.dataframe(pd.DataFrame(generated["rows"], columns=generated["columns"]), hide_index=True)
        if generated["matches"]:
            st.success(f"Correct: result matches the expected answer for Question {question_id}.")
        else:
            st.warning(f"Result does not match the expected answer for Question {question_id}.")
        st.caption("Validation compares values, row order, and column order; SQL wording and column aliases may differ.")
    else:
        st.info("Automatic execution was disabled for this generation. Copy the SQL into the quiz editor above to run or save it.")
