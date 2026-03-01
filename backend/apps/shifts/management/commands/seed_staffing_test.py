"""Seed focused test data for staffing-check page (3 stores only).

Period: 2026-03-16 ~ 2026-04-15 (31 days)
  Closed days (日曜+祝日): 5 (3/20祝, 3/22日, 3/29日, 4/5日, 4/12日)
  Business days: 26
  Working days per staff: 21 (= 26 - 5 regular days off)
  出勤合計(21) = 配属店勤務 + 応援勤務 + 有給
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.shifts.models import Shift, ShiftPeriod
from apps.staff.models import Staff
from apps.stores.models import Store


# ---------- Constants ----------

PERIOD_START = date(2026, 3, 16)
PERIOD_END = date(2026, 4, 15)
PERIOD_DEADLINE = date(2026, 3, 1)

JAPANESE_HOLIDAYS = {date(2026, 3, 20)}  # 春分の日

WORKING_DAYS_PER_STAFF = 21  # 出勤合計数 (有給含む)

# ---------- Store definitions ----------

STORES = [
    # (name, area, min_pharmacists, base_difficulty)
    ("神居３条店", "旭川", 4, "3.0"),
    ("忠和店", "旭川", 1, "2.0"),
    ("旭川駅前店", "旭川", 4, "3.5"),
]

# ---------- Staff definitions ----------
# (name, role, employment_type, is_rounder)

STAFF_DEFS = {
    "神居３条店": [
        ("関根 禎浩", "pharmacist", "full_time", False),
        ("鈴木 正宏", "managing_pharmacist", "full_time", False),
        ("佐藤 智加子", "pharmacist", "full_time", False),
        ("久保田 温子", "pharmacist", "full_time", False),
        ("内海 翔平", "pharmacist", "full_time", False),
        ("高橋 愛奈", "pharmacist", "full_time", False),
        ("高田 一輝", "pharmacist", "full_time", False),
    ],
    "忠和店": [
        ("石岡 直人", "managing_pharmacist", "full_time", False),
    ],
    "旭川駅前店": [
        ("長谷川 良平", "managing_pharmacist", "full_time", False),
        ("古川 穂乃花", "pharmacist", "full_time", False),
        ("三浦 理美", "pharmacist", "dispatch", False),   # 派遣・調剤できず
        ("平 みどり", "pharmacist", "full_time", True),    # 全日応援
    ],
}


# ---------- Helpers ----------

def _all_days() -> list[date]:
    """Period の全日リスト."""
    days = []
    cur = PERIOD_START
    while cur <= PERIOD_END:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def _is_closed(day: date) -> bool:
    """日曜 or 祝日."""
    return day.weekday() == 6 or day in JAPANESE_HOLIDAYS


def _business_days() -> list[date]:
    """営業日のみ."""
    return [d for d in _all_days() if not _is_closed(d)]


def _shift_type(day: date) -> str:
    """土曜=morning(9-13時), 平日=full(9-18時)."""
    return "morning" if day.weekday() == 5 else "full"


def _pick_off_days(bdays: list[date], staff_idx: int, count: int = 5) -> set[date]:
    """スタッフごとに公休日を分散して選択.
    staff_idx をオフセットにして、均等に散らす."""
    off = set()
    step = len(bdays) // (count + 1)  # 26 // 6 = 4 → 4日おき
    for i in range(count):
        idx = (staff_idx + step * (i + 1)) % len(bdays)
        off.add(bdays[idx])
    return off


class Command(BaseCommand):
    help = "Seed focused staffing-check test data (3 stores, 12 staff, 21 working days each)"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete test data first")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        stores = self._create_stores()
        staff_map = self._create_staff(stores)
        period = self._create_period()
        self._create_shifts(staff_map, stores, period)
        self._verify(period)

    # ---- Reset ----
    def _reset(self):
        names = []
        for defs in STAFF_DEFS.values():
            names.extend(n for n, *_ in defs)
        staff_qs = Staff.objects.filter(name__in=names)
        n_shifts = Shift.objects.filter(staff__in=staff_qs).delete()[0]
        n_staff = staff_qs.delete()[0]
        self.stdout.write(f"  Deleted {n_shifts} shifts, {n_staff} staff")

    # ---- Stores ----
    def _create_stores(self) -> dict[str, Store]:
        result = {}
        for name, area, min_ph, diff in STORES:
            store, created = Store.objects.update_or_create(
                name=name,
                defaults={
                    "area": area,
                    "min_pharmacists": min_ph,
                    "base_difficulty": Decimal(diff),
                    "is_active": True,
                },
            )
            status = "created" if created else "updated"
            self.stdout.write(f"  Store: {name} (min_ph={min_ph}) [{status}]")
            result[name] = store
        return result

    # ---- Staff ----
    def _create_staff(self, stores: dict[str, Store]) -> dict[str, list[Staff]]:
        role_map = {
            "pharmacist": Staff.Role.PHARMACIST,
            "managing_pharmacist": Staff.Role.MANAGING_PHARMACIST,
        }
        emp_map = {
            "full_time": Staff.EmploymentType.FULL_TIME,
            "dispatch": Staff.EmploymentType.DISPATCH,
        }
        result = {}
        for store_name, defs in STAFF_DEFS.items():
            store = stores[store_name]
            staff_list = []
            for name, role, emp, is_rounder in defs:
                staff, created = Staff.objects.update_or_create(
                    name=name,
                    defaults={
                        "role": role_map[role],
                        "employment_type": emp_map[emp],
                        "store": store,
                        "is_rounder": is_rounder,
                        "monthly_working_days": WORKING_DAYS_PER_STAFF,
                        "is_active": True,
                    },
                )
                staff_list.append(staff)
                tag = "created" if created else "updated"
                self.stdout.write(f"  Staff: {name} -> {store_name} (wd={WORKING_DAYS_PER_STAFF}) [{tag}]")
            result[store_name] = staff_list
        return result

    # ---- Period ----
    def _create_period(self) -> ShiftPeriod:
        period, created = ShiftPeriod.objects.get_or_create(
            start_date=PERIOD_START,
            end_date=PERIOD_END,
            defaults={"request_deadline": PERIOD_DEADLINE, "is_finalized": False},
        )
        self.stdout.write(f"  Period: {period} [{'created' if created else 'exists'}]")
        return period

    # ---- Shifts ----
    def _add(self, staff, day, period, store, leave_type, confirmed=True):
        """Create one shift record."""
        stype = _shift_type(day) if not leave_type else "full"
        Shift.objects.get_or_create(
            staff=staff, date=day, shift_type=stype,
            defaults={
                "shift_period": period,
                "store": store if not leave_type else None,
                "leave_type": leave_type,
                "is_confirmed": confirmed,
            },
        )

    def _create_shifts(
        self,
        staff_map: dict[str, list[Staff]],
        stores: dict[str, Store],
        period: ShiftPeriod,
    ):
        all_days = _all_days()
        bdays = _business_days()
        kamui = stores["神居３条店"]
        chuwa = stores["忠和店"]
        ekimae = stores["旭川駅前店"]

        global_idx = 0  # 全スタッフ通しのindex (公休分散用)

        # ==== 神居３条店 (7名) ====
        for i, staff in enumerate(staff_map["神居３条店"]):
            off_days = _pick_off_days(bdays, global_idx)
            global_idx += 1
            work_count = 0

            for day in all_days:
                if _is_closed(day):
                    self._add(staff, day, period, None, "holiday")
                    continue

                if day in off_days:
                    self._add(staff, day, period, None, "holiday")
                    continue

                # 鈴木(管理者): 水曜午後は研修 → AMのみ
                if staff.name == "鈴木 正宏" and day.weekday() == 2:
                    Shift.objects.get_or_create(
                        staff=staff, date=day, shift_type="morning",
                        defaults={
                            "shift_period": period, "store": kamui,
                            "leave_type": None, "is_confirmed": True,
                        },
                    )
                    work_count += 1
                    continue

                self._add(staff, day, period, kamui, None, day < date(2026, 4, 1))
                work_count += 1

        # ==== 忠和店 (1名) ====
        ishioka = staff_map["忠和店"][0]
        off_days = _pick_off_days(bdays, global_idx)
        global_idx += 1

        for day in all_days:
            if _is_closed(day):
                self._add(ishioka, day, period, None, "holiday")
            elif day in off_days:
                self._add(ishioka, day, period, None, "holiday")
            else:
                self._add(ishioka, day, period, chuwa, None)

        # ==== 旭川駅前店 (4名) ====
        for staff in staff_map["旭川駅前店"]:
            off_days = _pick_off_days(bdays, global_idx)
            global_idx += 1
            work_count = 0

            for day in all_days:
                if _is_closed(day):
                    self._add(staff, day, period, None, "holiday")
                    continue

                if day in off_days:
                    self._add(staff, day, period, None, "holiday")
                    continue

                # 平 みどり: 全日応援 → 神居３条店 or 忠和店
                if staff.name == "平 みどり":
                    day_offset = (day - PERIOD_START).days
                    target = kamui if day_offset % 3 != 0 else chuwa
                    self._add(staff, day, period, target, None)
                    work_count += 1
                    continue

                self._add(staff, day, period, ekimae, None, day < date(2026, 4, 1))
                work_count += 1

        total = Shift.objects.filter(shift_period=period).count()
        self.stdout.write(f"  Shifts in period: {total}")

    # ---- Verify ----
    def _verify(self, period: ShiftPeriod):
        """各スタッフの日数を検証."""
        from django.db.models import Count, Q

        self.stdout.write(self.style.SUCCESS("\n  === Verification ==="))
        names = []
        for defs in STAFF_DEFS.values():
            names.extend(n for n, *_ in defs)

        for staff in Staff.objects.filter(name__in=names).order_by("store__name", "name"):
            qs = Shift.objects.filter(staff=staff, shift_period=period)
            total = qs.count()
            closed = qs.filter(
                Q(date__week_day=1) | Q(date__in=JAPANESE_HOLIDAYS),
                leave_type="holiday",
            ).count()
            regular_off = qs.filter(leave_type="holiday").count() - closed
            work = qs.filter(leave_type__isnull=True).count()
            paid = qs.filter(leave_type="paid").count()
            working_total = work + paid

            ok = "OK" if total == 31 and working_total == WORKING_DAYS_PER_STAFF else "NG"
            self.stdout.write(
                f"  {staff.name:12s} | total={total} | "
                f"closed={closed} off={regular_off} work={work} paid={paid} | "
                f"出勤計={working_total} [{ok}]"
            )
