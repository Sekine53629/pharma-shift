from django.test import TestCase

from .models import AuditLog, User


class UserModelTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            roles=["admin"],
        )
        self.sv_user = User.objects.create_user(
            email="sv@test.com",
            password="testpass123",
            roles=["supervisor"],
        )
        self.multi_role_user = User.objects.create_user(
            email="multi@test.com",
            password="testpass123",
            roles=["admin", "supervisor"],
        )

    def test_has_role(self):
        self.assertTrue(self.admin_user.has_role("admin"))
        self.assertFalse(self.admin_user.has_role("supervisor"))

    def test_has_any_role(self):
        self.assertTrue(self.admin_user.has_any_role("admin", "supervisor"))
        self.assertFalse(self.sv_user.has_any_role("admin", "store_manager"))

    def test_role_properties(self):
        self.assertTrue(self.admin_user.is_admin)
        self.assertFalse(self.admin_user.is_supervisor)
        self.assertTrue(self.sv_user.is_supervisor)

    def test_multi_role(self):
        self.assertTrue(self.multi_role_user.is_admin)
        self.assertTrue(self.multi_role_user.is_supervisor)

    def test_email_login(self):
        self.assertEqual(self.admin_user.USERNAME_FIELD, "email")
        self.assertEqual(str(self.admin_user), "admin@test.com")


class AuditLogTest(TestCase):
    def test_create_audit_log(self):
        user = User.objects.create_user(email="test@test.com", password="test123")
        log = AuditLog(
            user=user,
            action="create",
            table_name="stores",
            record_id=1,
            after_data={"name": "テスト店舗"},
        )
        log.save()
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_audit_log_no_update(self):
        user = User.objects.create_user(email="test@test.com", password="test123")
        log = AuditLog(user=user, action="create", table_name="stores")
        log.save()

        log.action = "modified"
        with self.assertRaises(ValueError):
            log.save()

    def test_audit_log_no_delete(self):
        user = User.objects.create_user(email="test@test.com", password="test123")
        log = AuditLog(user=user, action="create", table_name="stores")
        log.save()

        with self.assertRaises(ValueError):
            log.delete()
