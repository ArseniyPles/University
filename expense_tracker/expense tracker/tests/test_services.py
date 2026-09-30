import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from models.expense import Expense, ValidationError, validate_expense_payload
from services.analysis_service import analyze_expenses, compare_with_previous_month
from services.budget_service import budget_info
from services.currency_service import APIError, CurrencyService
from services.expense_service import ExpenseService
from storage.json_storage import JSONStorage


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.storage = JSONStorage(
            base / "expenses.json", base / "settings.json", base / "rates.json"
        )
        self.storage.ensure()
        self.currency = CurrencyService(self.storage)
        self.expenses = ExpenseService(self.storage, self.currency)

    def tearDown(self):
        self.tmp.cleanup()

    def test_validation_rejects_negative_amount(self):
        with self.assertRaises(ValidationError):
            validate_expense_payload({
                "date": "2026-09-30",
                "amount": "-1",
                "currency": "RUB",
                "category": "Еда",
                "description": "test",
            })

    def test_validation_rejects_future_date(self):
        with self.assertRaises(ValidationError):
            validate_expense_payload({
                "date": "2099-12-31",
                "amount": "100",
                "currency": "RUB",
                "category": "Еда",
                "description": "future",
            })

    def test_analysis_and_budget(self):
        items = [
            Expense(1, "2026-09-01", 1000, "RUB", "Еда", "A", 1, "2026-09-01", "local", 1000),
            Expense(2, "2026-09-02", 500, "RUB", "Еда", "B", 1, "2026-09-02", "local", 500),
            Expense(3, "2026-09-02", 300, "RUB", "Транспорт", "C", 1, "2026-09-02", "local", 300),
        ]
        result = analyze_expenses(items, 2026, 9)
        self.assertEqual(result["total"], 1800.0)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["average"], 600.0)
        info = budget_info(result, Decimal("2000"), 2026, 9)
        self.assertEqual(info["remaining"], 200.0)
        self.assertIn(info["status"], {"ok", "risk"})
        self.assertTrue(info["has_budget"])

    def test_analysis_contains_all_days_of_month(self):
        items = [Expense(1, "2026-09-01", 1000, "RUB", "Еда", "A", 1, "2026-09-01", "local", 1000)]
        result = analyze_expenses(items, 2026, 9)
        self.assertEqual(len(result["days"]), 30)
        self.assertEqual(result["days"][0]["amount"], 1000.0)
        self.assertEqual(result["days"][-1]["amount"], 0.0)

    def test_compare_with_previous_month(self):
        items = [
            Expense(1, "2026-08-10", 1000, "RUB", "Еда", "A", 1, "2026-08-10", "local", 1000),
            Expense(2, "2026-09-10", 1500, "RUB", "Еда", "B", 1, "2026-09-10", "local", 1500),
        ]
        result = compare_with_previous_month(items, 2026, 9)
        self.assertEqual(result["difference"], 500.0)
        self.assertEqual(result["percent"], 50.0)

    def test_budget_exceeded_status(self):
        analysis = {"total": 6000.0, "count": 3, "average": 2000.0}
        info = budget_info(analysis, Decimal("5000"), 2026, 9)
        self.assertEqual(info["remaining"], -1000.0)
        self.assertEqual(info["status"], "exceeded")

    def test_future_period_has_no_forecast(self):
        analysis = {"total": 1200.0, "count": 1, "average": 1200.0}
        info = budget_info(analysis, Decimal("5000"), 2099, 1)
        self.assertTrue(info["is_future"])
        self.assertEqual(info["forecast"], 0.0)
        self.assertEqual(info["elapsed_days"], 0)

    def test_filter_validation(self):
        with self.assertRaises(ValueError):
            self.expenses.list_month(
                2026,
                9,
                {"amount_min": "5000", "amount_max": "1000"},
            )

    @patch("services.currency_service.api_json")
    def test_external_rate_and_cache(self, mock_api):
        mock_api.return_value = {
            "date": "2026-09-30",
            "base": "USD",
            "quote": "RUB",
            "rate": 80.5,
        }
        rate, source, _ = self.currency.get_rate("USD", "RUB", "2026-09-30")
        self.assertEqual(rate, Decimal("80.5"))
        self.assertEqual(source, "api")
        mock_api.reset_mock()
        rate2, source2, _ = self.currency.get_rate("USD", "RUB", "2026-09-30")
        self.assertEqual(rate2, Decimal("80.5"))
        self.assertEqual(source2, "cache")
        mock_api.assert_not_called()

    @patch("services.currency_service.api_json", side_effect=APIError("down"))
    def test_external_rate_failure_raises_controlled_error(self, mock_api):
        with self.assertRaises(APIError):
            self.currency.get_rate("USD", "RUB", "2026-09-30")

    def test_expense_crud_with_rub(self):
        payload = {
            "date": date.today().isoformat(),
            "amount": "125.50",
            "currency": "RUB",
            "category": "Еда",
            "description": "Обед",
        }
        created = self.expenses.add(payload)
        self.assertEqual(created.base_amount, 125.5)
        updated = self.expenses.update(created.id, {**payload, "amount": "200"})
        self.assertEqual(updated.amount, 200.0)
        self.expenses.delete(created.id)
        self.assertEqual(self.expenses.list_all(), [])

    def test_settings_persist_monthly_budget(self):
        settings = self.storage.settings()
        settings["budgets"]["2026-09"] = 75000.0
        self.storage.save_settings(settings)
        loaded = self.storage.settings()
        self.assertEqual(loaded["budgets"]["2026-09"], 75000.0)


if __name__ == "__main__":
    unittest.main()


class AdditionalBudgetTests(unittest.TestCase):
    def test_no_budget_is_explicit(self):
        analysis = {"total": 1200.0, "count": 2, "average": 600.0}
        info = budget_info(analysis, Decimal("0"), 2026, 9)
        self.assertFalse(info["has_budget"])
        self.assertEqual(info["status"], "undefined")

    def test_zero_expenses_with_budget_has_empty_status(self):
        analysis = {"total": 0.0, "count": 0, "average": 0.0}
        info = budget_info(analysis, Decimal("50000"), 2026, 9)
        self.assertTrue(info["has_budget"])
        self.assertEqual(info["status"], "empty")


