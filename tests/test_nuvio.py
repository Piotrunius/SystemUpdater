import unittest
from unittest.mock import patch

from modules.nuvio import NuvioModule


class NuvioAssetTests(unittest.TestCase):
    def test_rpm_asset_selection_matches_host_architecture(self):
        assets = [
            {"name": "Nuvio-linux-aarch64.rpm", "browser_download_url": "arm-url"},
            {"name": "Nuvio-linux-x86_64.rpm", "browser_download_url": "x86-url"},
        ]

        with patch("platform.machine", return_value="x86_64"):
            url, _ = NuvioModule()._find_rpm_asset(assets)

        self.assertEqual(url, "x86-url")

    def test_does_not_select_an_explicitly_incompatible_rpm_asset(self):
        assets = [
            {"name": "Nuvio-linux-aarch64.rpm", "browser_download_url": "arm-url"},
        ]

        with patch("platform.machine", return_value="x86_64"):
            url, _ = NuvioModule()._find_rpm_asset(assets)

        self.assertIsNone(url)

    def test_selects_a_single_architecture_neutral_rpm_asset(self):
        assets = [
            {"name": "NuvioDesktop.rpm", "browser_download_url": "generic-url"},
        ]

        with patch("platform.machine", return_value="x86_64"):
            url, _ = NuvioModule()._find_rpm_asset(assets)

        self.assertEqual(url, "generic-url")


if __name__ == "__main__":
    unittest.main()
