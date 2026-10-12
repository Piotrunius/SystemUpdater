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

    def test_nuvio_skips_when_no_token_and_github_rate_limited(self):
        from modules.base import UpdateContext
        from ui import StepResult

        context = UpdateContext()
        module = NuvioModule()

        with (
            patch.object(module, "_get_installed_tag", return_value="0.1.0-alpha"),
            patch.object(module, "_get_github_token", return_value=None),
            patch(
                "modules.nuvio.check_github_api",
                return_value=StepResult("warning", "GitHub API rate limit reached"),
            ),
        ):
            result = module.run(context)
            self.assertEqual(result.status, "warning")
            self.assertIn("GitHub API rate limit reached", result.message)

    def test_nuvio_handles_http_403_rate_limit_exception(self):
        import urllib.error

        from modules.base import UpdateContext

        context = UpdateContext()
        module = NuvioModule()

        from email.message import Message

        headers = Message()
        headers["x-ratelimit-remaining"] = "0"
        http_err = urllib.error.HTTPError(
            url="https://api.github.com/...",
            code=403,
            msg="rate limit exceeded",
            hdrs=headers,
            fp=None,
        )

        with (
            patch.object(module, "_get_installed_tag", return_value="0.1.0-alpha"),
            patch.object(module, "_get_github_token", return_value="fake_token"),
            patch.object(module, "_fetch_latest_release", side_effect=http_err),
        ):
            result = module.run(context)
            self.assertEqual(result.status, "warning")
            self.assertEqual(result.message, "GitHub API rate limit reached")


if __name__ == "__main__":
    unittest.main()
