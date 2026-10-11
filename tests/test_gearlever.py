import unittest
import urllib.error
from unittest.mock import Mock, patch

from modules.base import UpdateContext
from modules.gearlever import GearLeverModule
from modules.nobara import parse_dnf_packages
from modules.proton import ProtonPlusModule


class GearLeverAndGitHubTests(unittest.TestCase):
    def test_parse_dnf_packages_with_epoch_replacements(self):
        output = """
Package                     Arch   Version         Repository          Size
Upgrading:
 nobara-updater             noarch 0:2.0.1-75.fc44 nobara-updates   1.0 MiB
   replacing nobara-updater noarch 0:2.0.1-72.fc44 nobara-updates   1.0 MiB

Transaction Summary:
 Upgrading:          1 package
 Replacing:          1 package
"""
        packages = parse_dnf_packages(output)
        self.assertEqual(
            packages, ["nobara-updater: 2.0.1-72.fc44 -> 2.0.1-75.fc44"]
        )

    @patch("modules.base.urllib.request.urlopen")
    def test_gearlever_skips_when_github_api_rate_limited(self, mock_urlopen):
        # Simulate GitHub 403 rate limit
        error = urllib.error.HTTPError(
            url="https://api.github.com/",
            code=403,
            msg="rate limit exceeded",
            hdrs={"x-ratelimit-remaining": "0"},
            fp=None,
        )
        mock_urlopen.side_effect = error

        context = UpdateContext()
        context.run_cmd = Mock()

        result = GearLeverModule().run(context)

        self.assertEqual(result.status, "warning")
        self.assertIn("GitHub API rate limit reached", result.message)
        # Should not have called flatpak at all
        context.run_cmd.assert_not_called()

    @patch("modules.base.urllib.request.urlopen")
    def test_gearlever_skips_when_github_api_unreachable(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        context = UpdateContext()
        context.run_cmd = Mock()

        result = GearLeverModule().run(context)

        self.assertEqual(result.status, "warning")
        self.assertIn("GitHub API unreachable or timed out", result.message)
        context.run_cmd.assert_not_called()

    @patch("modules.base.urllib.request.urlopen")
    def test_gearlever_detects_rate_limit_in_command_output(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.headers = {"x-ratelimit-remaining": "50"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        context = UpdateContext()
        context.run_cmd = Mock(
            return_value=(
                0,
                '403 Client Error: rate limit exceeded for url: https://api.github.com/repos/...\n{"schema_version": 1, "updates": []}',
                "",
            )
        )

        result = GearLeverModule().run(context)

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.message, "GitHub API rate limit reached")

    @patch("modules.base.urllib.request.urlopen")
    def test_gearlever_successful_update_with_json(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.headers = {"x-ratelimit-remaining": "50"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        context = UpdateContext()
        context.run_cmd = Mock(
            side_effect=[
                (
                    0,
                    '{"schema_version": 1, "updates": [{"name": "Steam Art Manager"}]}',
                    "",
                ),
                (0, "Updated successfully", ""),
            ]
        )

        result = GearLeverModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 appimage updated")
        self.assertEqual(result.details, ["Steam Art Manager"])

    @patch("modules.base.urllib.request.urlopen")
    def test_protonplus_skips_when_github_api_rate_limited(self, mock_urlopen):
        error = urllib.error.HTTPError(
            url="https://api.github.com/",
            code=403,
            msg="rate limit exceeded",
            hdrs={"x-ratelimit-remaining": "0"},
            fp=None,
        )
        mock_urlopen.side_effect = error

        context = UpdateContext()
        context.run_cmd = Mock()

        result = ProtonPlusModule().run(context)

        self.assertEqual(result.status, "warning")
        self.assertIn("GitHub API rate limit reached", result.message)
        context.run_cmd.assert_not_called()

    @patch("modules.base.urllib.request.urlopen")
    def test_gearlever_formats_version_changes_when_present(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.headers = {"x-ratelimit-remaining": "50"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        context = UpdateContext()
        context.run_cmd = Mock(
            side_effect=[
                (
                    0,
                    '{"schema_version": 1, "updates": [{"name": "App", "current_version": "1.0", "available_version": "2.0"}]}',
                    "",
                ),
                (0, "Updated", ""),
            ]
        )

        result = GearLeverModule().run(context)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.details, ["App: 1.0 -> 2.0"])

    def test_skills_ignores_summary_count_line(self):
        from modules.devtools import SkillsModule

        context = UpdateContext()
        raw_output = """Checking for skill updates…
Updating cloudflare…
  ✓ Updated cloudflare
✓ Updated 1 skill(s)
"""
        context.run_cmd = Mock(return_value=(0, raw_output, ""))
        result = SkillsModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 skill updated")
        self.assertEqual(result.details, ["cloudflare"])

    def test_skills_formats_old_and_new_hash(self):
        from modules.devtools import SkillsModule

        context = UpdateContext()
        raw_output = """Checking for skill updates…
Updating cloudflare…
  ✓ Updated cloudflare
✓ Updated 1 skill(s)
"""
        context.run_cmd = Mock(return_value=(0, raw_output, ""))
        mod = SkillsModule()
        mod._read_skill_hashes = Mock(
            side_effect=[
                {"cloudflare": "1a76dad"},
                {"cloudflare": "8206f3f"},
            ]
        )
        result = mod.run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 skill updated")
        self.assertEqual(result.details, ["cloudflare: 1a76dad -> 8206f3f"])

    def test_docker_formats_old_and_new_image_id(self):
        from modules.docker import DockerModule

        context = UpdateContext()
        context.run_cmd = Mock(
            side_effect=[
                (0, "ghcr.io/pelican/panel:latest\t44136fa355b3", ""),
                (
                    0,
                    "Digest: sha256:6d895cfb3a7cc8b939eda4f7f3cba5c45b569cd9532dad6e8da32cba76285654\nStatus: Downloaded newer image",
                    "",
                ),
            ]
        )
        result = DockerModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(
            result.details,
            ["ghcr.io/pelican/panel:latest: 44136fa355b3 -> 6d895cfb3a7c"],
        )

    def test_docker_recreates_compose_service_on_image_update(self):
        from modules.docker import DockerModule

        context = UpdateContext()
        commands_run = []

        def mock_run(cmd, **kwargs):
            commands_run.append(cmd)
            if "images" in cmd:
                return (0, "ghcr.io/pelican/panel:latest\t44136fa355b3", "")
            if "pull" in cmd:
                return (
                    0,
                    "Digest: sha256:6d895cfb3a7cc8b939eda4f7f3cba5c45b569cd9532dad6e8da32cba76285654\nStatus: Downloaded newer image",
                    "",
                )
            if "ps" in cmd:
                return (
                    0,
                    "ghcr.io/pelican/panel:latest\t/opt/pelican/docker-compose.yml\t/opt/pelican\n",
                    "",
                )
            if "compose" in cmd:
                return (0, "[+] up 1/1\n ✔ Container pelican-panel-1 Recreated", "")
            return (0, "", "")

        context.run_cmd = Mock(side_effect=mock_run)
        result = DockerModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(
            result.details,
            ["ghcr.io/pelican/panel:latest: 44136fa355b3 -> 6d895cfb3a7c"],
        )
        self.assertTrue(
            any("compose" in cmd and "up" in cmd for cmd in commands_run),
            "Expected docker compose up -d to be executed",
        )


if __name__ == "__main__":
    unittest.main()
