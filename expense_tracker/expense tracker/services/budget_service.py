from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any

from models.expense import money


def budget_info(
    analysis: dict[str, Any],
    budget: Decimal,
    year: int,
    month: int,
) -> dict[str, Any]:
    total = Decimal(str(analysis["total"]))
    days_total = monthrange(year, month)[1]
    today = date.today()

    if (year, month) < (today.year, today.month):
        elapsed = days_total
    elif (year, month) == (today.year, today.month):
        elapsed = min(today.day, days_total)
    else:
        elapsed = 0

    effective_days = max(1, elapsed)
    avg_per_day = total / effective_days if total else Decimal("0")
    forecast = avg_per_day * days_total if elapsed else Decimal("0")
    remaining = budget - total
    percent_used = total / budget * 100 if budget > 0 else Decimal("0")

    if total == 0:
        status = "empty"
    elif budget > 0 and total > budget:
        status = "exceeded"
    elif budget > 0 and forecast > budget and elapsed:
        status = "risk"
    elif budget > 0:
        status = "ok"
    else:
        status = "undefined"

    return {
        "budget": float(money(budget)),
        "spent": float(money(total)),
        "remaining": float(money(remaining)),
        "percent_used": float(percent_used.quantize(Decimal("0.1"))),
        "avg_per_day": float(money(avg_per_day)),
        "forecast": float(money(forecast)),
        "forecast_over_budget": float(money(forecast - budget))
        if elapsed and budget > 0 and forecast > budget
        else 0.0,
        "year": year,
        "month": month,
        "elapsed_days": elapsed,
        "month_days": days_total,
        "is_future": elapsed == 0,
        "status": status,
        "has_budget": budget > 0,
    }
