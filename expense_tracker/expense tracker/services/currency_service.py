from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from models.expense import SUPPORTED_CURRENCIES
from storage.json_storage import JSONStorage

API_BASE = "https://api.frankfurter.dev/v2"


class APIError(Exception):
    """Ошибка внешнего сервиса."""


def api_json(url: str, timeout: int = 5) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ExpenseTracker/6.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise APIError("Внешний сервис временно недоступен.") from exc


class CurrencyService:
    def __init__(self, storage: JSONStorage, base_currency: str = "RUB") -> None:
        self.storage = storage
        self.base_currency = base_currency

    @staticmethod
    def _cache_key(expense_date: str, from_currency: str, to_currency: str) -> str:
        return f"{expense_date}:{from_currency}:{to_currency}"

    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        target_date: str | None = None,
    ) -> tuple[Decimal, str, str]:
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        target_date = target_date or date.today().isoformat()

        if from_currency not in SUPPORTED_CURRENCIES or to_currency not in SUPPORTED_CURRENCIES:
            raise APIError("Неподдерживаемая валюта.")
        if from_currency == to_currency:
            return Decimal("1"), "local", target_date

        cache = self.storage.rates()
        key = self._cache_key(target_date, from_currency, to_currency)
        cached = cache.get(key)
        if isinstance(cached, dict) and "rate" in cached:
            try:
                return Decimal(str(cached["rate"])), "cache", str(cached.get("date", target_date))
            except InvalidOperation:
                pass

        target_date_encoded = urllib.parse.quote(target_date)
        endpoint = f"{API_BASE}/rate/{from_currency}/{to_currency}?date={target_date_encoded}"
        last_error: Exception | None = None
        try:
            data = api_json(endpoint)
            rate = Decimal(str(data["rate"]))
            rate_date = str(data.get("date", target_date))
            cache[key] = {"rate": str(rate), "date": rate_date}
            self.storage.save_rates(cache)
            return rate, "api", rate_date
        except (APIError, KeyError, InvalidOperation) as exc:
            last_error = exc

        # For the current day only, a rate may not have been published yet.
        # In that case the latest available quote is a reasonable fallback.
        if target_date == date.today().isoformat():
            try:
                latest_endpoint = f"{API_BASE}/rate/{from_currency}/{to_currency}"
                data = api_json(latest_endpoint)
                rate = Decimal(str(data["rate"]))
                rate_date = str(data.get("date", target_date))
                cache[key] = {"rate": str(rate), "date": rate_date}
                self.storage.save_rates(cache)
                return rate, "api-latest", rate_date
            except (APIError, KeyError, InvalidOperation) as exc:
                last_error = exc

        suffix = f":{from_currency}:{to_currency}"
        cached_candidates = [
            value for cache_key, value in cache.items()
            if cache_key.endswith(suffix) and isinstance(value, dict) and "rate" in value
        ]
        if cached_candidates:
            try:
                latest = sorted(cached_candidates, key=lambda x: str(x.get("date", "")))[-1]
                return Decimal(str(latest["rate"])), "cache-fallback", str(latest.get("date", target_date))
            except InvalidOperation:
                pass

        raise APIError(f"Не удалось получить курс {from_currency}/{to_currency}.") from last_error
