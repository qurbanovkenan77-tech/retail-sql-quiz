"""Offline checks: real Chroma retrieval, mocked Gemini, result validation.

Run: python rag_checks.py. No API key or database credentials required.
This does not replace a live deployed end-to-end test.
"""
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from questions import QUESTIONS
from rag import generate_sql, get_index
from result_validation import validate_result


class RagChecks(unittest.TestCase):
    def test_real_chroma_retrieval_changes_with_question(self):
        index = get_index()
        self.assertEqual(index.collection.count(), 7)
        for question in QUESTIONS:
            retrieved = index.retrieve(question["prompt"])
            self.assertEqual(len(retrieved), 4)
            self.assertEqual(retrieved[0]["id"], f"example-{question['id']}")
        self.assertNotEqual(index.retrieve(QUESTIONS[0]["prompt"])[0]["id"],
                            index.retrieve(QUESTIONS[3]["prompt"])[0]["id"])

    def test_authentication_precedes_retrieval_and_api(self):
        with patch("rag.get_index") as index, patch("rag.requests.post") as api:
            with self.assertRaises(PermissionError):
                generate_sql(None, "Show all products")
            index.assert_not_called()
            api.assert_not_called()

    def test_retrieved_context_is_sent_to_api(self):
        response = Mock(status_code=200)
        response.json.return_value = {"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{
                "text": "```sql\nSELECT product_name FROM retail.products;\n```"
            }]}
        }]}
        with patch("rag.require_user", return_value="test-user"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-placeholder"}), \
             patch("rag.requests.post", return_value=response) as api:
            result = generate_sql("test-token", QUESTIONS[0]["prompt"])
        self.assertEqual(result["sql"], "SELECT product_name FROM retail.products;")
        sent = api.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
        for doc in result["context"]:
            self.assertIn(doc["text"], sent)
        self.assertEqual(len(result["context"]), 4)

    def test_quota_error_is_readable(self):
        with patch("rag.require_user", return_value="test-user"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-placeholder"}), \
             patch("rag.requests.post", return_value=Mock(status_code=429)):
            with self.assertRaisesRegex(ValueError, "quota"):
                generate_sql("test-token", QUESTIONS[0]["prompt"])

    def test_validation_accepts_decimal_dates_and_aliases(self):
        q = QUESTIONS[0]
        rows = [(r["product_name"], Decimal(str(r["price"]))) for r in q["expected_result"]]
        self.assertTrue(validate_result(["item", "cost"], rows, q["expected_result"]))
        q = QUESTIONS[2]
        rows = [(r["order_id"], r["customer_name"], date.fromisoformat(r["order_date"]))
                for r in q["expected_result"]]
        self.assertTrue(validate_result(["id", "name", "date"], rows, q["expected_result"]))

    def test_validation_rejects_wrong_values_order_and_duplicates(self):
        q = QUESTIONS[0]
        rows = [list(r.values()) for r in q["expected_result"]]
        self.assertFalse(validate_result(["name", "price"], rows[::-1], q["expected_result"]))
        self.assertFalse(validate_result(["name", "price"], rows + rows, q["expected_result"]))
        self.assertFalse(validate_result(["name", "price"], [("Headphones", 1)], q["expected_result"]))
        self.assertFalse(validate_result(["name", "price"], [], q["expected_result"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
