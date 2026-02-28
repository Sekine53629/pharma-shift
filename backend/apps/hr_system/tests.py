from decimal import Decimal

from django.test import TestCase

from apps.staff.models import Rounder, Staff

from .models import HrEvaluation
from .services import points_to_hr


class HrGrowthCurveTest(TestCase):
    def test_low_range(self):
        # 1pt = 2HR for points <= 30
        self.assertEqual(points_to_hr(Decimal("10")), Decimal("20"))
        self.assertEqual(points_to_hr(Decimal("30")), Decimal("60"))

    def test_mid_range(self):
        # 1pt = 1HR for 30 < points <= 60
        self.assertEqual(points_to_hr(Decimal("45")), Decimal("75"))
        self.assertEqual(points_to_hr(Decimal("60")), Decimal("90"))

    def test_high_range(self):
        # 1pt = 0.5HR for points > 60
        self.assertEqual(points_to_hr(Decimal("80")), Decimal("100"))


class HrEvaluationModelTest(TestCase):
    def setUp(self):
        self.evaluator = Staff.objects.create(name="評価者", role="pharmacist")
        self.rounder_staff = Staff.objects.create(
            name="ラウンダー", role="pharmacist", is_rounder=True
        )
        self.rounder = Rounder.objects.create(staff=self.rounder_staff)

    def test_create_evaluation(self):
        ev = HrEvaluation(
            evaluator=self.evaluator,
            rounder=self.rounder,
            period_start="2026-01-01",
            period_end="2026-06-30",
            score=Decimal("0.5"),
            reason="良好な対応",
        )
        ev.save()
        self.assertEqual(HrEvaluation.objects.count(), 1)

    def test_update_prohibited(self):
        ev = HrEvaluation(
            evaluator=self.evaluator,
            rounder=self.rounder,
            period_start="2026-01-01",
            period_end="2026-06-30",
            score=Decimal("0.5"),
            reason="テスト",
        )
        ev.save()

        ev.score = Decimal("1.0")
        with self.assertRaises(ValueError):
            ev.save()

    def test_delete_prohibited(self):
        ev = HrEvaluation(
            evaluator=self.evaluator,
            rounder=self.rounder,
            period_start="2026-01-01",
            period_end="2026-06-30",
            score=Decimal("-0.5"),
            reason="テスト",
        )
        ev.save()

        with self.assertRaises(ValueError):
            ev.delete()
