"""Read-only LAN dashboard for the bot's SQLite data."""

import calendar
import datetime as dt
import ipaddress
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from zoneinfo import ZoneInfo

from aiohttp import web


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATA_DIR", "/data")) / "botBD.db"
HOST = os.getenv("DASHBOARD_HOST", "192.168.1.10")
PORT = int(os.getenv("DASHBOARD_PORT", "3005"))
ALLOWED_NETWORK = ipaddress.ip_network(
    os.getenv("DASHBOARD_ALLOWED_CIDR", "192.168.1.0/24"), strict=False
)
KYIV = ZoneInfo("Europe/Kyiv")


@web.middleware
async def lan_only(request: web.Request, handler):
    try:
        address = ipaddress.ip_address(request.remote)
    except (TypeError, ValueError):
        raise web.HTTPForbidden()
    if address not in ALLOWED_NETWORK:
        raise web.HTTPForbidden()
    response = await handler(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
    return response


def load_statistics(year: int, month: int) -> dict:
    first = dt.date(year, month, 1)
    last = dt.date(year + (month == 12), month % 12 + 1, 1)
    start, end = first.isoformat(), last.isoformat()
    with closing(sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        revenue_rows = db.execute(
            """SELECT date, SUM(cashAM + cashPM) AS total
               FROM stat WHERE date >= ? AND date < ?
               GROUP BY date ORDER BY date""",
            (start, end),
        ).fetchall()
        expense_rows = db.execute(
            """SELECT date, SUM(cash) AS total
               FROM credet WHERE date >= ? AND date < ?
               GROUP BY date ORDER BY date""",
            (start, end),
        ).fetchall()
        year_start, year_end = f"{year}-01-01", f"{year + 1}-01-01"
        year_revenue = db.execute(
            """SELECT substr(date, 6, 2) AS month, SUM(cashAM + cashPM) AS total
               FROM stat WHERE date >= ? AND date < ?
               GROUP BY substr(date, 6, 2)""",
            (year_start, year_end),
        ).fetchall()
        year_expenses = db.execute(
            """SELECT substr(date, 6, 2) AS month, SUM(cash) AS total
               FROM credet WHERE date >= ? AND date < ?
               GROUP BY substr(date, 6, 2)""",
            (year_start, year_end),
        ).fetchall()
        recent = db.execute(
            """SELECT date, description, cash FROM credet
               WHERE date >= ? AND date < ?
               ORDER BY date DESC, id DESC LIMIT 6""",
            (start, end),
        ).fetchall()
        earliest = db.execute(
            """SELECT MIN(year) FROM (
                SELECT MIN(substr(date, 1, 4)) AS year FROM stat
                UNION ALL
                SELECT MIN(substr(date, 1, 4)) AS year FROM credet
            )"""
        ).fetchone()[0]

    revenue = {row["date"]: row["total"] or 0 for row in revenue_rows}
    expenses = {row["date"]: row["total"] or 0 for row in expense_rows}
    daily = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        date = dt.date(year, month, day).isoformat()
        earned, spent = revenue.get(date, 0), expenses.get(date, 0)
        daily.append(
            {"date": date, "day": day, "revenue": earned,
             "expenses": spent, "balance": earned - spent}
        )
    monthly_revenue = {int(row["month"]): row["total"] or 0 for row in year_revenue}
    monthly_expenses = {int(row["month"]): row["total"] or 0 for row in year_expenses}
    monthly = [
        {"month": value, "revenue": monthly_revenue.get(value, 0),
         "expenses": monthly_expenses.get(value, 0)}
        for value in range(1, 13)
    ]
    total_revenue = sum(revenue.values())
    total_expenses = sum(expenses.values())
    active_days = sum(day["revenue"] > 0 for day in daily)
    best_day = max(daily, key=lambda day: day["revenue"]) if active_days else None
    current_year = dt.datetime.now(KYIV).year
    return {
        "period": {"year": year, "month": month},
        "years": list(range(int(earliest or current_year), current_year + 1)),
        "summary": {
            "revenue": total_revenue,
            "expenses": total_expenses,
            "balance": total_revenue - total_expenses,
            "average": round(total_revenue / active_days) if active_days else 0,
            "active_days": active_days,
            "best_day": best_day["date"] if best_day else None,
        },
        "daily": daily,
        "monthly": monthly,
        "recent_expenses": [dict(row) for row in recent],
    }


async def home(request: web.Request):
    return web.FileResponse(BASE_DIR / "dashboard.html")


async def stylesheet(request: web.Request):
    return web.FileResponse(BASE_DIR / "dashboard.css")


async def script(request: web.Request):
    return web.FileResponse(BASE_DIR / "dashboard.js")


async def statistics(request: web.Request):
    today = dt.datetime.now(KYIV)
    try:
        year = int(request.query.get("year", today.year))
        month = int(request.query.get("month", today.month))
        if not 2000 <= year <= today.year or not 1 <= month <= 12:
            raise ValueError
    except ValueError:
        raise web.HTTPBadRequest(text="Invalid year or month")
    return web.json_response(load_statistics(year, month))


async def health(request: web.Request):
    return web.Response(text="ok" if DB_PATH.is_file() else "missing database",
                        status=200 if DB_PATH.is_file() else 503)


def main():
    host_address = ipaddress.ip_address(HOST)
    if not isinstance(host_address, ipaddress.IPv4Address) or host_address not in ALLOWED_NETWORK:
        raise ValueError("Dashboard host must be inside the allowed IPv4 LAN")
    if not DB_PATH.is_file():
        raise FileNotFoundError(DB_PATH)
    app = web.Application(middlewares=[lan_only])
    app.router.add_get("/", home)
    app.router.add_get("/dashboard.css", stylesheet)
    app.router.add_get("/dashboard.js", script)
    app.router.add_get("/api/stats", statistics)
    app.router.add_get("/health", health)
    web.run_app(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
