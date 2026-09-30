from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any


DEFAULT_SETTINGS = {
    "base_currency": "RUB",
    "monthly_budget": 50000.0,
    "budgets": {},
}


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


class JSONStorage:
    def __init__(self, expenses_file: Path, settings_file: Path, rates_file: Path) -> None:
        self.expenses_file = expenses_file
        self.settings_file = settings_file
        self.rates_file = rates_file
        self._lock = RLock()

    def ensure(self) -> None:
        self.expenses_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.expenses_file.exists() or self.expenses_file.stat().st_size == 0:
            write_json(self.expenses_file, [])
        if not self.settings_file.exists() or self.settings_file.stat().st_size == 0:
            write_json(self.settings_file, DEFAULT_SETTINGS.copy())
        if not self.rates_file.exists() or self.rates_file.stat().st_size == 0:
            write_json(self.rates_file, {})

    def expenses(self) -> list[dict[str, Any]]:
        data = read_json(self.expenses_file, [])
        return data if isinstance(data, list) else []

    def save_expenses(self, expenses: list[dict[str, Any]]) -> None:
        with self._lock:
            write_json(self.expenses_file, expenses)

    def settings(self) -> dict[str, Any]:
        data = read_json(self.settings_file, {})
        if not isinstance(data, dict):
            data = {}

        settings = DEFAULT_SETTINGS.copy()
        settings.update(data)
        budgets = settings.get("budgets")
        if not isinstance(budgets, dict):
            budgets = {}
        settings["budgets"] = budgets

        # Backward compatibility: migrate the old global budget to the current month
        # only when a per-month budget has not yet been configured.
        return settings

    def save_settings(self, settings: dict[str, Any]) -> None:
        with self._lock:
            write_json(self.settings_file, settings)

    def rates(self) -> dict[str, Any]:
        data = read_json(self.rates_file, {})
        return data if isinstance(data, dict) else {}

    def save_rates(self, rates: dict[str, Any]) -> None:
        with self._lock:
            write_json(self.rates_file, rates)
