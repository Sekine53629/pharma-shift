from decimal import Decimal

from django.test import TestCase

from apps.stores.models import Store

from .models import Rounder, RounderStoreExperience, Staff


class StaffModelTest(TestCase):
    def setUp(self):
        self.store = Store.objects.create(name="テスト店舗", base_difficulty=Decimal("3.0"))

    def test_managing_pharmacist_requires_store(self):
        staff = Staff.objects.create(
            name="管理薬剤師",
            role=Staff.Role.MANAGING_PHARMACIST,
            store=self.store,
        )
        self.assertTrue(staff.is_managing_pharmacist)

    def test_rounder_initial_hr(self):
        staff = Staff.objects.create(
            name="ラウンダーA",
            role=Staff.Role.PHARMACIST,
            is_rounder=True,
        )
        rounder = Rounder.objects.create(
            staff=staff,
            managing_pharmacist_years=Decimal("4.0"),
        )
        self.assertEqual(rounder.initial_hr, Decimal("20.0"))  # 4 * 5 = 20

    def test_rounder_initial_hr_cap(self):
        staff = Staff.objects.create(
            name="ラウンダーB",
            role=Staff.Role.PHARMACIST,
            is_rounder=True,
        )
        rounder = Rounder.objects.create(
            staff=staff,
            managing_pharmacist_years=Decimal("10.0"),
        )
        self.assertEqual(rounder.initial_hr, Decimal("30"))  # capped at 30


class RounderStoreExperienceTest(TestCase):
    def test_experience_tracking(self):
        store = Store.objects.create(name="テスト店舗")
        staff = Staff.objects.create(name="ラウンダー", role="pharmacist", is_rounder=True)
        rounder = Rounder.objects.create(staff=staff)

        exp = RounderStoreExperience.objects.create(
            rounder=rounder, store=store, visit_count=3
        )
        self.assertEqual(exp.visit_count, 3)
