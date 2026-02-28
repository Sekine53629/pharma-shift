"""Fetch historical weather data from JMA (気象庁).

Scrapes daily weather observations for Hokkaido stations from the JMA
past weather data download service.

JMA download endpoint:
    https://www.data.jma.go.jp/gmd/risk/obsdl/show/table

Usage:
    python manage.py fetch_weather                          # Fetch last 30 days
    python manage.py fetch_weather --start 2024-01-01 --end 2024-12-31
    python manage.py fetch_weather --station 旭川 --start 2024-06-01
"""

import csv
import io
import logging
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.core.management.base import BaseCommand

from apps.analytics.models import AREA_STATION_MAP, WeatherRecord

logger = logging.getLogger(__name__)

# JMA station config: (station_name, prec_no, block_no)
JMA_STATIONS = {
    name: (prec_no, block_no)
    for _, (name, prec_no, block_no) in AREA_STATION_MAP.items()
}

# JMA data download endpoint
JMA_URL = "https://www.data.jma.go.jp/gmd/risk/obsdl/show/table"


def _parse_decimal(value: str) -> Decimal | None:
    """Parse a decimal value from JMA CSV, handling special markers."""
    if not value:
        return None
    # JMA uses special markers: ), ], *, #, -- for various data quality flags
    cleaned = value.strip().rstrip(")]*#").replace("--", "").replace("///", "")
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
        """Fetch weather data for one station. Returns (created, updated, errors)."""
        self.stdout.write(f"  Station: {station_name} (prec={prec_no}, block={block_no})")

        # JMA download form uses POST with specific parameters
        # Request daily data: avg temp, max temp, min temp, precipitation,
        # humidity, snowfall, snow depth
        params = {
            "prec_no": prec_no,
            "block_no": block_no,
            "year1": str(start_date.year),
            "month1": str(start_date.month),
            "day1": str(start_date.day),
            "year2": str(end_date.year),
            "month2": str(end_date.month),
            "day2": str(end_date.day),
            "view": "a1",  # Daily data
            "aggrgPeriod": "1",  # Daily
            "optionNum498": "1",  # avg temp
            "optionNumAvg498": "",
            "optionNumMax498": "",
            "optionNumMin498": "",
            "optionNumHigh499": "1",  # max temp
            "optionNumLow500": "1",  # min temp
            "optionNumPrec501": "1",  # precipitation
            "optionNumHum503": "1",  # humidity
            "optionNumSnow504": "1",  # snowfall
            "optionNumSnowDepth505": "1",  # snow depth
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; pharma-shift-weather-fetcher/1.0)",
            "Referer": "https://www.data.jma.go.jp/gmd/risk/obsdl/",
        }

        try:
            resp = requests.get(
                JMA_URL,
                params=params,
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(self.style.WARNING(f"  Failed: {e}"))
            return 0, 0, 1

        # Parse HTML table or CSV response
        # JMA returns HTML with a data table; we extract data from it
        created = 0
        updated = 0

        try:
            created, updated = self._parse_jma_html(
                resp.text, station_name, block_no
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  Parse error: {e}"))
            # Fallback: try to generate records from a simpler approach
            self.stdout.write("    Falling back to direct CSV approach...")
            created, updated = self._fetch_station_csv(
                station_name, prec_no, block_no, start_date, end_date
            )

        self.stdout.write(f"    → {created} created, {updated} updated")
        return created, updated, 0

    def _parse_jma_html(
        self, html: str, station_name: str, block_no: str
    ) -> tuple[int, int]:
        """Parse JMA HTML response and extract weather data."""
        # JMA returns data in a table format within HTML
        # We'll look for the CSV-formatted data section
        created = 0
        updated = 0

        # Try to find CSV data in the response
        # JMA sometimes includes a downloadable CSV section
        lines = html.split("\n")
        data_started = False
        header_found = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for date-formatted rows (YYYY/M/D or YYYY-MM-DD pattern)
            if "/" in line and any(c.isdigit() for c in line[:4]):
                parts = line.split(",")
                if len(parts) >= 3:
                    try:
                        date_str = parts[0].strip().strip('"')
                        # Parse date in various formats
                        if "/" in date_str:
                            date_parts = date_str.split("/")
                            if len(date_parts) == 3:
                                record_date = date(
                                    int(date_parts[0]),
                                    int(date_parts[1]),
                                    int(date_parts[2]),
                                )
                            else:
                                continue
                        else:
                            continue

                        # Extract values from columns
                        avg_temp = _parse_decimal(parts[1]) if len(parts) > 1 else None
                        max_temp = _parse_decimal(parts[2]) if len(parts) > 2 else None
                        min_temp = _parse_decimal(parts[3]) if len(parts) > 3 else None
                        precip = _parse_decimal(parts[4]) if len(parts) > 4 else None
                        humid = _parse_decimal(parts[5]) if len(parts) > 5 else None
                        snow = _parse_decimal(parts[6]) if len(parts) > 6 else None
                        snow_d = _parse_decimal(parts[7]) if len(parts) > 7 else None

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
                                "snowfall": snow,
                                "snow_depth": snow_d,
                            },
                        )
                        if was_created:
                            created += 1
                        else:
                            updated += 1
                    except (ValueError, IndexError):
                        continue

        return created, updated

    def _fetch_station_csv(
        self,
        station_name: str,
        prec_no: str,
        block_no: str,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        """Alternative CSV download approach for JMA data.

        Uses the direct download URL pattern which may work for some stations.
        """
        created = 0
        updated = 0

        # Process month by month to stay within JMA limits
        current = start_date.replace(day=1)
        while current <= end_date:
            month_end = (current.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            if month_end > end_date:
                month_end = end_date

            url = (
                f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php"
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
                        resp.text, station_name, block_no, current.year, current.month
                    )
                    created += c
                    updated += u
            except requests.RequestException:
                pass

            # Move to next month
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
            time.sleep(2)

        return created, updated

    def _parse_daily_html(
        self,
        html: str,
        station_name: str,
        block_no: str,
        year: int,
        month: int,
    ) -> tuple[int, int]:
        """Parse JMA daily HTML table and extract weather data.

        The HTML page contains a table with daily weather observations.
        We extract key columns: avg temp, max temp, min temp, precipitation,
        humidity, snowfall, snow depth.
        """
        created = 0
        updated = 0

        try:
            # Simple HTML table parser
            # Look for table rows with numeric data
            import re

            # Find all <tr> rows containing daily data
            # JMA daily pages have rows like: <td>1</td><td>value</td>...
            td_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)

            # Split by table rows
            rows = html.split("<tr")
            for row_html in rows:
                tds = td_pattern.findall(row_html)
                if len(tds) < 8:
                    continue

                # First column should be the day number
                day_text = re.sub(r"<[^>]+>", "", tds[0]).strip()
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

                # Extract values - column positions may vary by station type
                # Typical order: day, precip_total, precip_max_1h, precip_max_10m,
                #   avg_temp, max_temp, min_temp, avg_humidity, ...
                def clean_val(idx):
                    if idx >= len(tds):
                        return None
                    val = re.sub(r"<[^>]+>", "", tds[idx]).strip()
                    return _parse_decimal(val)

                # These column indices are approximate and may vary
                avg_temp = clean_val(4) or clean_val(6)
                max_temp = clean_val(5) or clean_val(7)
                min_temp = clean_val(6) or clean_val(8)
                precip = clean_val(1)
                humid = clean_val(9) or clean_val(11)

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
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

        except Exception as e:
            logger.warning("Failed to parse JMA daily HTML: %s", e)

        return created, updated
