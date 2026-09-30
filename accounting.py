"""Shared revenue rule for the bot and dashboard.

The stored AM and PM amounts are turnover. Revenue is exactly half of it.
"""

import datetime as dt


def revenue_from_turnover(turnover: int | float) -> float:
    return turnover / 2


def covered_months(year: int, first_record: dt.date, as_of: dt.date) -> int:
    """Count calendar months with available history, including months without sales."""
    start = max(dt.date(year, 1, 1), first_record)
    end = min(dt.date(year, 12, 31), as_of)
    return end.month - start.month + 1 if start <= end else 0


def format_amount(amount: int | float) -> str:
    """Show hryvnias without losing a possible 50-kopiyka fraction."""
    return f"{amount:,.2f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")
