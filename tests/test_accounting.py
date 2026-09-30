import sqlite3
import tempfile
import unittest
import datetime as dt
from contextlib import closing
from pathlib import Path

import dashboard
from accounting import covered_months, format_amount, revenue_from_turnover


class AccountingTests(unittest.TestCase):
    def test_turnover_is_halved_without_discarding_fraction(self):
        self.assertEqual(revenue_from_turnover(101), 50.5)
        self.assertEqual(format_amount(1234.5), "1 234,5")
        self.assertEqual(format_amount(100), "100")

    def test_partial_year_month_count_includes_months_without_sales(self):
        first = dt.date(2022, 10, 11)
        today = dt.date(2026, 9, 30)
        self.assertEqual(covered_months(2022, first, today), 3)
        self.assertEqual(covered_months(2023, first, today), 12)
        self.assertEqual(covered_months(2026, first, today), 9)

    def test_monthly_dashboard_uses_revenue_and_leaves_expenses_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "botBD.db"
            with closing(sqlite3.connect(path)) as db:
                db.executescript("""
                    CREATE TABLE stat (date TEXT, cashAM INTEGER, cashPM INTEGER);
                    CREATE TABLE credet (id INTEGER PRIMARY KEY, date TEXT,
                                         cash INTEGER, description TEXT);
                    INSERT INTO stat VALUES ('2025-01-01', 101, 0);
                    INSERT INTO stat VALUES ('2025-01-02', 1, 0);
                    INSERT INTO credet (date, cash, description)
                        VALUES ('2025-01-01', 10, 'test');
                """)
            original = dashboard.DB_PATH
            try:
                dashboard.DB_PATH = path
                data = dashboard.load_statistics(2025, 1)
            finally:
                dashboard.DB_PATH = original
        self.assertEqual(data["summary"]["revenue"], 51)
        self.assertEqual(data["summary"]["expenses"], 10)
        self.assertEqual(data["summary"]["balance"], 41)
        self.assertEqual(data["summary"]["average"], 4.25)
        self.assertEqual(data["summary"]["average_months"], 12)
        self.assertEqual(data["daily"][0]["revenue"], 50.5)
        self.assertEqual(data["monthly"][0]["revenue"], 51)


if __name__ == "__main__":
    unittest.main()
