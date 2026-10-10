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


if __name__ == "__main__":
    unittest.main()
