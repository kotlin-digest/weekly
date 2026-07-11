from datetime import date, timedelta


def edition_to_dates(edition: str) -> tuple:
    """'2026-W28' → (date(2026-07-06), date(2026-07-12))"""
    year, week = edition.split("-W")
    monday = date.fromisocalendar(int(year), int(week), 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday
