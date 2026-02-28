from decimal import Decimal

from django.test import TestCase

from .models import Store


class StoreModelTest(TestCase):
    def test_effective_difficulty_no_flags(self):
        store = Store(name="テスト店舗", base_difficulty=Decimal("3.0"))
        self.assertEqual(store.effective_difficulty, Decimal("3.0"))

    def test_effective_difficulty_with_flags(self):
        store = Store(
            name="テスト店舗",
            base_difficulty=Decimal("3.0"),
            has_controlled_medical_device=True,  # +0.5
            has_toxic_substances=True,  # +0.5
        )
        self.assertEqual(store.effective_difficulty, Decimal("4.0"))

    def test_effective_difficulty_cap_at_5(self):
        store = Store(
            name="テスト店舗",
            base_difficulty=Decimal("4.5"),
            has_controlled_medical_device=True,  # +0.5
            has_toxic_substances=True,  # +0.5
            has_workers_comp=True,  # +0.3
        )
        self.assertEqual(store.effective_difficulty, Decimal("5.0"))

    def test_active_flag_count(self):
        store = Store(
            name="テスト店舗",
            has_controlled_medical_device=True,
            has_workers_comp=True,
            has_holiday_rules=True,
        )
        self.assertEqual(store.active_flag_count, 3)
