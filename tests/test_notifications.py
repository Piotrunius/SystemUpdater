import unittest
from unittest.mock import patch

from notifications import send_notification


class NotificationTests(unittest.TestCase):
    def test_send_notification_linux_success(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("shutil.which", return_value="/usr/bin/notify-send"),
            patch(
                "subprocess.run",
                return_value=unittest.mock.Mock(returncode=0),
            ) as mock_run,
        ):
            ok = send_notification("Update Complete", "10 packages updated")
            self.assertTrue(ok)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertEqual(args[0], "/usr/bin/notify-send")
            self.assertIn("Update Complete", args)
            self.assertIn("10 packages updated", args)

    def test_send_notification_linux_not_installed(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("shutil.which", return_value=None),
        ):
            ok = send_notification("Update Complete", "10 packages updated")
            self.assertFalse(ok)

    def test_send_notification_darwin_success(self):
        with (
            patch("platform.system", return_value="Darwin"),
            patch("shutil.which", return_value="/usr/bin/osascript"),
            patch(
                "subprocess.run",
                return_value=unittest.mock.Mock(returncode=0),
            ) as mock_run,
        ):
            ok = send_notification("Update Complete", "All good")
            self.assertTrue(ok)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertEqual(args[0], "/usr/bin/osascript")

    def test_send_notification_unsupported_platform(self):
        with patch("platform.system", return_value="Windows"):
            ok = send_notification("Update Complete", "All good")
            self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
