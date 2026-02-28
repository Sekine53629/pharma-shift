"""Generate sample prescription data for development and testing.

Creates realistic-looking daily prescription records for all 62 stores,
incorporating seasonal patterns (influenza season), day-of-week effects,
and random noise.

Usage:
    python manage.py seed_prescription_data                    # Last 180 days
    python manage.py seed_prescription_data --days 365         # Last year
    python manage.py seed_prescription_data --start 2024-01-01 --end 2024-12-31
    python manage.py seed_prescription_data --reset            # Delete existing + regenerate
"""

import math
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.analytics.models import PrescriptionRecord
from apps.stores.models import Store


# Base prescription count ranges by area (smaller areas tend to have fewer)
AREA_BASE_COUNTS = {
    "旭川": (40, 80),      # Urban, high volume
    "帯広": (35, 70),
    "釧路": (30, 65),
    "北見・網走": (25, 55),
    "名寄": (20, 45),
    "稚内": (20, 45),
    "富良野": (20, 40),
    "留萌": (15, 35),
    "紋別": (15, 35),
    "滝川・砂川": (25, 50),
    "中標津": (20, 40),
}


def _seasonal_factor(d: date) -> float:
    """Seasonal prescription volume multiplier.

    - Peak during flu season (Dec-Feb): 1.2-1.4x
    - Summer dip (Jul-Aug): 0.85x
    - Transitions in spring/autumn
    """
    day_of_year = d.timetuple().tm_yday
    # Sinusoidal pattern peaking in mid-January
    angle = 2 * math.pi * (day_of_year - 15) / 365
    return 1.0 + 0.2 * math.cos(angle)


def _day_of_week_factor(d: date) -> float:
    """Day-of-week prescription volume multiplier.

    Pharmacies are typically closed on Sundays and have
    reduced volume on Saturdays.
    """
    dow = d.weekday()  # 0=Mon, 6=Sun
    factors = {
        0: 1.1,   # Monday (post-weekend catchup)
        1: 1.0,   # Tuesday
        2: 1.0,   # Wednesday
        3: 1.0,   # Thursday
        4: 0.95,  # Friday
        5: 0.5,   # Saturday (half day)
        6: 0.0,   # Sunday (closed)
    }
    return factors[dow]


def _holiday_check(d: date) -> bool:
    """Simple check for major Japanese holidays and year-end closures."""
    # New Year (Dec 31 - Jan 3)
    if (d.month == 12 and d.day >= 31) or (d.month == 1 and d.day <= 3):
        return True
    # Golden Week (Apr 29, May 3-5)
    if (d.month == 4 and d.day == 29) or (d.month == 5 and d.day in [3, 4, 5]):
        return True
    # Obon (Aug 13-15)
    if d.month == 8 and d.day in [13, 14, 15]:
        return True
    return False


def _flu_spike(d: date) -> float:
    """Simulate influenza-driven prescription spikes.

    Sharp increase during peak flu weeks (typically weeks 4-8).
    """
    iso_week = d.isocalendar()[1]
    if 4 <= iso_week <= 8:
        # Peak flu season: gaussian-ish spike centered at week 6
        intensity = math.exp(-0.5 * ((iso_week - 6) / 1.5) ** 2)
        return 1.0 + 0.3 * intensity
    return 1.0


class Command(BaseCommand):
    help = "Generate sample prescription data for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=180,
            help="Number of days of data to generate (default: 180)",
        )
        parser.add_argument(
            "--start", type=str, default=None,
            help="Start date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--end", type=str, default=None,
            help="End date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--reset", action="store_true",
            help="Delete all existing prescription records before seeding",
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="Random seed for reproducibility (default: 42)",
        )

    def handle(self, *args, **options):
        random.seed(options["seed"])

        stores = Store.objects.filter(is_active=True)
        if not stores.exists():
            self.stderr.write(
                self.style.ERROR(
                    "No stores found. Run 'python manage.py seed_stores' first."
                )
            )
            return

        if options["reset"]:
            deleted, _ = PrescriptionRecord.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} existing prescription records")

        # Determine date range
        if options["start"]:
            start_date = date.fromisoformat(options["start"])
        else:
            start_date = date.today() - timedelta(days=options["days"])

        if options["end"]:
            end_date = date.fromisoformat(options["end"])
        else:
            end_date = date.today() - timedelta(days=1)

        self.stdout.write(
            f"Generating prescription data: {stores.count()} stores × "
            f"{(end_date - start_date).days + 1} days ({start_date} to {end_date})"
        )

        created = 0
        skipped = 0

        for store in stores:
            area = store.area
            base_low, base_high = AREA_BASE_COUNTS.get(area, (25, 50))
            # Each store gets a fixed base count (simulating store size variation)
            store_base = random.uniform(base_low, base_high)

            # Difficulty adjustment: harder stores tend to have more prescriptions
            # (more complex operations often correlate with higher volume)
            difficulty_factor = 1.0 + (float(store.effective_difficulty) - 3.0) * 0.05

            current = start_date
            while current <= end_date:
                dow_factor = _day_of_week_factor(current)

                # Skip Sundays (no prescriptions)
                if dow_factor == 0.0:
                    current += timedelta(days=1)
                    continue

                # Holidays
                if _holiday_check(current):
                    current += timedelta(days=1)
                    continue

                # Calculate prescription count
                count = store_base * difficulty_factor
                count *= _seasonal_factor(current)
                count *= dow_factor
                count *= _flu_spike(current)

                # Add random noise (±15%)
                noise = random.gauss(1.0, 0.15)
                count *= max(noise, 0.5)

                count = max(int(round(count)), 1)

                _, was_created = PrescriptionRecord.objects.update_or_create(
                    store=store,
                    date=current,
                    defaults={
                        "count": count,
                        "source": PrescriptionRecord.Source.CSV_UPLOAD,
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

                current += timedelta(days=1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {created} records created, {skipped} updated. "
                f"Total: {PrescriptionRecord.objects.count()}"
            )
        )
