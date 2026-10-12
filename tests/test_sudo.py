import unittest
from unittest.mock import patch

import sudo


class SudoTests(unittest.TestCase):
    @patch("os.geteuid", return_value=0)
    def test_root_user_returns_true_immediately(self, mock_euid):
        self.assertTrue(sudo.init_sudo())

    @patch("os.geteuid", return_value=1000)
    @patch("sudo.is_sudo_active", return_value=True)
    def test_already_active_sudo_starts_keeper_and_returns_true(
        self, mock_active, mock_euid
    ):
        with patch("sudo.start_sudo_keeper") as mock_keeper:
            self.assertTrue(sudo.init_sudo())
            mock_keeper.assert_called_once()

    @patch("os.geteuid", return_value=1000)
    @patch("sudo.is_sudo_active", return_value=False)
    def test_non_interactive_returns_false_when_inactive(self, mock_active, mock_euid):
        self.assertFalse(sudo.init_sudo(interactive=False))

    @patch("os.geteuid", return_value=1000)
    @patch("sudo.is_sudo_active", return_value=False)
    @patch("subprocess.run")
    def test_interactive_keyboard_interrupt_propagates(
        self, mock_run, mock_active, mock_euid
    ):
        mock_run.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            sudo.init_sudo(interactive=True)


if __name__ == "__main__":
    unittest.main()
