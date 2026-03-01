"""Auto-generate SupportSlots for understaffed days.

For each store x date in the given shift period:
  1. Count pharmacists working at the store
  2. If pharmacist_count < store.min_pharmacists → create SupportSlot(s)
  3. Set difficulty parameters based on 処方枚数/人 and shortage severity
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.assignments.models import SupportSlot
from apps.shifts.models import Shift, ShiftPeriod
from apps.staff.models import Staff
from apps.stores.models import Store


# 日本の祝日 (対象期間)
JAPANESE_HOLIDAYS = {date(2026, 3, 20)}

# 1日あたりの処方枚数 (全店統一テスト値)
DEFAULT_DAILY_RX = 150


def _is_closed(day: date) -> bool:
    return day.weekday() == 6 or day in JAPANESE_HOLIDAYS


def _rx_forecast(rx_per_person: float) -> str:
    """1人あたり処方枚数 → 予測ランク."""
    if rx_per_person >= 50:
        return "A"  # 超過密
    if rx_per_person >= 38:
        return "B"  # 多忙
    if rx_per_person >= 30:
        return "C"  # 通常
    if rx_per_person >= 25:
        return "D"  # 余裕
    return "E"      # 軽い


def _priority_from_shortage(shortage: int) -> int:
    """不足人数 → 優先度 (P1=最高, P5=最低)."""
    if shortage >= 3:
        return 1  # P1: 緊急
    if shortage >= 2:
        return 2  # P2: 深刻
    return 3      # P3: 要応援


def _solo_hours(attending: int, is_saturday: bool) -> Decimal:
    """出勤薬剤師数 → 応援者のソロ時間."""
    max_hours = Decimal("4") if is_saturday else Decimal("8")
    if attending == 0:
        return max_hours       # 終日1人
    if attending == 1:
        return Decimal("2.0")  # 休憩時に1人
    return Decimal("0")


class Command(BaseCommand):
    help = "Auto-generate SupportSlots for understaffed days"

    def add_arguments(self, parser):
        parser.add_argument(
            "--period",
            type=int,
            help="ShiftPeriod ID (default: latest)",
        )
        parser.add_argument(
            "--rx",
            type=int,
            default=DEFAULT_DAILY_RX,
            help=f"Daily prescription count per store (default: {DEFAULT_DAILY_RX})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without saving",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing auto-generated slots before creating",
        )
        parser.add_argument(
            "--store",
            nargs="*",
            help="Store names to target (default: all stores with shifts)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Resolve period
        if options["period"]:
            period = ShiftPeriod.objects.get(pk=options["period"])
        else:
            period = ShiftPeriod.objects.order_by("-start_date").first()
            if not period:
                self.stderr.write("No ShiftPeriod found.")
                return

        self.stdout.write(f"Period: {period}")
        daily_rx = options["rx"]
        dry_run = options["dry_run"]

        if options["clear"] and not dry_run:
            n, _ = SupportSlot.objects.filter(
                shift_period=period,
                note__startswith="[auto]",
            ).delete()
            self.stdout.write(f"  Cleared {n} auto-generated slots")

        # Target stores
        if options["store"]:
            stores = Store.objects.filter(name__in=options["store"], is_active=True)
        else:
            store_ids_with_shifts = (
                Shift.objects.filter(shift_period=period, store__isnull=False, leave_type__isnull=True)
                .values_list("store_id", flat=True)
                .distinct()
            )
            stores = Store.objects.filter(id__in=store_ids_with_shifts, is_active=True)
        self.stdout.write(f"  Target stores: {', '.join(s.name for s in stores)}")

        # Get all shifts in this period
        shifts = Shift.objects.filter(shift_period=period).select_related("staff", "store")

        # Build index: (store_id, date) -> list of (staff, shift)
        store_date_shifts: dict[tuple[int, date], list[tuple[Staff, Shift]]] = {}
        for s in shifts:
            if s.store_id and not s.leave_type:
                key = (s.store_id, s.date)
                if key not in store_date_shifts:
                    store_date_shifts[key] = []
                store_date_shifts[key].append((s.staff, s))

        created = 0
        skipped = 0

        # Walk each store x each day
        cur = period.start_date
        while cur <= period.end_date:
            if _is_closed(cur):
                cur += timedelta(days=1)
                continue

            is_saturday = cur.weekday() == 5

            for store in stores:
                entries = store_date_shifts.get((store.id, cur), [])

                # Count pharmacists
                pharmacists = [
                    staff for staff, shift in entries
                    if staff.role in ("pharmacist", "managing_pharmacist")
                ]
                ph_count = len(pharmacists)
                shortage = store.min_pharmacists - ph_count

                if shortage <= 0:
                    continue

                # Check if slot already exists for this store+date
                existing = SupportSlot.objects.filter(
                    store=store, shift_period=period, date=cur,
                ).exists()
                if existing:
                    skipped += 1
                    continue

                # Calculate parameters
                # 応援者が来た場合の1人あたり枚数 (attending + 1)
                rx_per_person = daily_rx / max(ph_count + 1, 1)
                forecast = _rx_forecast(rx_per_person)
                priority = _priority_from_shortage(shortage)
                solo_h = _solo_hours(ph_count, is_saturday)
                has_chief = any(
                    staff.role == "managing_pharmacist" for staff, _ in entries
                )

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] {cur} {store.name}: "
                        f"ph={ph_count}/{store.min_pharmacists} "
                        f"shortage={shortage} P{priority} "
                        f"forecast={forecast} solo={solo_h}h "
                        f"chief={'Y' if has_chief else 'N'}"
                    )
                    created += 1
                    continue

                SupportSlot.objects.create(
                    store=store,
                    shift_period=period,
                    date=cur,
                    priority=priority,
                    base_difficulty=store.base_difficulty,
                    attending_pharmacists=ph_count,
                    attending_clerks=0,
                    has_chief_present=has_chief,
                    solo_hours=solo_h,
                    prescription_forecast=forecast,
                    is_filled=False,
                    note=f"[auto] 薬剤師不足 {ph_count}/{store.min_pharmacists} (不足{shortage}名)",
                )
                created += 1

            cur += timedelta(days=1)

        tag = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"\n{tag}Created: {created}, Skipped (existing): {skipped}"
        ))
