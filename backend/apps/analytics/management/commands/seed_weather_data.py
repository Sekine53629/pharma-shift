"""Generate simulated weather data for development and testing.

Creates realistic daily weather records for all JMA stations mapped
to Hokkaido pharmacy areas.  Simulation uses sinusoidal annual curves
for temperature and seasonal snowfall patterns.

Usage:
    python manage.py seed_weather_data                          # 2024-01-01 ~ 2024-12-31
    python manage.py seed_weather_data --start 2024-06-01 --end 2024-12-31
    python manage.py seed_weather_data --reset                  # Delete existing + regenerate
"""

import math
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.analytics.models import AREA_STATION_MAP, WeatherRecord


# Station-level climate profiles (annual mean temp, winter low, summer high)
# Based loosely on real JMA normals for Hokkaido.
# Now includes 富良野 and 滝川 which have their own AMeDAS stations.
STATION_PROFILES = {
    "旭川":   {"mean_temp": 6.5, "amp": 16.0, "precip_base": 3.0, "snow_factor": 1.0},
    "名寄":   {"mean_temp": 5.5, "amp": 17.0, "precip_base": 2.5, "snow_factor": 1.2},
    "稚内":   {"mean_temp": 6.0, "amp": 13.0, "precip_base": 3.5, "snow_factor": 0.9},
    "留萌":   {"mean_temp": 7.0, "amp": 14.0, "precip_base": 3.2, "snow_factor": 1.1},
    "北見":   {"mean_temp": 5.8, "amp": 17.0, "precip_base": 2.2, "snow_factor": 0.8},
    "紋別":   {"mean_temp": 5.5, "amp": 15.0, "precip_base": 2.8, "snow_factor": 0.9},
    "富良野": {"mean_temp": 6.0, "amp": 17.0, "precip_base": 3.0, "snow_factor": 1.1},
    "滝川":   {"mean_temp": 6.8, "amp": 16.5, "precip_base": 3.0, "snow_factor": 1.0},
    "帯広":   {"mean_temp": 6.0, "amp": 17.5, "precip_base": 2.5, "snow_factor": 0.7},
    "釧路":   {"mean_temp": 5.5, "amp": 13.0, "precip_base": 3.0, "snow_factor": 0.5},
    "中標津": {"mean_temp": 4.5, "amp": 15.5, "precip_base": 2.8, "snow_factor": 0.6},
}


def _day_of_year_frac(d: date) -> float:
    """Day of year as fraction [0, 1)."""
    return (d.timetuple().tm_yday - 1) / 365.0


class Command(BaseCommand):
    help = "Generate simulated weather data for all AREA_STATION_MAP stations"

    def add_arguments(self, parser):
        parser.add_argument("--start", type=str, default="2024-01-01")
        parser.add_argument("--end", type=str, default="2024-12-31")
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        start = date.fromisoformat(options["start"])
        end = date.fromisoformat(options["end"])

        if options["reset"]:
            deleted, _ = WeatherRecord.objects.filter(
                date__gte=start, date__lte=end
            ).delete()
            self.stdout.write(f"Deleted {deleted} existing weather records")

        # Unique stations from AREA_STATION_MAP
        stations = {}
        for area_name, (station, prec, block) in AREA_STATION_MAP.items():
            if station not in stations:
                stations[station] = (prec, block)

        created = 0
        skipped = 0
        current = start

        while current <= end:
            doy_frac = _day_of_year_frac(current)

            for station_name, (prec_code, block_code) in stations.items():
                profile = STATION_PROFILES.get(
                    station_name,
                    {"mean_temp": 6.0, "amp": 15.0, "precip_base": 3.0, "snow_factor": 0.8},
                )

                # Temperature: sinusoidal annual cycle (min in late Jan, max in late Jul)
                # Phase shift: coldest ~Jan 25 -> day 25 -> frac=0.068
                temp_phase = 2 * math.pi * (doy_frac - 0.068)
                avg_temp = profile["mean_temp"] - profile["amp"] * math.cos(temp_phase)
                avg_temp += rng.gauss(0, 2.5)  # daily noise

                max_temp = avg_temp + rng.uniform(2.0, 6.0)
                min_temp = avg_temp - rng.uniform(2.0, 6.0)

                # Precipitation: random events, more frequent in summer & late autumn
                precip_season = 1.0 + 0.5 * math.sin(2 * math.pi * (doy_frac - 0.25))
                if rng.random() < 0.35 * precip_season:
                    precipitation = rng.expovariate(1 / (profile["precip_base"] * precip_season))
                else:
                    precipitation = 0.0

                # Humidity: higher in summer, lower in winter
                humidity = 65 + 15 * math.sin(2 * math.pi * (doy_frac - 0.25))
                humidity += rng.gauss(0, 5)
                humidity = max(30, min(100, humidity))

                # Snowfall: only in cold months (Nov-Mar roughly)
                snowfall = 0.0
                snow_depth = 0.0
                if avg_temp < 3.0:
                    snow_prob = min(0.6, max(0, (3.0 - avg_temp) / 10.0))
                    if rng.random() < snow_prob:
                        snowfall = rng.expovariate(1 / (5.0 * profile["snow_factor"]))
                    # Accumulated snow depth (simplified: proportional to how cold)
                    if avg_temp < 0:
                        snow_depth = max(0, (-avg_temp) * 3 * profile["snow_factor"]
                                         + rng.gauss(0, 5))

                _, is_created = WeatherRecord.objects.update_or_create(
                    station_name=station_name,
                    date=current,
                    defaults={
                        "station_code": block_code,
                        "avg_temperature": Decimal(str(round(avg_temp, 1))),
                        "max_temperature": Decimal(str(round(max_temp, 1))),
                        "min_temperature": Decimal(str(round(min_temp, 1))),
                        "precipitation": Decimal(str(round(max(precipitation, 0), 1))),
                        "humidity": Decimal(str(round(humidity, 1))),
                        "snowfall": Decimal(str(round(max(snowfall, 0), 1))),
                        "snow_depth": Decimal(str(round(max(snow_depth, 0), 1))),
                    },
                )
                if is_created:
                    created += 1
                else:
                    skipped += 1

            current += timedelta(days=1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Weather seed complete: {created} created, {skipped} updated "
                f"({len(stations)} stations × {(end - start).days + 1} days)"
            )
        )
