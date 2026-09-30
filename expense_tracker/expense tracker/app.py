from __future__ import annotations

import csv
import io
import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urlparse

from models.expense import DEFAULT_CATEGORIES, SUPPORTED_CURRENCIES, Expense
from services.analysis_service import analyze_expenses, compare_with_previous_month
from services.budget_service import budget_info
from services.currency_service import APIError, CurrencyService
from services.expense_service import ExpenseService
from storage.json_storage import JSONStorage

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPENSES_FILE = DATA_DIR / "expenses.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
RATES_FILE = DATA_DIR / "rates.json"
HTML_FILE = BASE_DIR / "templates" / "index.html"
STATIC_DIR = BASE_DIR / "static"

STORAGE = JSONStorage(EXPENSES_FILE, SETTINGS_FILE, RATES_FILE)
STORAGE.ensure()
CURRENCY_SERVICE = CurrencyService(STORAGE)
EXPENSE_SERVICE = ExpenseService(STORAGE, CURRENCY_SERVICE)


def json_response(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def text_response(handler: BaseHTTPRequestHandler, content: str, content_type: str, status: int = 200) -> None:
    data = content.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_request_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("Некорректная длина запроса.") from exc
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Некорректный JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Ожидался JSON-объект.")
    return payload


def query_dict(path: str) -> dict[str, str]:
    parsed = parse_qs(urlparse(path).query)
    return {key: values[-1] for key, values in parsed.items() if values}


def escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


class ExpenseTrackerHandler(BaseHTTPRequestHandler):
    server_version = "ExpenseTracker/7.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        routes = {
            "/": self.serve_index,
            "/api/data": lambda: self.api_data(query_dict(self.path)),
            "/api/rate": lambda: self.api_rate(query_dict(self.path)),
            "/api/export": lambda: self.api_export(query_dict(self.path)),
            "/api/health": self.api_health,
        }
        if parsed.path in routes:
            try:
                routes[parsed.path]()
            except Exception as exc:
                json_response(self, {"error": "Внутренняя ошибка сервера."}, 500)
                print(f"Unhandled GET error: {exc}")
            return
        if parsed.path.startswith("/static/"):
            self.serve_static(parsed.path)
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        if self.path == "/api/expenses":
            self.create_expense()
            return
        self.send_error(404, "Not found")

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/expenses/"):
            try:
                expense_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                json_response(self, {"error": "Некорректный идентификатор."}, 400)
                return
            self.update_expense(expense_id)
            return
        if parsed.path == "/api/settings":
            self.update_settings()
            return
        self.send_error(404, "Not found")

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/settings/budget":
            self.delete_budget(query_dict(self.path))
            return
        if not parsed.path.startswith("/api/expenses/"):
            self.send_error(404, "Not found")
            return
        try:
            expense_id = int(parsed.path.rsplit("/", 1)[-1])
        except ValueError:
            json_response(self, {"error": "Некорректный идентификатор."}, 400)
            return
        self.delete_expense(expense_id)

    def api_health(self) -> None:
        json_response(self, {"status": "ok", "service": "Expense Tracker", "version": "7.0"})

    def delete_budget(self, params: dict[str, str]) -> None:
        try:
            year, month = self.parse_period(params)
            settings = STORAGE.settings()
            period_key = f"{year:04d}-{month:02d}"
            settings.get("budgets", {}).pop(period_key, None)
            STORAGE.save_settings(settings)
            json_response(self, {"success": True, "year": year, "month": month})
        except ValueError as exc:
            json_response(self, {"error": str(exc)}, 400)

    def serve_index(self) -> None:
        template = HTML_FILE.read_text(encoding="utf-8")
        category_options = "".join(
            f'<option value="{escape_html(category)}">{escape_html(category)}</option>'
            for category in DEFAULT_CATEGORIES
        )
        currency_options = "".join(
            f'<option value="{currency}">{currency}</option>'
            for currency in SUPPORTED_CURRENCIES
        )
        html = template.replace("__CATEGORY_OPTIONS__", category_options)
        html = html.replace("__CURRENCY_OPTIONS__", currency_options)
        text_response(self, html, "text/html; charset=utf-8")

    def serve_static(self, path: str) -> None:
        relative = path.removeprefix("/static/")
        file_path = (STATIC_DIR / relative).resolve()
        root = STATIC_DIR.resolve()
        if root not in file_path.parents or not file_path.is_file():
            self.send_error(404, "Not found")
            return
        content_types = {
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }
        text_response(self, file_path.read_text(encoding="utf-8"), content_types.get(file_path.suffix, "text/plain; charset=utf-8"))

    def parse_period(self, params: dict[str, str]) -> tuple[int, int]:
        today = date.today()
        try:
            year = int(params.get("year", today.year))
            month = int(params.get("month", today.month))
            if year < 2000 or year > 2100 or not 1 <= month <= 12:
                raise ValueError
            return year, month
        except ValueError as exc:
            raise ValueError("Некорректный период.") from exc

    def api_data(self, params: dict[str, str]) -> None:
        try:
            year, month = self.parse_period(params)
            expense_objects = EXPENSE_SERVICE.list_all()
            filtered = EXPENSE_SERVICE.list_month(year, month, params)
            analysis = analyze_expenses(expense_objects, year, month)
            comparison = compare_with_previous_month(expense_objects, year, month)
            settings = STORAGE.settings()
            period_key = f"{year:04d}-{month:02d}"
            budgets = settings.get("budgets", {})
            configured_budget = budgets.get(period_key, 0)
            budget = currency_decimal(configured_budget)
            payload = {
                "expenses": [item.to_dict() for item in filtered],
                "analysis": analysis,
                "comparison": comparison,
                "budget": budget_info(analysis, budget, year, month),
                "settings": settings,
                "categories": DEFAULT_CATEGORIES,
                "currencies": SUPPORTED_CURRENCIES,
            }
            json_response(self, payload)
        except ValueError as exc:
            json_response(self, {"error": str(exc)}, 400)

    def create_expense(self) -> None:
        try:
            expense = EXPENSE_SERVICE.add(read_request_json(self))
            json_response(self, expense.to_dict(), 201)
        except (ValueError, APIError) as exc:
            json_response(self, {"error": str(exc)}, 400)

    def update_expense(self, expense_id: int) -> None:
        try:
            expense = EXPENSE_SERVICE.update(expense_id, read_request_json(self))
            json_response(self, expense.to_dict())
        except LookupError as exc:
            json_response(self, {"error": str(exc)}, 404)
        except (ValueError, APIError) as exc:
            json_response(self, {"error": str(exc)}, 400)

    def delete_expense(self, expense_id: int) -> None:
        try:
            EXPENSE_SERVICE.delete(expense_id)
            json_response(self, {"success": True})
        except LookupError as exc:
            json_response(self, {"error": str(exc)}, 404)

    def update_settings(self) -> None:
        try:
            payload = read_request_json(self)
            budget = currency_decimal(payload.get("monthly_budget", 0))
            year = int(payload.get("year"))
            month = int(payload.get("month"))
            if not 2000 <= year <= 2100 or not 1 <= month <= 12:
                raise ValueError("Некорректный период.")
            if budget < 0:
                raise ValueError("Бюджет не может быть отрицательным.")
            settings = STORAGE.settings()
            settings["base_currency"] = "RUB"
            settings.setdefault("budgets", {})
            period_key = f"{year:04d}-{month:02d}"
            settings["budgets"][period_key] = float(budget)
            STORAGE.save_settings(settings)
            json_response(self, {"year": year, "month": month, "monthly_budget": float(budget)})
        except (ValueError, ArithmeticError) as exc:
            json_response(self, {"error": "Некорректный бюджет."}, 400)

    def api_rate(self, params: dict[str, str]) -> None:
        from_currency = params.get("from", "RUB").upper()
        to_currency = params.get("to", "RUB").upper()
        target_date = params.get("date") or date.today().isoformat()
        try:
            rate, source, rate_date = CURRENCY_SERVICE.get_rate(from_currency, to_currency, target_date)
            json_response(self, {"from": from_currency, "to": to_currency, "rate": float(rate), "date": rate_date, "source": source})
        except APIError as exc:
            json_response(self, {"error": str(exc)}, 503)

    def api_export(self, params: dict[str, str]) -> None:
        try:
            year, month = self.parse_period(params)
            expenses = EXPENSE_SERVICE.list_month(year, month, params)
            output = io.StringIO()
            writer = csv.writer(output, delimiter=";")
            writer.writerow(["Дата", "Категория", "Описание", "Сумма", "Валюта", "Сумма в RUB", "Курс", "Дата курса"])
            for expense in expenses:
                writer.writerow([
                    expense.date, expense.category, expense.description,
                    f"{expense.amount:.2f}", expense.currency,
                    f"{expense.base_amount:.2f}", f"{expense.exchange_rate:.6f}", expense.rate_date,
                ])
            data = output.getvalue().encode("utf-8-sig")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="expenses.csv"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except ValueError as exc:
            json_response(self, {"error": str(exc)}, 400)


def currency_decimal(value: Any):
    from decimal import Decimal, InvalidOperation
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError from exc


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), ExpenseTrackerHandler)
    print(f"Expense Tracker 7.0: http://{host}:{port}")
    print("Для остановки нажмите Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
