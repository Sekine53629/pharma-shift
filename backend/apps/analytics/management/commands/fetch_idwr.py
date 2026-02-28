"""Fetch IDWR (Infectious Disease Weekly Report) data from JIHS/NIID.

Downloads sentinel surveillance CSV data (定点把握疾患) and stores
per-sentinel counts for Hokkaido prefecture.

CSV format (Shift-JIS encoded, wide format):
    Row 0: Title
    Row 1: Week/date info
    Row 2: Disease name (e.g., "インフルエンザ")
    Row 3: Week number headers (総数, 01週, 02週, ...)
    Row 4: Sub-headers (報告, 定当, 報告, 定当, ...)
    Row 5: 総数 (national total)
    Row 6: 北海道
    ...

    Columns: [prefecture, cumulative_reports, cumulative_per_sentinel,
              week1_reports, week1_per_sentinel, week2_reports, ...]

URL pattern (current, JIHS):
    https://id-info.jihs.go.jp/surveillance/idwr/rapid/
    {YEAR}/{WEEK}/{YEAR}-{WEEK:02d}-teiten-tougai.csv

Usage:
    python manage.py fetch_idwr                            # Fetch latest week
    python manage.py fetch_idwr --year 2024 --weeks 1-52   # Full year
    python manage.py fetch_idwr --year 2024 --weeks 40     # Single week
"""

import csv
import io
import logging
import time
from datetime import date

import requests
from django.core.management.base import BaseCommand

from apps.analytics.models import InfluenzaReport

logger = logging.getLogger(__name__)

# URL templates in priority order (try JIHS first, then NIID legacy)
IDWR_URL_TEMPLATES = [
    (
        "https://id-info.jihs.go.jp/surveillance/idwr/rapid/"
        "{year}/{week}/{year}-{week:02d}-teiten-tougai.csv"
    ),
    (
        "https://id-info.jihs.go.jp/surveillance/idwr/provisional/"
        "{year}/{week}/{year}-{week:02d}-teiten-tougai.csv"
    ),
]

# Target diseases relevant to prescription prediction
TARGET_DISEASES = [
    "インフルエンザ",
    "RSウイルス感染症",
    "咽頭結膜熱",
    "A群溶血性レンサ球菌咽頭炎",
    "感染性胃腸炎",
    "手足口病",
    "新型コロナウイルス感染症",
]


def _current_epi_week() -> tuple[int, int]:
    """Return the current epidemiological (year, week)."""
    today = date.today()
    iso = today.isocalendar()
    return iso[0], iso[1]


class Command(BaseCommand):
    help = "Fetch IDWR sentinel surveillance data and store reports for Hokkaido"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, default=None,
            help="Start year (default: current year)",
        )
        parser.add_argument(
            "--weeks", type=str, default=None,
            help="Week range, e.g. '1-52' or '40' (default: last 4 weeks)",
        )
        parser.add_argument(
            "--year-end", type=int, default=None,
            help="End year for multi-year fetch",
        )
        parser.add_argument(
            "--week-end", type=int, default=None,
            help="End week (used with --year-end)",
        )
        parser.add_argument(
            "--all-diseases", action="store_true",
            help="Fetch all diseases, not just target list",
        )
        parser.add_argument(
            "--delay", type=float, default=1.5,
            help="Delay between requests in seconds (default: 1.5)",
        )

    def handle(self, *args, **options):
        current_year, current_week = _current_epi_week()
        year = options["year"] or current_year

        if options["weeks"]:
            parts = options["weeks"].split("-")
            week_start = int(parts[0])
            week_end = int(parts[1]) if len(parts) > 1 else week_start
        else:
            week_start = max(current_week - 4, 1)
            week_end = current_week - 1

        year_end = options["year_end"] or year
        if options["week_end"]:
            week_end = options["week_end"]

        all_diseases = options["all_diseases"]
        delay = options["delay"]

        total_created = 0
        total_updated = 0
        total_errors = 0

        fetch_list = []
        y, w = year, week_start
        while y < year_end or (y == year_end and w <= week_end):
            fetch_list.append((y, w))
            w += 1
            if w > 53:
                w = 1
                y += 1

        self.stdout.write(
            f"Fetching IDWR data: {len(fetch_list)} weeks "
            f"from {year}W{week_start:02d} to {year_end}W{week_end:02d}"
        )

        for y, w in fetch_list:
            created, updated, errors = self._fetch_week(y, w, all_diseases)
            total_created += created
            total_updated += updated
            total_errors += errors

            if delay > 0 and (y, w) != fetch_list[-1]:
                time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {total_created} created, {total_updated} updated, "
                f"{total_errors} errors"
            )
        )

    def _download_csv(self, year: int, week: int) -> str | None:
        """Try downloading CSV from multiple URL patterns."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; pharma-shift-idwr/1.0)",
        }
        for template in IDWR_URL_TEMPLATES:
            url = template.format(year=year, week=week)
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code == 200 and len(resp.content) > 100:
                    self.stdout.write(f"  OK: {url}")
                    return resp.content.decode("shift_jis", errors="replace")
            except requests.RequestException:
                continue
        return None

    def _fetch_week(
        self, year: int, week: int, all_diseases: bool
    ) -> tuple[int, int, int]:
        """Fetch and parse one week of IDWR data."""
        self.stdout.write(f"  Fetching {year}W{week:02d}...")

        content = self._download_csv(year, week)
        if content is None:
            self.stderr.write(
                self.style.WARNING(f"  Could not download {year}W{week:02d}")
            )
            return 0, 0, 1

        created = 0
        updated = 0

        try:
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)

            # Parse the wide-format IDWR CSV
            # Structure: multiple disease sections, each with:
            #   disease_name row
            #   week-number header row
            #   sub-header row (報告/定当)
            #   data rows (総数, then prefectures)
            current_disease = None
            target_week_col_report = None
            target_week_col_sentinel = None
            in_data_section = False

            for row_idx, row in enumerate(rows):
                if not row:
                    continue

                first_cell = row[0].strip()

                # Detect disease name row: non-empty first cell, rest mostly empty
                non_empty = sum(1 for c in row[1:] if c.strip())
                if first_cell and non_empty < 3 and first_cell not in ("総数",):
                    # Skip title/date rows
                    if "報告数" in first_cell or "年" in first_cell:
                        continue
                    # Check if this is a known disease name
                    if all_diseases or first_cell in TARGET_DISEASES:
                        current_disease = first_cell
                        in_data_section = False
                        target_week_col_report = None
                        target_week_col_sentinel = None
                    else:
                        current_disease = None
                    continue

                if current_disease is None:
                    continue

                # Detect week number header row (contains "01週", "02週", etc.)
                if any(f"{week:02d}週" in c for c in row):
                    # Find the column index for the target week
                    for col_idx, cell in enumerate(row):
                        if f"{week:02d}週" in cell.strip():
                            # IDWR uses paired columns: report, per_sentinel
                            target_week_col_report = col_idx
                            break
                    continue

                # Detect sub-header row (報告/定当)
                if target_week_col_report and any("定当" in c or "定点" in c for c in row):
                    # Verify: the target column should be 報告, next is 定当
                    if target_week_col_report < len(row):
                        sub = row[target_week_col_report].strip()
                        if sub == "報告":
                            target_week_col_sentinel = target_week_col_report + 1
                        elif "定" in sub:
                            target_week_col_sentinel = target_week_col_report
                            target_week_col_report = target_week_col_report - 1
                    in_data_section = True
                    continue

                # Parse data rows
                if in_data_section and first_cell:
                    # We only care about 北海道
                    if first_cell != "北海道":
                        continue

                    per_sentinel = None
                    total_reports = None

                    if target_week_col_report and target_week_col_report < len(row):
                        val = row[target_week_col_report].strip().replace(",", "")
                        if val and val not in ("-", "…", ""):
                            try:
                                total_reports = int(val)
                            except ValueError:
                                pass

                    if target_week_col_sentinel and target_week_col_sentinel < len(row):
                        val = row[target_week_col_sentinel].strip().replace(",", "")
                        if val and val not in ("-", "…", ""):
                            try:
                                per_sentinel = float(val)
                            except ValueError:
                                pass

                    if per_sentinel is not None or total_reports is not None:
                        _, was_created = InfluenzaReport.objects.update_or_create(
                            year=year,
                            week=week,
                            prefecture="北海道",
                            disease=current_disease,
                            defaults={
                                "patients": per_sentinel,
                                "total_reports": total_reports,
                            },
                        )
                        if was_created:
                            created += 1
                        else:
                            updated += 1

                    # Reset for next disease section
                    current_disease = None
                    in_data_section = False

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"  Parse error for {year}W{week:02d}: {e}")
            )
            return created, updated, 1

        self.stdout.write(f"    → {created} created, {updated} updated")
        return created, updated, 0
