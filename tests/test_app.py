import unittest

from werkzeug.datastructures import MultiDict

from app import app
from common_calc.base import receiver
from common_calc.errors import CalculationError


class CalculatorAppTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_page_is_available(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Разделите общие расходы", response.get_data(as_text=True))

    def test_valid_calculation(self):
        response = self.client.post(
            "/",
            data={
                "name": ["Анна", "Борис", "Виктор"],
                "sum": ["1000", "500", "0"],
            },
        )
        html = response.get_data(as_text=True).replace("\u00a0", " ")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Расчёт готов", html)
        self.assertIn("1 500", html)
        self.assertIn("Виктор", html)
        self.assertIn("Анна", html)

    def test_decimal_comma_and_spaces_are_accepted(self):
        response = self.client.post(
            "/",
            data={"name": ["Анна", "Борис"], "sum": ["1 500,50", "499,50"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "2 000", response.get_data(as_text=True).replace("\u00a0", " ")
        )

    def test_invalid_amount_returns_400_and_keeps_values(self):
        response = self.client.post(
            "/",
            data={"name": ["Анна", "Борис"], "sum": ["abc", "200"]},
        )
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("должна быть числом", html)
        self.assertIn('value="abc"', html)
        self.assertIn('value="200"', html)
        self.assertIn('data-error-field="sum-1"', html)

    def test_empty_name_is_rejected(self):
        response = self.client.post(
            "/",
            data={"name": ["   ", "Борис"], "sum": ["100", "200"]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Укажите имя участника", response.get_data(as_text=True))

    def test_duplicate_names_are_rejected(self):
        response = self.client.post(
            "/",
            data={"name": ["Анна", "анна"], "sum": ["100", "200"]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("указано более одного раза", response.get_data(as_text=True))

    def test_empty_form_is_rejected(self):
        response = self.client.post("/", data={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("хотя бы одного участника", response.get_data(as_text=True))

    def test_unknown_page_returns_custom_404(self):
        response = self.client.get("/does-not-exist")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 404)
        self.assertIn("Страница не найдена", html)

    def test_unsupported_method_returns_custom_405(self):
        response = self.client.put("/")

        self.assertEqual(response.status_code, 405)
        self.assertIn("Метод не поддерживается", response.get_data(as_text=True))


class ReceiverTestCase(unittest.TestCase):
    def test_transactions_are_balanced_to_the_cent(self):
        form = MultiDict(
            [
                ("name", "Анна"),
                ("name", "Борис"),
                ("name", "Виктор"),
                ("sum", "0"),
                ("sum", "0"),
                ("sum", "100"),
            ]
        )

        participants, total, average, debts, overpays, transactions = receiver(form)

        self.assertEqual(total, 100)
        self.assertEqual(average, 33.33)
        self.assertEqual(len(participants), 3)
        self.assertEqual(
            round(sum(item["amount"] for item in debts), 2),
            round(sum(item["amount"] for item in overpays), 2),
        )
        self.assertEqual(
            round(sum(item["amount"] for item in transactions), 2), 66.67
        )

    def test_negative_amount_is_rejected(self):
        form = MultiDict([("name", "Анна"), ("sum", "-10")])

        with self.assertRaises(CalculationError):
            receiver(form)

    def test_mismatched_fields_are_rejected(self):
        form = MultiDict([("name", "Анна"), ("name", "Борис"), ("sum", "10")])

        with self.assertRaises(CalculationError):
            receiver(form)


if __name__ == "__main__":
    unittest.main()
