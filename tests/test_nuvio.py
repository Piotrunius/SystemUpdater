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
        self.addCleanup(http_err.close)

        with (
            patch.object(module, "_get_installed_tag", return_value="0.1.0-alpha"),
            patch.object(module, "_get_github_token", return_value="fake_token"),
            patch.object(module, "_fetch_latest_release", side_effect=http_err),
        ):
            result = module.run(context)
            self.assertEqual(result.status, "warning")
            self.assertEqual(result.message, "GitHub API rate limit reached")

    def test_nuvio_reapply_patch_returns_clean_updated_status(self):
        from modules.base import UpdateContext

        context = UpdateContext()
        module = NuvioModule()

        with (
            patch.object(module, "_get_installed_tag", return_value="0.1.33-alpha"),
            patch.object(module, "_get_github_token", return_value="token"),
            patch.object(
                module,
                "_fetch_latest_release",
                return_value={"tag_name": "0.1.33-alpha"},
            ),
            patch.object(module, "_find_target_jar", return_value="/fake/jar"),
            patch.object(module, "_ensure_patched", return_value=True),
        ):
            result = module.run(context)
            self.assertEqual(result.status, "ok")
            self.assertEqual(result.message, "updated")


class NuvioBytecodePatchTests(unittest.TestCase):
    def test_patch_bytecode_transforms_is_windows_check(self):
        # Sample bytecode simulating AsyncImage_desktopKt.<clinit> with trailing instructions
        prefix = b"\x13\x02\x8c\xb8\x02\x92\x4b\x2a\xc6\x00\x0e\x2a\x13\x02\x94"
        pattern_target = b"\x04\xb8\x02\x9a\xa7\x00\x04\x03\xb3\x01\x17"
        trailing = b"\xba\x02\xa0\x00\x00\xb1"
        raw_code = bytearray(prefix + pattern_target + trailing)

        module = NuvioModule()
        patched = module._patch_bytecode(raw_code)

        expected_patch = b"\x57\x57\x00\x00\x00\x00\x00\x04\xb3\x01\x17"
        self.assertIn(expected_patch, patched)
        self.assertTrue(patched.endswith(trailing))

    def test_patch_bytecode_idempotent_when_already_patched(self):
        module = NuvioModule()
        already_patched = bytearray(b"\x00\x12\x57\x57\x00\x00\x00\x00\x00\x04\xb3\x99")
        result = module._patch_bytecode(already_patched)
        self.assertEqual(result, already_patched)

    def test_patch_bytecode_raises_when_pattern_not_found(self):
        module = NuvioModule()
        invalid_bytes = bytearray(b"\x00\x01\x02\x03\xb1")
        with self.assertRaises(ValueError) as ctx:
            module._patch_bytecode(invalid_bytes)
        self.assertIn("Could not locate", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
