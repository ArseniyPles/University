from __future__ import annotations

from decimal import Decimal
from typing import Any

from models.expense import Expense, money, validate_expense_payload
from services.currency_service import APIError, CurrencyService
from storage.json_storage import JSONStorage


class ExpenseService:
    def __init__(self, storage: JSONStorage, currency_service: CurrencyService) -> None:
        self.storage = storage
        self.currency_service = currency_service

    def list_all(self) -> list[Expense]:
        result: list[Expense] = []
        for item in self.storage.expenses():
            try:
                result.append(Expense.from_dict(item))
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def list_month(self, year: int, month: int, filters: dict[str, str] | None = None) -> list[Expense]:
        filters = filters or {}
        category = filters.get("category", "all")
        text = filters.get("q", "").strip().lower()
        amount_min = self._decimal_filter(filters.get("amount_min", ""), "Минимальная сумма задана некорректно.")
        amount_max = self._decimal_filter(filters.get("amount_max", ""), "Максимальная сумма задана некорректно.")
        if amount_min is not None and amount_max is not None and amount_min > amount_max:
            raise ValueError("Минимальная сумма не может быть больше максимальной.")

        result = []
        for expense in self.list_all():
            if not self._matches_month(expense.date, year, month):
                continue
            if category != "all" and expense.category != category:
                continue
            if text and text not in f"{expense.category} {expense.description}".lower():
                continue
            base_amount = Decimal(str(expense.base_amount))
            if amount_min is not None and base_amount < amount_min:
                continue
            if amount_max is not None and base_amount > amount_max:
                continue
            result.append(expense)
        return sorted(result, key=lambda x: (x.date, x.id), reverse=True)

    @staticmethod
    def _decimal_filter(value: str, message: str) -> Decimal | None:
        if not value:
            return None
        try:
            parsed = Decimal(value.replace(",", "."))
        except Exception as exc:
            raise ValueError(message) from exc
        if parsed < 0:
            raise ValueError(message)
        return parsed

    @staticmethod
    def _matches_month(expense_date: str, year: int, month: int) -> bool:
        return expense_date.startswith(f"{year:04d}-{month:02d}-")

    def add(self, payload: dict[str, Any]) -> Expense:
        clean = validate_expense_payload(payload)
        expenses = self.list_all()
        next_id = max((expense.id for expense in expenses), default=0) + 1
        rate, source, rate_date = self.currency_service.get_rate(
            clean["currency"], self.currency_service.base_currency, clean["date"]
        )
        base_amount = money(clean["amount"] * rate)
        expense = Expense(
            id=next_id,
            date=clean["date"],
            amount=float(clean["amount"]),
            currency=clean["currency"],
            category=clean["category"],
            description=clean["description"],
            exchange_rate=float(rate),
            rate_date=rate_date,
            rate_source=source,
            base_amount=float(base_amount),
        )
        self._save(expenses + [expense])
        return expense

    def update(self, expense_id: int, payload: dict[str, Any]) -> Expense:
        clean = validate_expense_payload(payload)
        expenses = self.list_all()
        if not any(item.id == expense_id for item in expenses):
            raise LookupError("Расход не найден.")
        rate, source, rate_date = self.currency_service.get_rate(
            clean["currency"], self.currency_service.base_currency, clean["date"]
        )
        base_amount = money(clean["amount"] * rate)
        updated = Expense(
            id=expense_id,
            date=clean["date"],
            amount=float(clean["amount"]),
            currency=clean["currency"],
            category=clean["category"],
            description=clean["description"],
            exchange_rate=float(rate),
            rate_date=rate_date,
            rate_source=source,
            base_amount=float(base_amount),
        )
        self._save([updated if item.id == expense_id else item for item in expenses])
        return updated

    def delete(self, expense_id: int) -> None:
        expenses = self.list_all()
        filtered = [item for item in expenses if item.id != expense_id]
        if len(filtered) == len(expenses):
            raise LookupError("Расход не найден.")
        self._save(filtered)

    def _save(self, expenses: list[Expense]) -> None:
        self.storage.save_expenses([expense.to_dict() for expense in expenses])
