from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.shifts.models import ShiftPeriod
from apps.staff.models import Rounder, RounderStoreExperience, Staff
from apps.stores.models import Store

from .models import SupportSlot
from .services import check_assignment_prerequisites, score_rounder


class SupportSlotDifficultyTest(TestCase):
    def test_effective_difficulty_calculation(self):
        store = Store.objects.create(name="テスト店舗", base_difficulty=Decimal("3.0"))
        period = ShiftPeriod.objects.create(
            start_date=date(2026, 2, 16),
            end_date=date(2026, 3, 15),
            request_deadline=date(2026, 2, 1),
        )
        slot = SupportSlot(
            store=store,
            shift_period=period,
            date=date(2026, 2, 20),
            base_difficulty=Decimal("3.0"),
            attending_pharmacists=1,
            has_chief_present=True,
            solo_hours=Decimal("0"),
            prescription_forecast="C",
        )
        # base * 10 - chief(5) - pharmacists(3) + solo(0) + forecast(0)
        # 30 - 5 - 3 = 22
        difficulty = slot.calculate_effective_difficulty()
        self.assertEqual(difficulty, Decimal("22"))


class AssignmentScoringTest(TestCase):
    def setUp(self):
        self.store = Store.objects.create(name="テスト店舗", base_difficulty=Decimal("3.0"))
        self.period = ShiftPeriod.objects.create(
            start_date=date(2026, 2, 16),
            end_date=date(2026, 3, 15),
            request_deadline=date(2026, 2, 1),
        )
        self.staff = Staff.objects.create(
            name="ラウンダーA",
            role=Staff.Role.PHARMACIST,
            is_rounder=True,
        )
        self.rounder = Rounder.objects.create(
            staff=self.staff,
            hunter_rank=Decimal("50"),
            can_work_alone=True,
        )

    def test_experienced_store_bonus(self):
        RounderStoreExperience.objects.create(
            rounder=self.rounder,
            store=self.store,
            visit_count=5,
        )

        slot = SupportSlot.objects.create(
            store=self.store,
            shift_period=self.period,
            date=date(2026, 2, 20),
            effective_difficulty_hr=Decimal("30"),
        )

        score = score_rounder(self.rounder, slot)
        self.assertGreaterEqual(score, Decimal("100"))  # experienced store bonus

    def test_prerequisites_hr_check(self):
        slot = SupportSlot.objects.create(
            store=self.store,
            shift_period=self.period,
            date=date(2026, 2, 20),
            effective_difficulty_hr=Decimal("60"),
            required_hr=Decimal("60"),
        )
        errors = check_assignment_prerequisites(self.rounder, slot)
        self.assertIn("HR値が不足しています", errors[0])
