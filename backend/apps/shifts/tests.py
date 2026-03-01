from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.staff.models import Staff
from apps.stores.models import Store

from .models import Shift, ShiftPeriod
from .validators import (
    validate_managing_pharmacist_store,
    validate_monthly_working_days,
    validate_no_double_booking,
    validate_store_minimum_staffing,
)


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


class StoreMinimumStaffingTest(TestCase):
    def setUp(self):
        self.store = Store.objects.create(name="テスト店舗A", min_pharmacists=1)
        self.store_b = Store.objects.create(name="テスト店舗B", min_pharmacists=1)
        self.period = ShiftPeriod.objects.create(
            start_date=date(2026, 2, 16),
            end_date=date(2026, 3, 15),
            request_deadline=date(2026, 2, 1),
        )
        # Managing pharmacist at store A
        self.managing = Staff.objects.create(
            name="管理薬剤師A",
            role=Staff.Role.MANAGING_PHARMACIST,
            store=self.store,
        )
        # Second pharmacist at store A
        self.pharmacist = Staff.objects.create(
            name="薬剤師B",
            role=Staff.Role.PHARMACIST,
            store=self.store,
        )
        # Rounder (no home store)
        self.rounder = Staff.objects.create(
            name="ラウンダーA",
            role=Staff.Role.PHARMACIST,
            store=None,
            is_rounder=True,
        )
        # Clerk at store A
        self.clerk = Staff.objects.create(
            name="事務員A",
            role=Staff.Role.CLERK,
            store=self.store,
        )

    def test_error_when_below_minimum(self):
        """Store with min_pharmacists=1: if the only pharmacist leaves, error."""
        # Only managing pharmacist at store; pharmacist_b takes leave
        # Give pharmacist_b a leave shift (away from store A)
        Shift.objects.create(
            staff=self.pharmacist,
            shift_period=self.period,
            date=date(2026, 2, 20),
            store=None,
            shift_type=Shift.ShiftType.FULL,
            leave_type=Shift.LeaveType.PAID,
        )
        # Now managing pharmacist tries to leave too — should fail
        with self.assertRaises(ValidationError):
            validate_store_minimum_staffing(
                self.managing, date(2026, 2, 20), None, Shift.ShiftType.FULL
            )

    def test_ok_when_above_minimum(self):
        """Store with min_pharmacists=1: one pharmacist remains, OK."""
        # pharmacist_b is working at store A
        Shift.objects.create(
            staff=self.pharmacist,
            shift_period=self.period,
            date=date(2026, 2, 20),
            store=self.store,
            shift_type=Shift.ShiftType.FULL,
        )
        # Managing pharmacist can leave since pharmacist_b remains
        validate_store_minimum_staffing(
            self.managing, date(2026, 2, 20), None, Shift.ShiftType.FULL
        )

    def test_rounder_not_affected(self):
        """Rounders (store=None) are not subject to minimum staffing check."""
        # Should not raise regardless of store staffing
        validate_store_minimum_staffing(
            self.rounder, date(2026, 2, 20), self.store_b, Shift.ShiftType.FULL
        )

    def test_clerk_not_affected(self):
        """Clerks are not subject to pharmacist minimum staffing check."""
        # Even if no pharmacists remain, clerk leaving should not raise
        Shift.objects.create(
            staff=self.managing,
            shift_period=self.period,
            date=date(2026, 2, 20),
            store=None,
            shift_type=Shift.ShiftType.FULL,
            leave_type=Shift.LeaveType.PAID,
        )
        Shift.objects.create(
            staff=self.pharmacist,
            shift_period=self.period,
            date=date(2026, 2, 20),
            store=None,
            shift_type=Shift.ShiftType.FULL,
            leave_type=Shift.LeaveType.PAID,
        )
        validate_store_minimum_staffing(
            self.clerk, date(2026, 2, 20), None, Shift.ShiftType.FULL
        )


class MonthlyWorkingDaysTest(TestCase):
    def setUp(self):
        self.store = Store.objects.create(name="テスト店舗A")
        self.period = ShiftPeriod.objects.create(
            start_date=date(2026, 2, 16),
            end_date=date(2026, 3, 15),
            request_deadline=date(2026, 2, 1),
        )
        self.staff = Staff.objects.create(
            name="薬剤師A",
            role=Staff.Role.PHARMACIST,
            monthly_working_days=3,  # Very low limit for testing
        )

    def test_error_when_exceeding_monthly_limit(self):
        """Error when working days exceed monthly limit."""
        # Create 3 working shifts (at the limit)
        for i in range(3):
            Shift.objects.create(
                staff=self.staff,
                shift_period=self.period,
                date=date(2026, 2, 16) + timedelta(days=i),
                store=self.store,
                shift_type=Shift.ShiftType.FULL,
            )
        # 4th working day should fail
        with self.assertRaises(ValidationError):
            validate_monthly_working_days(
                self.staff,
                date(2026, 2, 19),
                self.period,
                None,  # Not leave
            )

    def test_leave_shifts_not_counted(self):
        """Leave shifts do not count toward working day limit."""
        # Create 3 working shifts (at the limit)
        for i in range(3):
            Shift.objects.create(
                staff=self.staff,
                shift_period=self.period,
                date=date(2026, 2, 16) + timedelta(days=i),
                store=self.store,
                shift_type=Shift.ShiftType.FULL,
            )
        # Adding a leave shift should NOT raise
        validate_monthly_working_days(
            self.staff,
            date(2026, 2, 19),
            self.period,
            Shift.LeaveType.PAID,
        )

    def test_morning_afternoon_counts_as_one_day(self):
        """Morning + afternoon on same date = 1 working day."""
        # Day 1: morning + afternoon (1 day)
        Shift.objects.create(
            staff=self.staff,
            shift_period=self.period,
            date=date(2026, 2, 16),
            store=self.store,
            shift_type=Shift.ShiftType.MORNING,
        )
        Shift.objects.create(
            staff=self.staff,
            shift_period=self.period,
            date=date(2026, 2, 16),
            store=self.store,
            shift_type=Shift.ShiftType.AFTERNOON,
        )
        # Day 2 and Day 3 (2 more days)
        Shift.objects.create(
            staff=self.staff,
            shift_period=self.period,
            date=date(2026, 2, 17),
            store=self.store,
            shift_type=Shift.ShiftType.FULL,
        )
        Shift.objects.create(
            staff=self.staff,
            shift_period=self.period,
            date=date(2026, 2, 18),
            store=self.store,
            shift_type=Shift.ShiftType.FULL,
        )
        # 4th day should fail (total distinct dates = 3 already at limit)
        with self.assertRaises(ValidationError):
            validate_monthly_working_days(
                self.staff,
                date(2026, 2, 19),
                self.period,
                None,
            )

    def test_employment_type_default(self):
        """Verify employment type defaults for effective_monthly_working_days."""
        full_time = Staff(employment_type=Staff.EmploymentType.FULL_TIME)
        self.assertEqual(full_time.effective_monthly_working_days, 22)

        part_time = Staff(employment_type=Staff.EmploymentType.PART_TIME)
        self.assertEqual(part_time.effective_monthly_working_days, 15)

        dispatch = Staff(employment_type=Staff.EmploymentType.DISPATCH)
        self.assertEqual(dispatch.effective_monthly_working_days, 20)

    def test_explicit_override(self):
        """Explicit monthly_working_days overrides employment type default."""
        staff = Staff(
            employment_type=Staff.EmploymentType.FULL_TIME,
            monthly_working_days=18,
        )
        self.assertEqual(staff.effective_monthly_working_days, 18)
