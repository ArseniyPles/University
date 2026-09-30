from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

MONEY_QUANT = Decimal("0.01")
DEFAULT_CATEGORIES = [
    "Еда", "Транспорт", "Покупки", "Развлечения",
    "Здоровье", "Жильё", "Образование", "Другое",
]
SUPPORTED_CURRENCIES = ["RUB", "USD", "EUR", "CNY", "GBP"]


class ValidationError(ValueError):
    """Ошибка пользовательских данных."""


def money(value: Decimal | float | int | str) -> Decimal:
    try:
        return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("Некорректная денежная сумма.") from exc


@dataclass
class Expense:
    id: int
    date: str
    amount: float
    currency: str
    category: str
    description: str
    exchange_rate: float
    rate_date: str
    rate_source: str
    base_amount: float
    base_currency: str = "RUB"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Expense":
        return cls(
            id=int(data["id"]),
            date=str(data["date"]),
            amount=float(data["amount"]),
            currency=str(data["currency"]),
            category=str(data["category"]),
            description=str(data.get("description", "")),
            exchange_rate=float(data.get("exchange_rate", 1.0)),
            rate_date=str(data.get("rate_date", data["date"])),
            rate_source=str(data.get("rate_source", "local")),
            base_amount=float(data.get("base_amount", data["amount"])),
            base_currency=str(data.get("base_currency", "RUB")),
        )


def validate_expense_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_date = str(payload.get("date", "")).strip()
    raw_amount = str(payload.get("amount", "")).strip().replace(",", ".")
    currency = str(payload.get("currency", "")).strip().upper()
    category = str(payload.get("category", "")).strip()
    description = str(payload.get("description", "")).strip()

    try:
        parsed_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ValidationError("Некорректная дата.") from exc

    amount = money(raw_amount)
    if amount <= 0:
        raise ValidationError("Сумма должна быть больше нуля.")
    if currency not in SUPPORTED_CURRENCIES:
        raise ValidationError("Выбрана неподдерживаемая валюта.")
    if category not in DEFAULT_CATEGORIES:
        raise ValidationError("Выбрана неподдерживаемая категория.")
    if parsed_date > date.today():
        raise ValidationError("Дата расхода не может быть в будущем.")
    if len(description) > 120:
        raise ValidationError("Описание не должно превышать 120 символов.")

    return {
        "date": parsed_date.isoformat(),
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": description,
    }
