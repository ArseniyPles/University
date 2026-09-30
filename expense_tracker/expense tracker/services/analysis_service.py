from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any

from models.expense import Expense, money


def analyze_expenses(expenses: list[Expense], year: int, month: int) -> dict[str, Any]:
    selected = [
        expense for expense in expenses
        if _is_in_month(expense.date, year, month)
    ]
    total = sum((Decimal(str(e.base_amount)) for e in selected), Decimal("0"))
    count = len(selected)
    average = total / count if count else Decimal("0")

    by_category: dict[str, Decimal] = {}
    by_day: dict[str, Decimal] = {}
    for expense in selected:
        amount = Decimal(str(expense.base_amount))
        by_category[expense.category] = by_category.get(expense.category, Decimal("0")) + amount
        by_day[expense.date] = by_day.get(expense.date, Decimal("0")) + amount

    categories = []
    for category, value in sorted(by_category.items(), key=lambda item: item[1], reverse=True):
        share = value / total * 100 if total else Decimal("0")
        categories.append({
            "category": category,
            "amount": float(money(value)),
            "share": float(share.quantize(Decimal("0.1"))),
        })

    return {
        "year": year,
        "month": month,
        "total": float(money(total)),
        "count": count,
        "average": float(money(average)),
        "categories": categories,
        "days": [
            {
                "date": f"{year:04d}-{month:02d}-{day:02d}",
                "amount": float(money(by_day.get(f"{year:04d}-{month:02d}-{day:02d}", Decimal("0")))),
            }
            for day in range(1, monthrange(year, month)[1] + 1)
        ],
    }


def _is_in_month(value: str, year: int, month: int) -> bool:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.year == year and parsed.month == month


def previous_period(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def compare_with_previous_month(expenses: list[Expense], year: int, month: int) -> dict[str, float | int | None]:
    prev_year, prev_month = previous_period(year, month)
    current = analyze_expenses(expenses, year, month)["total"]
    previous = analyze_expenses(expenses, prev_year, prev_month)["total"]
    difference = Decimal(str(current)) - Decimal(str(previous))
    percent = (difference / Decimal(str(previous)) * 100) if previous else None
    return {
        "previous_year": prev_year,
        "previous_month": prev_month,
        "current_total": float(money(current)),
        "previous_total": float(money(previous)),
        "difference": float(money(difference)),
        "percent": float(percent.quantize(Decimal("0.1"))) if percent is not None else None,
    }
