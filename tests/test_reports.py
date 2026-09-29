import datetime as dt
import unittest

from dashboard import revenue_reports


ROWS = [
    ("2022-10-11", 100),
    ("2023-04-30", 200),
    ("2023-05-01", 900),
    ("2023-10-01", 300),
    ("2024-04-30", 200),
    ("2024-10-01", 1000),
    ("2025-04-30", 500),
    ("2025-09-29", 200),
    ("2025-10-01", 250),
    ("2026-04-30", 250),
    ("2026-09-29", 300),
]
TODAY = dt.date(2026, 9, 29)


class RevenueReportTests(unittest.TestCase):
    def test_season_crosses_year_and_excludes_summer(self):
        seasons = revenue_reports(ROWS, TODAY, 2025, 2026)["seasons"]
        self.assertEqual(
            [(item["label"], item["total"], item["status"]) for item in seasons],
            [
                ("2022/23", 300, "initial"),
                ("2023/24", 500, "full"),
                ("2024/25", 1500, "full"),
                ("2025/26", 500, "full"),
            ],
        )
        self.assertIsNone(seasons[1]["percent"])
        self.assertEqual(seasons[2]["percent"], 200.0)

    def test_current_year_uses_same_end_date_in_both_years(self):
        report = revenue_reports(ROWS, TODAY, 2025, 2026)
        years = report["years"]
        self.assertEqual(years[0]["status"], "initial")
        self.assertEqual(years[-1]["status"], "current")
        self.assertIsNone(years[-1]["percent"])
        comparison = report["comparison"]
        self.assertEqual(comparison["base_total"], 700)
        self.assertEqual(comparison["compare_total"], 550)
        self.assertEqual(comparison["window"]["end_month"], 9)
        self.assertEqual(comparison["window"]["end_day"], 29)
        self.assertEqual(comparison["percent"], -21.4)

    def test_first_partial_year_only_compares_covered_dates(self):
        comparison = revenue_reports(ROWS, TODAY, 2022, 2023)["comparison"]
        self.assertTrue(comparison["available"])
        self.assertEqual(comparison["window"]["start_month"], 10)
        self.assertEqual(comparison["window"]["start_day"], 11)
        self.assertEqual(comparison["base_total"], 100)
        self.assertEqual(comparison["compare_total"], 0)
        self.assertFalse(
            revenue_reports(ROWS, TODAY, 2022, 2026)["comparison"]["available"]
        )


if __name__ == "__main__":
    unittest.main()
