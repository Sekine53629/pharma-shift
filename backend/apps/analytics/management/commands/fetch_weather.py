"""Fetch historical weather data from JMA (気象庁).

Scrapes daily weather observations for Hokkaido stations from the JMA
past weather data download service.

Supports both 官署 (main observatories, daily_s1.php) and
AMeDAS (automated stations, daily_a1.php) URL patterns.

Usage:
    python manage.py fetch_weather                          # Fetch last 30 days
    python manage.py fetch_weather --start 2024-01-01 --end 2024-12-31
    python manage.py fetch_weather --station 旭川 --start 2024-06-01
"""

import logging
import re
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.core.management.base import BaseCommand

from apps.analytics.models import AREA_STATION_MAP, WeatherRecord, is_amedas

logger = logging.getLogger(__name__)

# Deduplicated JMA stations from AREA_STATION_MAP
# {station_name: (prec_no, block_no)}
JMA_STATIONS = {
    name: (prec_no, block_no)
    for _, (name, prec_no, block_no) in AREA_STATION_MAP.items()
}

# JMA URL patterns
JMA_DAILY_S1 = "https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php"  # 官署
JMA_DAILY_A1 = "https://www.data.jma.go.jp/obd/stats/etrn/view/daily_a1.php"  # AMeDAS

# Column index maps for parsing JMA HTML tables.
# 官署 (daily_s1) has more columns than AMeDAS (daily_a1).
# Indices are 0-based within the <td> list (column 0 = day number).
#
# daily_s1 typical layout (per JMA):
#   0:day, 1:precip_total, 2:precip_max1h, 3:precip_max10m,
#   4:avg_temp, 5:max_temp, 6:min_temp,
#   7:avg_humidity, 8:min_humidity,
#   9:avg_wind, 10:max_wind, 11:max_wind_dir, 12:max_gust, 13:max_gust_dir,
#   14:sunshine, 15:snowfall, 16:snow_depth, ...
#
# daily_a1 typical layout (per JMA):
#   0:day, 1:precip_total, 2:precip_max1h, 3:precip_max10m,
#   4:avg_temp, 5:max_temp, 6:min_temp,
#   7:avg_humidity, 8:min_humidity,
#   9:avg_wind, 10:max_wind, 11:max_wind_dir, 12:max_gust, 13:max_gust_dir,
#   14:sunshine, 15:snowfall, 16:snow_depth
COLUMN_MAP_S1 = {
    "avg_temp": 4, "max_temp": 5, "min_temp": 6,
    "precip": 1, "humidity": 7,
    "snowfall": 15, "snow_depth": 16,
}
COLUMN_MAP_A1 = {
    "avg_temp": 4, "max_temp": 5, "min_temp": 6,
    "precip": 1, "humidity": 7,
    "snowfall": 15, "snow_depth": 16,
}

_TD_PATTERN = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
_TAG_STRIP = re.compile(r"<[^>]+>")


def _parse_decimal(value: str) -> Decimal | None:
    """Parse a decimal value from JMA HTML, handling special markers."""
    if not value:
        return None
    # JMA uses special markers: ), ], *, #, -- for various data quality flags
    cleaned = value.strip().rstrip(")]*#").replace("--", "").replace("///", "")
    # Also strip × (missing data marker) and whitespace
    cleaned = cleaned.replace("×", "").replace("\xa0", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


class Command(BaseCommand):
    help = "Fetch daily weather data from JMA for Hokkaido stations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--start", type=str, default=None,
            help="Start date (YYYY-MM-DD). Default: 30 days ago",
        )
        parser.add_argument(
            "--end", type=str, default=None,
            help="End date (YYYY-MM-DD). Default: yesterday",
        )
        parser.add_argument(
            "--station", type=str, default=None,
            help="Station name to fetch (e.g., 旭川). Default: all stations",
        )
        parser.add_argument(
            "--delay", type=float, default=3.0,
            help="Delay between requests in seconds (default: 3.0)",
        )

    def handle(self, *args, **options):
        yesterday = date.today() - timedelta(days=1)

        if options["start"]:
            start_date = date.fromisoformat(options["start"])
        else:
            start_date = yesterday - timedelta(days=30)

        if options["end"]:
            end_date = date.fromisoformat(options["end"])
        else:
            end_date = yesterday

        # Determine which stations to fetch
        if options["station"]:
            station_name = options["station"]
            if station_name not in JMA_STATIONS:
                self.stderr.write(
                    self.style.ERROR(
                        f"Unknown station: {station_name}. "
                        f"Available: {', '.join(JMA_STATIONS.keys())}"
                    )
                )
                return
            stations = {station_name: JMA_STATIONS[station_name]}
        else:
            stations = JMA_STATIONS

        delay = options["delay"]

        self.stdout.write(
            f"Fetching weather data: {len(stations)} stations, "
            f"{start_date} to {end_date}"
        )

        total_created = 0
        total_updated = 0
        total_errors = 0

        station_list = list(stations.items())
        for idx, (name, (prec_no, block_no)) in enumerate(station_list):
            station_type = "AMeDAS" if is_amedas(block_no) else "官署"
            self.stdout.write(
                f"  [{idx + 1}/{len(station_list)}] {name} "
                f"(prec={prec_no}, block={block_no}, {station_type})"
            )

            created, updated, errors = self._fetch_station(
                name, prec_no, block_no, start_date, end_date
            )
            total_created += created
            total_updated += updated
            total_errors += errors

            if delay > 0 and idx < len(station_list) - 1:
                time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {total_created} created, {total_updated} updated, "
                f"{total_errors} errors"
            )
        )

    def _fetch_station(
        self,
        station_name: str,
        prec_no: str,
        block_no: str,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int, int]:
        """Fetch weather data for one station month by month.

        Returns (created, updated, errors).
        """
        created = 0
        updated = 0
        errors = 0

        # Select URL pattern based on station type
        base_url = JMA_DAILY_A1 if is_amedas(block_no) else JMA_DAILY_S1
        col_map = COLUMN_MAP_A1 if is_amedas(block_no) else COLUMN_MAP_S1

        # Process month by month
        current = start_date.replace(day=1)
        while current <= end_date:
            month_end = (
                (current.replace(day=28) + timedelta(days=4)).replace(day=1)
                - timedelta(days=1)
            )
            if month_end > end_date:
                month_end = end_date

            url = (
                f"{base_url}"
                f"?prec_no={prec_no}&block_no={block_no}"
                f"&year={current.year}&month={current.month}"
            )

            try:
                resp = requests.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; pharma-shift/1.0)",
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    c, u = self._parse_daily_html(
                        resp.text, station_name, block_no,
                        current.year, current.month,
                        col_map, start_date, end_date,
                    )
                    created += c
                    updated += u
                    self.stdout.write(
                        f"    {current.year}-{current.month:02d}: "
                        f"{c} created, {u} updated"
                    )
                else:
                    self.stderr.write(
                        self.style.WARNING(
                            f"    {current.year}-{current.month:02d}: "
                            f"HTTP {resp.status_code}"
                        )
                    )
                    errors += 1
            except requests.RequestException as e:
                self.stderr.write(
                    self.style.WARNING(
                        f"    {current.year}-{current.month:02d}: {e}"
                    )
                )
                errors += 1

            # Move to next month
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
            time.sleep(2)

        return created, updated, errors

    def _parse_daily_html(
        self,
        html: str,
        station_name: str,
        block_no: str,
        year: int,
        month: int,
        col_map: dict,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        """Parse JMA daily HTML table and extract weather data.

        Works for both daily_s1 (官署) and daily_a1 (AMeDAS) pages.
        Uses col_map to locate columns by station type.
        """
        created = 0
        updated = 0

        try:
            rows = html.split("<tr")
            for row_html in rows:
                tds = _TD_PATTERN.findall(row_html)
                if len(tds) < 5:
                    continue

                # First column should be the day number
                day_text = _TAG_STRIP.sub("", tds[0]).strip()
                try:
                    day = int(day_text)
                    if day < 1 or day > 31:
                        continue
                except ValueError:
                    continue

                try:
                    record_date = date(year, month, day)
                except ValueError:
                    continue

                # Skip dates outside the requested range
                if record_date < start_date or record_date > end_date:
                    continue

                def clean_val(idx):
                    if idx >= len(tds):
                        return None
                    val = _TAG_STRIP.sub("", tds[idx]).strip()
                    return _parse_decimal(val)

                avg_temp = clean_val(col_map["avg_temp"])
                max_temp = clean_val(col_map["max_temp"])
                min_temp = clean_val(col_map["min_temp"])
                precip = clean_val(col_map["precip"])
                humid = clean_val(col_map["humidity"])
                snowfall = clean_val(col_map.get("snowfall", 99))
                snow_depth = clean_val(col_map.get("snow_depth", 99))

                if avg_temp is not None:
                    _, was_created = WeatherRecord.objects.update_or_create(
                        station_name=station_name,
                        date=record_date,
                        defaults={
                            "station_code": block_no,
                            "avg_temperature": avg_temp,
                            "max_temperature": max_temp,
                            "min_temperature": min_temp,
                            "precipitation": precip,
                            "humidity": humid,
                            "snowfall": snowfall,
                            "snow_depth": snow_depth,
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

        except Exception as e:
            logger.warning("Failed to parse JMA daily HTML for %s: %s", station_name, e)

        return created, updated
