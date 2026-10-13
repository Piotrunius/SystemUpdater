import io
import unittest
from unittest.mock import patch

from main import latest_homebrew_version


class VersionTests(unittest.TestCase):
    @patch("main.urllib.request.urlopen")
    def test_homebrew_version_comes_from_upstream_formula(self, urlopen):
        urlopen.return_value = io.BytesIO(
            b'class Systemupdater\n  version "0.1.4"\nend\n'
        )

        self.assertEqual(latest_homebrew_version(), "0.1.4")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 8)

    @patch("main.urllib.request.urlopen", side_effect=OSError("offline"))
    def test_homebrew_version_is_unavailable_when_upstream_cannot_be_read(
        self, _urlopen
    ):
        self.assertIsNone(latest_homebrew_version())

    @patch("main.urllib.request.urlopen")
    def test_homebrew_version_rejects_unexpected_formula_contents(self, urlopen):
        urlopen.return_value = io.BytesIO(
            b'class Systemupdater\n  desc "No version field"\nend\n'
        )

        self.assertIsNone(latest_homebrew_version())

    @patch("main.latest_upstream_version", return_value="1.4.0")
    @patch("main.git_output", return_value="v1.4.0")
    @patch("main.is_homebrew_install", return_value=False)
    def test_version_action_renders_status_line_and_omits_durations(
        self, _is_brew, _git_out, _latest_ver
    ):
        import argparse

        from main import VersionAction

        parser = argparse.ArgumentParser()
        parser.add_argument("--version", action=VersionAction, nargs=0)

        out = io.StringIO()
        with patch("sys.stdout", out), self.assertRaises(SystemExit):
            parser.parse_args(["--version"])

        rendered = out.getvalue()
        self.assertIn("Installed version: 1.4.0", rendered)
        self.assertIn("Latest version: 1.4.0", rendered)
        self.assertIn("Status: up to date", rendered)
        self.assertNotIn("(0.1s)", rendered)
        self.assertNotIn("s)", rendered)

    @patch("main.latest_upstream_version", return_value="1.4.0")
    @patch("main.git_output", return_value="v1.4.0")
    @patch("main.is_homebrew_install", return_value=False)
    def test_version_action_recognizes_same_version_as_up_to_date(
        self, _is_brew, _git_out, _latest_ver
    ):
        import argparse

        from main import VersionAction

        parser = argparse.ArgumentParser()
        parser.add_argument("--version", action=VersionAction, nargs=0)

        out = io.StringIO()
        with patch("sys.stdout", out), self.assertRaises(SystemExit):
            parser.parse_args(["--version"])

        rendered = out.getvalue()
        self.assertIn("Status: up to date", rendered)

    @patch("main.latest_upstream_version", return_value="1.5.0")
    @patch("main.git_output", return_value="v1.4.0")
    @patch("main.is_homebrew_install", return_value=False)
    def test_version_action_recognizes_update_available_when_behind(
        self, _is_brew, _git_out, _latest_ver
    ):
        import argparse

        from main import VersionAction

        parser = argparse.ArgumentParser()
        parser.add_argument("--version", action=VersionAction, nargs=0)

        out = io.StringIO()
        with patch("sys.stdout", out), self.assertRaises(SystemExit):
            parser.parse_args(["--version"])

        rendered = out.getvalue()
        self.assertIn("Installed version: 1.4.0", rendered)
        self.assertIn("Latest version: 1.5.0", rendered)
        self.assertIn("Status: update available", rendered)


if __name__ == "__main__":
    unittest.main()
