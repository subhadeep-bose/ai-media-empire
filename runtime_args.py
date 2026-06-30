"""
Shared --date CLI override, used by every squad script + chief_of_staff so a
single failed stage can be retried against a specific day's date_str instead
of always defaulting to today (see manual_retry.yml). Squad scripts that
scrape live sources still fetch current data regardless of --date — this only
controls which date_str the run's output is filed/labelled under.
"""

import argparse
from datetime import datetime


def get_date_str() -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD override; defaults to today")
    args, _ = parser.parse_known_args()

    if args.date:
        datetime.strptime(args.date, "%Y-%m-%d")  # raises ValueError if malformed
        return args.date
    return datetime.now().strftime("%Y-%m-%d")
