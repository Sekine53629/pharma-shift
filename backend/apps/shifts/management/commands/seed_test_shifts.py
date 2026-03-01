"""Seed test data for the April shift period (2026-03-16 to 2026-04-15)."""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assignments.models import SupportSlot
from apps.shifts.models import Shift, ShiftPeriod
from apps.staff.models import Rounder, RounderStoreExperience, Staff
from apps.stores.models import Store

# ---------- Staff definitions ----------

MANAGING_PHARMACISTS = [
    # (name, store_name, monthly_working_days)
    ("佐藤明", "旭川大町店", 22),
    ("鈴木健一", "錦町店", 22),
    ("高橋美咲", "旭川駅前店", 22),
    ("田中直樹", "永山３条店", 22),
    ("渡辺裕子", "豊岡１２条店", 22),
    ("伊藤大輔", "神居３条店", 22),
    ("小林智子", "東光５条店", 22),
    ("加藤誠", "旭川近文店", 22),
    ("山本恵", "名寄西４条店", 22),
    ("中村翔太", "北見メッセ店", 22),
]

GENERAL_PHARMACISTS = [
    # (name, store_name, monthly_working_days, employment_type)
    # Busy stores (slots >= 2) get a second pharmacist for buffer
    ("岡田彩花", "錦町店", 22, "full_time"),
    ("西村健太", "旭川駅前店", 22, "full_time"),
    ("三浦優子", "豊岡１２条店", 20, "dispatch"),
    ("松田裕太", "神居３条店", 15, "part_time"),
    ("遠藤理恵", "名寄西４条店", 22, "full_time"),
]

ROUNDERS = [
    # (name, hr, can_work_alone, has_car, can_long_distance, mp_years, max_rx, monthly_working_days)
    ("松本陽介", "45.0", True, True, True, "6.0", 40, 22),
    ("井上真理", "40.0", True, True, False, "5.0", 35, 22),
    ("木村大地", "35.0", True, True, True, "4.0", 35, 22),
    ("林由美", "30.0", False, True, False, "3.0", 30, 20),
    ("清水拓也", "28.0", True, False, False, "2.0", 30, 22),
    ("山田あかり", "22.0", False, True, False, "1.0", 25, 15),
    ("佐々木翼", "18.0", False, False, False, "0.5", 25, 22),
    ("吉田美月", "15.0", False, True, False, "0", 20, 20),
]

CLERKS = [
    # (name, store_name, monthly_working_days)
    ("藤田恵", "旭川大町店", 22),
    ("石川光", "錦町店", 22),
]

# ---------- SupportSlot definitions ----------

SUPPORT_SLOTS = [
    # (store_name, date_offset_from_start, priority, forecast, solo_hours, attending_ph, has_chief, note)
    ("旭川大町店", 5, 1, "A", "2.0", 0, False, "管理薬剤師急病欠勤"),
    ("錦町店", 8, 1, "B", "0", 1, False, "管理薬剤師インフル欠勤"),
    ("旭川駅前店", 10, 2, "C", "0", 1, True, "義務有給消化（管理薬剤師）"),
    ("豊岡１２条店", 12, 2, "C", "0", 0, False, "義務有給消化"),
    ("名寄西４条店", 15, 2, "B", "1.0", 0, False, "義務有給消化（遠方）"),
    ("永山３条店", 3, 3, "C", "0", 1, False, "薬局長公休"),
    ("神居３条店", 7, 3, "D", "0", 1, True, "管理薬剤師研修"),
    ("東光５条店", 18, 3, "C", "0", 0, False, "管理薬剤師公休"),
    ("旭川近文店", 20, 4, "C", "0", 1, True, "健康診断"),
    ("北見メッセ店", 22, 4, "E", "0", 0, False, "希望休"),
    ("富良野店", 14, 4, "D", "0", 1, False, "健康診断（遠方）"),
    ("旭川大町店", 25, 5, "C", "0", 1, True, "有給消化"),
    ("錦町店", 26, 5, "C", "0", 1, False, "任意休暇"),
    ("旭川末広北店", 16, 5, "D", "0", 0, False, "その他有給"),
    ("稚内新光店", 19, 5, "C", "0", 0, False, "その他有給（遠方）"),
]

# Japanese public holidays in the shift period
HOLIDAYS = {
    date(2026, 3, 20),  # 春分の日
}

# Store assignment pools per area for rounders
AREA_STORES = {
    "旭川": [
        "旭川大町店", "東光５条店", "神居３条店", "永山３条店",
        "豊岡１２条店", "錦町店", "旭川近文店", "旭川駅前店",
        "旭川大町３条店", "忠和店", "旭川末広北店",
    ],
    "遠方": [
        "名寄西４条店", "名寄西５条店", "富良野店",
        "北見メッセ店", "南稚内店",
    ],
}


def _get_business_days(start: date, end: date) -> list[date]:
    """Return business days (Mon-Sat, excluding holidays) in [start, end]."""
    days = []
    current = start
    while current <= end:
        if current.weekday() != 6 and current not in HOLIDAYS:  # Skip Sunday & holidays
            days.append(current)
        current += timedelta(days=1)
    return days


class Command(BaseCommand):
    help = "Seed test shift data for April period (2026-03-16 to 2026-04-15)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all test data before seeding",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility (default: 42)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])

        if options["reset"]:
            self._reset()

        stores = self._ensure_stores()
        staff_list = self._create_staff(stores)
        rounder_objs = self._create_rounders(staff_list, stores, rng)
        self._create_rounder_experience(rounder_objs, stores, rng)
        period = self._create_shift_period()
        self._create_shifts(staff_list, period, stores, rng)
        self._create_support_slots(period, stores)

        self.stdout.write(self.style.SUCCESS("Done! Test data summary:"))
        self.stdout.write(f"  Staff: {Staff.objects.count()}")
        self.stdout.write(f"  Rounders: {Rounder.objects.count()}")
        self.stdout.write(f"  RounderStoreExperience: {RounderStoreExperience.objects.count()}")
        self.stdout.write(f"  ShiftPeriods: {ShiftPeriod.objects.count()}")
        self.stdout.write(f"  Shifts: {Shift.objects.count()}")
        self.stdout.write(f"  SupportSlots: {SupportSlot.objects.count()}")

    # ------------------------------------------------------------------ reset
    def _reset(self):
        """Delete seeded test data (preserves stores and users)."""
        counts = {}
        counts["SupportSlot"] = SupportSlot.objects.all().delete()[0]
        counts["Shift"] = Shift.objects.all().delete()[0]
        counts["ShiftPeriod"] = ShiftPeriod.objects.all().delete()[0]
        counts["RounderStoreExperience"] = RounderStoreExperience.objects.all().delete()[0]
        counts["Rounder"] = Rounder.objects.all().delete()[0]
        counts["Staff"] = Staff.objects.all().delete()[0]
        for model, n in counts.items():
            self.stdout.write(f"  Deleted {n} {model}")

    # ----------------------------------------------------------- ensure stores
    def _ensure_stores(self) -> dict[str, Store]:
        """Ensure stores exist (run seed_stores if needed) and return name->Store map."""
        if Store.objects.count() == 0:
            self.stdout.write("No stores found. Running seed_stores first...")
            from django.core.management import call_command
            call_command("seed_stores")
        return {s.name: s for s in Store.objects.all()}

    # -------------------------------------------------------------- staff
    def _create_staff(self, stores: dict[str, Store]) -> dict[str, Staff]:
        """Create 25 staff members. Returns name->Staff map."""
        created = 0
        skipped = 0
        result = {}

        # Managing pharmacists
        for name, store_name, mwd in MANAGING_PHARMACISTS:
            staff, was_created = Staff.objects.get_or_create(
                name=name,
                defaults={
                    "role": Staff.Role.MANAGING_PHARMACIST,
                    "employment_type": Staff.EmploymentType.FULL_TIME,
                    "store": stores.get(store_name),
                    "is_rounder": False,
                    "monthly_working_days": mwd,
                },
            )
            result[name] = staff
            if was_created:
                created += 1
            else:
                skipped += 1

        # General pharmacists (second pharmacist at busy stores)
        emp_type_map = {
            "full_time": Staff.EmploymentType.FULL_TIME,
            "part_time": Staff.EmploymentType.PART_TIME,
            "dispatch": Staff.EmploymentType.DISPATCH,
        }
        for name, store_name, mwd, emp in GENERAL_PHARMACISTS:
            staff, was_created = Staff.objects.get_or_create(
                name=name,
                defaults={
                    "role": Staff.Role.PHARMACIST,
                    "employment_type": emp_type_map[emp],
                    "store": stores.get(store_name),
                    "is_rounder": False,
                    "monthly_working_days": mwd,
                },
            )
            result[name] = staff
            if was_created:
                created += 1
            else:
                skipped += 1

        # Rounders
        for name, *_, mwd in ROUNDERS:
            staff, was_created = Staff.objects.get_or_create(
                name=name,
                defaults={
                    "role": Staff.Role.PHARMACIST,
                    "employment_type": Staff.EmploymentType.FULL_TIME,
                    "store": None,
                    "is_rounder": True,
                    "monthly_working_days": mwd,
                },
            )
            result[name] = staff
            if was_created:
                created += 1
            else:
                skipped += 1

        # Clerks
        for name, store_name, mwd in CLERKS:
            staff, was_created = Staff.objects.get_or_create(
                name=name,
                defaults={
                    "role": Staff.Role.CLERK,
                    "employment_type": Staff.EmploymentType.FULL_TIME,
                    "store": stores.get(store_name),
                    "is_rounder": False,
                    "monthly_working_days": mwd,
                },
            )
            result[name] = staff
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(f"Staff: created {created}, skipped {skipped}")
        return result

    # ------------------------------------------------------------ rounders
    def _create_rounders(
        self,
        staff_map: dict[str, Staff],
        stores: dict[str, Store],
        rng: random.Random,
    ) -> list[Rounder]:
        """Create Rounder profiles for rounder staff."""
        created = 0
        skipped = 0
        result = []

        for name, hr, alone, car, long_dist, mp_years, max_rx, _mwd in ROUNDERS:
            staff = staff_map[name]
            rounder, was_created = Rounder.objects.get_or_create(
                staff=staff,
                defaults={
                    "hunter_rank": Decimal(hr),
                    "can_work_alone": alone,
                    "has_car": car,
                    "can_long_distance": long_dist,
                    "managing_pharmacist_years": Decimal(mp_years),
                    "max_prescriptions": max_rx,
                },
            )
            result.append(rounder)
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(f"Rounders: created {created}, skipped {skipped}")
        return result

    # ------------------------------------------------- rounder experience
    def _create_rounder_experience(
        self,
        rounders: list[Rounder],
        stores: dict[str, Store],
        rng: random.Random,
    ):
        """Create store experience records (~3 per rounder)."""
        created = 0
        skipped = 0

        asahikawa_stores = [
            stores[n] for n in AREA_STORES["旭川"] if n in stores
        ]
        remote_stores = [
            stores[n] for n in AREA_STORES["遠方"] if n in stores
        ]

        for rounder in rounders:
            # Each rounder gets 2-4 experienced stores
            hr = float(rounder.hunter_rank)
            if hr >= 35:
                n_stores = rng.randint(3, 4)
            elif hr >= 25:
                n_stores = rng.randint(2, 3)
            else:
                n_stores = rng.randint(1, 2)

            # Veterans also get remote store experience
            exp_stores = rng.sample(asahikawa_stores, min(n_stores, len(asahikawa_stores)))
            if rounder.can_long_distance and remote_stores:
                exp_stores.append(rng.choice(remote_stores))

            for store in exp_stores:
                visit_count = rng.randint(2, 20) if hr >= 30 else rng.randint(1, 5)
                first_visit = date(2025, 1, 1) + timedelta(days=rng.randint(0, 300))
                last_visit = date(2026, 1, 1) + timedelta(days=rng.randint(0, 60))

                _, was_created = RounderStoreExperience.objects.get_or_create(
                    rounder=rounder,
                    store=store,
                    defaults={
                        "first_visit_date": first_visit,
                        "last_visit_date": last_visit,
                        "visit_count": visit_count,
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

        self.stdout.write(f"RounderStoreExperience: created {created}, skipped {skipped}")

    # --------------------------------------------------------- shift period
    def _create_shift_period(self) -> ShiftPeriod:
        """Create the April shift period (2026-03-16 to 2026-04-15)."""
        period, was_created = ShiftPeriod.objects.get_or_create(
            start_date=date(2026, 3, 16),
            end_date=date(2026, 4, 15),
            defaults={
                "request_deadline": date(2026, 3, 1),
                "is_finalized": False,
            },
        )
        status = "created" if was_created else "already exists"
        self.stdout.write(f"ShiftPeriod: {period} ({status})")
        return period

    # -------------------------------------------------------------- shifts
    def _create_shifts(
        self,
        staff_map: dict[str, Staff],
        period: ShiftPeriod,
        stores: dict[str, Store],
        rng: random.Random,
    ):
        """Generate shifts for all staff with monthly working day limits."""
        start = period.start_date
        end = period.end_date
        business_days = _get_business_days(start, end)
        march_cutoff = date(2026, 4, 1)  # Boundary for confirmation rate

        created = 0
        skipped = 0

        asahikawa_stores = [
            stores[n] for n in AREA_STORES["旭川"] if n in stores
        ]
        remote_stores = [
            stores[n] for n in AREA_STORES["遠方"] if n in stores
        ]
        all_rounder_stores = asahikawa_stores + remote_stores

        # --- Managing pharmacists: work at their own store ---
        for name, store_name, _mwd in MANAGING_PHARMACISTS:
            staff = staff_map[name]
            home_store = stores.get(store_name)
            if not home_store:
                continue

            max_days = staff.effective_monthly_working_days
            working_day_count = 0

            for day in business_days:
                roll = rng.random()

                # Saturday: 20% off
                if day.weekday() == 5 and rng.random() < 0.20:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                # 5% paid leave
                elif roll < 0.05:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.PAID,
                    }
                # 5% holiday
                elif roll < 0.10:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                # Monthly limit reached -> holiday
                elif working_day_count >= max_days:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                # Normal work
                else:
                    shift_data = {
                        "store": home_store,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": None,
                    }

                if shift_data["leave_type"] is None:
                    working_day_count += 1

                is_confirmed = rng.random() < (0.70 if day < march_cutoff else 0.40)

                _, was_created = Shift.objects.get_or_create(
                    staff=staff,
                    date=day,
                    shift_type=shift_data["shift_type"],
                    defaults={
                        "shift_period": period,
                        "store": shift_data["store"],
                        "leave_type": shift_data["leave_type"],
                        "is_confirmed": is_confirmed,
                        "note": "",
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

        # --- General pharmacists: work at their home store ---
        for name, store_name, _mwd, _emp in GENERAL_PHARMACISTS:
            staff = staff_map[name]
            home_store = stores.get(store_name)
            if not home_store:
                continue

            max_days = staff.effective_monthly_working_days
            working_day_count = 0

            for day in business_days:
                roll = rng.random()

                # Saturday: 30% off
                if day.weekday() == 5 and rng.random() < 0.30:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                # 5% paid leave
                elif roll < 0.05:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.PAID,
                    }
                # 8% holiday
                elif roll < 0.13:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                # Monthly limit reached -> holiday
                elif working_day_count >= max_days:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                # Normal work at home store
                else:
                    shift_data = {
                        "store": home_store,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": None,
                    }

                if shift_data["leave_type"] is None:
                    working_day_count += 1

                is_confirmed = rng.random() < (0.70 if day < march_cutoff else 0.40)

                _, was_created = Shift.objects.get_or_create(
                    staff=staff,
                    date=day,
                    shift_type=shift_data["shift_type"],
                    defaults={
                        "shift_period": period,
                        "store": shift_data["store"],
                        "leave_type": shift_data["leave_type"],
                        "is_confirmed": is_confirmed,
                        "note": "",
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

        # --- Rounders: assigned to various stores ---
        for name, *_, _mwd in ROUNDERS:
            staff = staff_map[name]
            max_days = staff.effective_monthly_working_days
            working_day_count = 0

            for day in business_days:
                roll = rng.random()

                # 10% paid leave
                if roll < 0.10:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.PAID,
                    }
                    result = self._try_create_shift(staff, day, period, shift_data, march_cutoff, rng)
                    if result:
                        created += 1
                    else:
                        skipped += 1
                    continue

                # 5% holiday
                if roll < 0.15:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                    result = self._try_create_shift(staff, day, period, shift_data, march_cutoff, rng)
                    if result:
                        created += 1
                    else:
                        skipped += 1
                    continue

                # Monthly limit reached -> holiday
                if working_day_count >= max_days:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                    result = self._try_create_shift(staff, day, period, shift_data, march_cutoff, rng)
                    if result:
                        created += 1
                    else:
                        skipped += 1
                    continue

                # 10% split (morning + afternoon at different stores)
                if roll < 0.25 and len(all_rounder_stores) >= 2:
                    two_stores = rng.sample(all_rounder_stores, 2)
                    for st, stype in zip(two_stores, [Shift.ShiftType.MORNING, Shift.ShiftType.AFTERNOON]):
                        split_data = {
                            "store": st,
                            "shift_type": stype,
                            "leave_type": None,
                        }
                        result = self._try_create_shift(staff, day, period, split_data, march_cutoff, rng)
                        if result:
                            created += 1
                        else:
                            skipped += 1
                    # Split counts as 1 working day
                    working_day_count += 1
                    continue

                # 75% normal full-day at a random store
                target_store = rng.choice(all_rounder_stores)
                shift_data = {
                    "store": target_store,
                    "shift_type": Shift.ShiftType.FULL,
                    "leave_type": None,
                }
                result = self._try_create_shift(staff, day, period, shift_data, march_cutoff, rng)
                if result:
                    created += 1
                else:
                    skipped += 1
                working_day_count += 1

        # --- Clerks: work at their own store ---
        for name, store_name, _mwd in CLERKS:
            staff = staff_map[name]
            home_store = stores.get(store_name)
            if not home_store:
                continue

            max_days = staff.effective_monthly_working_days
            working_day_count = 0

            for day in business_days:
                # Saturday: 50% off for clerks
                if day.weekday() == 5 and rng.random() < 0.50:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                # Monthly limit reached -> holiday
                elif working_day_count >= max_days:
                    shift_data = {
                        "store": None,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": Shift.LeaveType.HOLIDAY,
                    }
                else:
                    shift_data = {
                        "store": home_store,
                        "shift_type": Shift.ShiftType.FULL,
                        "leave_type": None,
                    }

                if shift_data["leave_type"] is None:
                    working_day_count += 1

                is_confirmed = rng.random() < (0.70 if day < march_cutoff else 0.40)
                _, was_created = Shift.objects.get_or_create(
                    staff=staff,
                    date=day,
                    shift_type=shift_data["shift_type"],
                    defaults={
                        "shift_period": period,
                        "store": shift_data["store"],
                        "leave_type": shift_data["leave_type"],
                        "is_confirmed": is_confirmed,
                        "note": "",
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

        self.stdout.write(f"Shifts: created {created}, skipped {skipped}")

    def _try_create_shift(
        self,
        staff: Staff,
        day: date,
        period: ShiftPeriod,
        shift_data: dict,
        march_cutoff: date,
        rng: random.Random,
    ) -> bool:
        """Try to create a shift. Returns True if created, False if skipped."""
        is_confirmed = rng.random() < (0.70 if day < march_cutoff else 0.40)
        _, was_created = Shift.objects.get_or_create(
            staff=staff,
            date=day,
            shift_type=shift_data["shift_type"],
            defaults={
                "shift_period": period,
                "store": shift_data["store"],
                "leave_type": shift_data["leave_type"],
                "is_confirmed": is_confirmed,
                "note": "",
            },
        )
        return was_created

    # ------------------------------------------------------- support slots
    def _create_support_slots(self, period: ShiftPeriod, stores: dict[str, Store]):
        """Create 15 unfilled support slots across priorities and areas."""
        created = 0
        skipped = 0

        for store_name, day_offset, priority, forecast, solo, att_ph, chief, note in SUPPORT_SLOTS:
            store = stores.get(store_name)
            if not store:
                self.stdout.write(self.style.WARNING(f"  Store not found: {store_name}"))
                continue

            slot_date = period.start_date + timedelta(days=day_offset)
            # Skip if the date falls on Sunday or holiday
            if slot_date.weekday() == 6 or slot_date in HOLIDAYS:
                slot_date += timedelta(days=1)

            _, was_created = SupportSlot.objects.get_or_create(
                store=store,
                shift_period=period,
                date=slot_date,
                priority=priority,
                defaults={
                    "base_difficulty": store.base_difficulty,
                    "attending_pharmacists": att_ph,
                    "attending_clerks": 0,
                    "has_chief_present": chief,
                    "solo_hours": Decimal(solo),
                    "prescription_forecast": forecast,
                    "is_filled": False,
                    "note": note,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(f"SupportSlots: created {created}, skipped {skipped}")
