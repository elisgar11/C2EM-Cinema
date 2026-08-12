from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class DefaultAdminBootstrapTests(TestCase):
    def test_creates_default_admin_with_requested_credentials(self):
        with patch.dict(
            "os.environ",
            {
                "DEFAULT_ADMIN_ENABLED": "true",
                "DEFAULT_ADMIN_USERNAME": "admin",
                "DEFAULT_ADMIN_PASSWORD": "admin",
                "DEFAULT_ADMIN_EMAIL": "admin@localhost",
            },
            clear=False,
        ):
            call_command("ensure_default_admin", stdout=StringIO())

        user = get_user_model().objects.get(username="admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("admin"))

    def test_existing_admin_password_is_not_reset_on_restart(self):
        User = get_user_model()
        user = User.objects.create_superuser("admin", "admin@localhost", "changed-password")

        with patch.dict(
            "os.environ",
            {
                "DEFAULT_ADMIN_ENABLED": "true",
                "DEFAULT_ADMIN_USERNAME": "admin",
                "DEFAULT_ADMIN_PASSWORD": "admin",
            },
            clear=False,
        ):
            call_command("ensure_default_admin", stdout=StringIO())

        user.refresh_from_db()
        self.assertTrue(user.check_password("changed-password"))
        self.assertFalse(user.check_password("admin"))

    def test_can_disable_default_admin_creation(self):
        with patch.dict("os.environ", {"DEFAULT_ADMIN_ENABLED": "false"}, clear=False):
            call_command("ensure_default_admin", stdout=StringIO())

        self.assertFalse(get_user_model().objects.filter(username="admin").exists())
