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


def revenue_reports(rows, today: dt.date, base_year: int, compare_year: int) -> dict:
    """Build revenue-only reports from daily rows (date, amount)."""
    revenue = {
        dt.date.fromisoformat(date): int(amount or 0)
        for date, amount in rows
    }
    first_record = min(revenue, default=today)
    years = []
    for year in range(first_record.year, today.year + 1):
        months = [0] * 12
        for date, amount in revenue.items():
            if date.year == year:
                months[date.month - 1] += amount
        full = first_record <= dt.date(year, 1, 1) and year < today.year
        years.append({
            "year": year,
            "total": sum(months),
            "season_total": sum(months[:4]) + sum(months[9:]),
            "offseason_total": sum(months[4:9]),
            "months": months,
            "status": "full" if full else ("current" if year == today.year else "initial"),
            "change": None,
            "percent": None,
        })
        if len(years) > 1 and full and years[-2]["status"] == "full":
            previous = years[-2]["total"]
            years[-1]["change"] = years[-1]["total"] - previous
            years[-1]["percent"] = round(
                (years[-1]["change"] / previous) * 100, 1
            ) if previous else None

    season_totals = {}
    for date, amount in revenue.items():
        if date.month >= 10:
            start_year, index = date.year, date.month - 10
        elif date.month <= 4:
            start_year, index = date.year - 1, date.month + 2
        else:
            continue
        season_totals.setdefault(start_year, [0] * 7)[index] += amount
    seasons = []
    for start_year, months in sorted(season_totals.items()):
        start = dt.date(start_year, 10, 1)
        end = dt.date(start_year + 1, 4, 30)
        full = first_record <= start and today > end
        season = {
            "start_year": start_year,
            "label": f"{start_year}/{str(start_year + 1)[-2:]}",
            "total": sum(months),
            "months": months,
            "status": "full" if full else ("current" if today <= end else "initial"),
            "change": None,
            "percent": None,
        }
        if (seasons and full and seasons[-1]["status"] == "full"
                and seasons[-1]["start_year"] == start_year - 1):
            previous = seasons[-1]["total"]
            season["change"] = season["total"] - previous
            season["percent"] = round(
                (season["change"] / previous) * 100, 1
            ) if previous else None
        seasons.append(season)

    offseasons = []
    for year in range(first_record.year, today.year + 1):
        start = dt.date(year, 5, 1)
        end = dt.date(year, 9, 30)
        if end < first_record or start > today:
            continue
        months = [0] * 5
        for date, amount in revenue.items():
            if date.year == year and 5 <= date.month <= 9:
                months[date.month - 5] += amount
        full = first_record <= start and today > end
        offseasons.append({
            "year": year,
            "total": sum(months),
            "months": months,
            "status": "full" if full else ("current" if today <= end else "initial"),
            "change": None,
            "percent": None,
        })
        if (len(offseasons) > 1 and full
                and offseasons[-2]["status"] == "full"
                and offseasons[-2]["year"] == year - 1):
            previous = offseasons[-2]["total"]
            offseasons[-1]["change"] = offseasons[-1]["total"] - previous
            offseasons[-1]["percent"] = round(
                offseasons[-1]["change"] / previous * 100, 1
            ) if previous else None

    if not first_record.year <= base_year <= today.year:
        raise ValueError("Invalid base year")
    if not first_record.year <= compare_year <= today.year or base_year == compare_year:
        raise ValueError("Invalid comparison year")
    start_month, start_day = (
        (first_record.month, first_record.day)
        if first_record.year in (base_year, compare_year) else (1, 1)
    )
    end_month, end_day = (
        (today.month, today.day)
        if today.year in (base_year, compare_year) else (12, 31)
    )
    available = (start_month, start_day) <= (end_month, end_day)
    if available:
        # Use the same calendar day in both years, including around leap years.
        start_day = min(start_day, *(calendar.monthrange(y, start_month)[1]
                                     for y in (base_year, compare_year)))
        end_day = min(end_day, *(calendar.monthrange(y, end_month)[1]
                                 for y in (base_year, compare_year)))
    comparison_months = []
    totals = {base_year: 0, compare_year: 0}
    for month in range(1, 13):
        item = {"month": month, "base": 0, "compare": 0}
        if available:
            for year, key in ((base_year, "base"), (compare_year, "compare")):
                start = dt.date(year, start_month, start_day)
                end = dt.date(year, end_month, end_day)
                item[key] = sum(
                    amount for date, amount in revenue.items()
                    if date.year == year and date.month == month and start <= date <= end
                )
                totals[year] += item[key]
        comparison_months.append(item)
    base_total, compare_total = totals[base_year], totals[compare_year]
    change = compare_total - base_total if available else None
    percent = round(change / base_total * 100, 1) if available and base_total else None
    return {
        "as_of": today.isoformat(),
        "first_record": first_record.isoformat(),
        "seasons": seasons,
        "offseasons": offseasons,
        "years": years,
        "comparison": {
            "base_year": base_year,
            "compare_year": compare_year,
            "available": available,
            "base_total": base_total,
            "compare_total": compare_total,
            "change": change,
            "percent": percent,
            "window": {
                "start_month": start_month,
                "start_day": start_day,
                "end_month": end_month,
                "end_day": end_day,
            },
            "months": comparison_months,
        },
    }


def load_reports(base_year: int, compare_year: int) -> dict:
    with closing(sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        rows = db.execute(
            """SELECT date, SUM(cashAM + cashPM)
               FROM stat GROUP BY date ORDER BY date"""
        ).fetchall()
    return revenue_reports(rows, dt.datetime.now(KYIV).date(), base_year, compare_year)


async def home(request: web.Request):
    return web.FileResponse(BASE_DIR / "dashboard.html")


async def stylesheet(request: web.Request):
    return web.FileResponse(BASE_DIR / "dashboard.css")


async def script(request: web.Request):
    return web.FileResponse(BASE_DIR / "dashboard.js")


async def reports_page(request: web.Request):
    return web.FileResponse(BASE_DIR / "reports.html")


async def reports_stylesheet(request: web.Request):
    return web.FileResponse(BASE_DIR / "reports.css")


async def reports_script(request: web.Request):
    return web.FileResponse(BASE_DIR / "reports.js")


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


async def reports_data(request: web.Request):
    today = dt.datetime.now(KYIV).date()
    try:
        base_year = int(request.query.get("base", today.year - 1))
        compare_year = int(request.query.get("compare", today.year))
        data = load_reports(base_year, compare_year)
    except ValueError:
        raise web.HTTPBadRequest(text="Invalid year selection")
    return web.json_response(data)


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
    app.router.add_get("/reports", reports_page)
    app.router.add_get("/reports.css", reports_stylesheet)
    app.router.add_get("/reports.js", reports_script)
    app.router.add_get("/api/stats", statistics)
    app.router.add_get("/api/reports", reports_data)
    app.router.add_get("/health", health)
    web.run_app(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
