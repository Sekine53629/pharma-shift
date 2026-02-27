from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.staff.models import Staff
from apps.stores.models import Store

from .models import Shift, ShiftPeriod
from .validators import validate_managing_pharmacist_store, validate_no_double_booking


class DoubleBookingTest(TestCase):
    def setUp(self):
        self.store = Store.objects.create(name="テスト店舗A")
        self.store_b = Store.objects.create(name="テスト店舗B")
        self.period = ShiftPeriod.objects.create(
            start_date=date(2026, 2, 16),
            end_date=date(2026, 3, 15),
            request_deadline=date(2026, 2, 1),
        )
        self.staff = Staff.objects.create(
            name="薬剤師A",
            role=Staff.Role.PHARMACIST,
        )

    def test_full_shift_prevents_double_booking(self):
        Shift.objects.create(
            staff=self.staff,
            shift_period=self.period,
            date=date(2026, 2, 20),
            store=self.store,
            shift_type=Shift.ShiftType.FULL,
        )
        with self.assertRaises(ValidationError):
            validate_no_double_booking(
                self.staff, date(2026, 2, 20), Shift.ShiftType.FULL
            )

    def test_morning_afternoon_allowed(self):
        Shift.objects.create(
            staff=self.staff,
            shift_period=self.period,
            date=date(2026, 2, 20),
            store=self.store,
            shift_type=Shift.ShiftType.MORNING,
        )
        # afternoon should not raise
        validate_no_double_booking(
            self.staff, date(2026, 2, 20), Shift.ShiftType.AFTERNOON
        )

    def test_same_half_day_raises(self):
        Shift.objects.create(
            staff=self.staff,
            shift_period=self.period,
            date=date(2026, 2, 20),
            store=self.store,
            shift_type=Shift.ShiftType.MORNING,
        )
        with self.assertRaises(ValidationError):
            validate_no_double_booking(
                self.staff, date(2026, 2, 20), Shift.ShiftType.MORNING
            )


class ManagingPharmacistTest(TestCase):
    def setUp(self):
        self.store = Store.objects.create(name="テスト店舗A")
        self.store_b = Store.objects.create(name="テスト店舗B")
        self.managing = Staff.objects.create(
            name="管理薬剤師",
            role=Staff.Role.MANAGING_PHARMACIST,
            store=self.store,
        )

    def test_managing_pharmacist_cannot_work_at_other_store(self):
        with self.assertRaises(ValidationError):
            validate_managing_pharmacist_store(self.managing, self.store_b)

    def test_managing_pharmacist_can_work_at_own_store(self):
        # Should not raise
        validate_managing_pharmacist_store(self.managing, self.store)
