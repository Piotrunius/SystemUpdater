import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

from modules.containers_ext import PodmanModule, VagrantModule
from modules.devtools import (
    AntigravityModule,
    BunModule,
    CargoUpdateModule,
    GemModule,
    GhExtensionsModule,
    MicroModule,
    NpmModule,
    PipxModule,
    PnpmModule,
    RustupModule,
    SkillsModule,
)
from modules.distrobox import DistroboxModule
from modules.docker import DockerModule


class FakeContext:
    def __init__(self, output="", error="", return_code=0, installed=True):
        self.output = output
        self.error = error
        self.return_code = return_code
        self.installed = installed

    def which(self, _binary):
        return "/usr/bin/tool" if self.installed else None

    def run_cmd(self, *_args, **_kwargs):
        return self.return_code, self.output, self.error


class ModuleAvailabilityTests(unittest.TestCase):
    def test_docker_requires_daemon_and_local_images(self):
        module = DockerModule()

        self.assertFalse(module.is_available(FakeContext(output="")))
        self.assertFalse(module.is_available(FakeContext(output="<none>:<none>\n")))
        self.assertTrue(module.is_available(FakeContext(output="example/app:latest\n")))
        unavailable = FakeContext(output="", return_code=1)
        self.assertTrue(module.is_available(unavailable))
        self.assertEqual(module.availability_status(unavailable), "[Unavailable]")
        self.assertFalse(module.is_available(FakeContext(installed=False)))

    def test_vagrant_requires_a_project_in_or_above_current_directory(self):
        module = VagrantModule()
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            nested = project / "nested"
            nested.mkdir(parents=True)
            with patch("modules.containers_ext.os.getcwd", return_value=str(nested)):
                self.assertFalse(module.is_available(FakeContext()))
                self.assertEqual(
                    module.availability_status(FakeContext()), "[No Project]"
                )
                (project / "Vagrantfile").touch()
                self.assertTrue(module.is_available(FakeContext()))
                self.assertFalse(module.is_available(FakeContext(installed=False)))

    def test_distrobox_requires_at_least_one_listed_container(self):
        module = DistroboxModule()
        header = "ID | NAME | STATUS | IMAGE\n"

        self.assertFalse(module.is_available(FakeContext(output=header)))
        self.assertTrue(
            module.is_available(
                FakeContext(output=header + "abc | dev | Up | fedora:latest\n")
            )
        )
        unavailable = FakeContext(output=header, return_code=1)
        self.assertTrue(module.is_available(unavailable))
        self.assertEqual(module.availability_status(unavailable), "[Unavailable]")

    def test_podman_distinguishes_empty_targets_from_probe_errors(self):
        module = PodmanModule()

        self.assertFalse(module.is_available(FakeContext(output="")))
        self.assertEqual(
            module.availability_status(FakeContext(output="")), "[No Targets]"
        )
        unavailable = FakeContext(return_code=1)
        self.assertTrue(module.is_available(unavailable))
        self.assertEqual(module.availability_status(unavailable), "[Unavailable]")

    def test_bun_and_pnpm_report_missing_global_packages_as_no_targets(self):
        bun = BunModule()
        pnpm = PnpmModule()

        self.assertFalse(
            bun.is_available(
                FakeContext(
                    error="error: No package.json was found for directory global",
                    return_code=1,
                )
            )
        )
        self.assertEqual(
            bun.availability_status(
                FakeContext(
                    error="error: No package.json was found for directory global",
                    return_code=1,
                )
            ),
            "[No Targets]",
        )
        self.assertFalse(
            pnpm.is_available(FakeContext(output="No global packages found"))
        )
        self.assertEqual(
            pnpm.availability_status(FakeContext(output="No global packages found")),
            "[No Targets]",
        )
        self.assertTrue(bun.is_available(FakeContext(output="cowsay 1.6.0")))
        self.assertTrue(
            pnpm.is_available(FakeContext(output="Package | Version\nfoo | 1.0.0"))
        )
        probe_error = FakeContext(error="registry is unavailable", return_code=1)
        self.assertTrue(bun.is_available(probe_error))
        self.assertEqual(bun.availability_status(probe_error), "[Unavailable]")

    def test_gh_extensions_requires_installed_extensions(self):
        gh = GhExtensionsModule()
        with patch("modules.devtools.os.path.isdir", return_value=False):
            self.assertFalse(
                gh.is_available(FakeContext(output="no installed extensions found\n"))
            )
            self.assertEqual(
                gh.availability_status(
                    FakeContext(output="no installed extensions found\n")
                ),
                "[No Targets]",
            )
            self.assertTrue(
                gh.is_available(
                    FakeContext(output="cli/gh-copilot\tCopilot extension\n")
                )
            )
            self.assertEqual(
                gh.availability_status(
                    FakeContext(output="cli/gh-copilot\tCopilot extension\n")
                ),
                "[Active]",
            )
        self.assertFalse(gh.is_available(FakeContext(installed=False)))
        self.assertEqual(
            gh.availability_status(FakeContext(installed=False)), "[Not Installed]"
        )

    def test_micro_plugins_requires_custom_plugins(self):
        micro = MicroModule()
        with patch("modules.devtools.os.path.isdir", return_value=False):
            builtin_only = "autoclose (built-in)\ncomment (built-in)\n"
            self.assertFalse(micro.is_available(FakeContext(output=builtin_only)))
            self.assertEqual(
                micro.availability_status(FakeContext(output=builtin_only)),
                "[No Targets]",
            )
            custom = "myplugin 1.0.0\nautoclose (built-in)\n"
            self.assertTrue(micro.is_available(FakeContext(output=custom)))
            self.assertEqual(
                micro.availability_status(FakeContext(output=custom)), "[Active]"
            )
        self.assertFalse(micro.is_available(FakeContext(installed=False)))
        self.assertEqual(
            micro.availability_status(FakeContext(installed=False)), "[Not Installed]"
        )

    def test_skills_requires_skills_in_lock_or_directory(self):
        skills = SkillsModule()
        with patch("modules.devtools.os.path.isdir", return_value=False):
            empty_data = json.dumps({"version": 3, "skills": {}})
            with (
                patch("builtins.open", mock_open(read_data=empty_data)),
                patch("modules.devtools.os.path.isfile", return_value=True),
            ):
                self.assertFalse(skills.is_available(FakeContext()))
                self.assertEqual(
                    skills.availability_status(FakeContext()), "[No Targets]"
                )

            active_data = json.dumps(
                {"version": 3, "skills": {"cloudflare": {"source": "foo"}}}
            )
            with (
                patch("builtins.open", mock_open(read_data=active_data)),
                patch("modules.devtools.os.path.isfile", return_value=True),
            ):
                self.assertTrue(skills.is_available(FakeContext()))
                self.assertEqual(skills.availability_status(FakeContext()), "[Active]")

        self.assertFalse(skills.is_available(FakeContext(installed=False)))
        self.assertEqual(
            skills.availability_status(FakeContext(installed=False)), "[Not Installed]"
        )

    def test_antigravity_requires_extensions(self):
        ag = AntigravityModule()
        with patch("modules.devtools.os.path.isdir", return_value=False):
            self.assertFalse(ag.is_available(FakeContext(output="")))
            self.assertEqual(
                ag.availability_status(FakeContext(output="")), "[No Targets]"
            )
            self.assertTrue(
                ag.is_available(FakeContext(output="golang.go\nmeta.pyrefly\n"))
            )
            self.assertEqual(
                ag.availability_status(FakeContext(output="golang.go\nmeta.pyrefly\n")),
                "[Active]",
            )
        self.assertFalse(ag.is_available(FakeContext(installed=False)))
        self.assertEqual(
            ag.availability_status(FakeContext(installed=False)), "[Not Installed]"
        )

    def test_npm_requires_global_packages(self):
        npm = NpmModule()
        npm_only = json.dumps(
            {"name": "lib", "dependencies": {"npm": {"version": "10.0"}}}
        )
        self.assertFalse(npm.is_available(FakeContext(output=npm_only)))
        self.assertEqual(
            npm.availability_status(FakeContext(output=npm_only)), "[No Targets]"
        )

        with_pkgs = json.dumps(
            {"name": "lib", "dependencies": {"npm": {}, "eslint": {"version": "9.0"}}}
        )
        self.assertTrue(npm.is_available(FakeContext(output=with_pkgs)))
        self.assertEqual(
            npm.availability_status(FakeContext(output=with_pkgs)), "[Active]"
        )
        self.assertFalse(npm.is_available(FakeContext(installed=False)))
        self.assertEqual(
            npm.availability_status(FakeContext(installed=False)), "[Not Installed]"
        )

    def test_rustup_requires_toolchains(self):
        rustup = RustupModule()
        with patch("modules.devtools.os.path.isdir", return_value=False):
            self.assertFalse(
                rustup.is_available(
                    FakeContext(output="info: no installed toolchains\n")
                )
            )
            self.assertEqual(
                rustup.availability_status(
                    FakeContext(output="info: no installed toolchains\n")
                ),
                "[No Targets]",
            )
            self.assertTrue(
                rustup.is_available(
                    FakeContext(output="stable-x86_64-unknown-linux-gnu (default)\n")
                )
            )
            self.assertEqual(
                rustup.availability_status(
                    FakeContext(output="stable-x86_64-unknown-linux-gnu (default)\n")
                ),
                "[Active]",
            )
        self.assertFalse(rustup.is_available(FakeContext(installed=False)))
        self.assertEqual(
            rustup.availability_status(FakeContext(installed=False)), "[Not Installed]"
        )

    def test_gem_requires_custom_gems(self):
        gem = GemModule()
        default_only = (
            "*** LOCAL GEMS ***\nbundler (default: 4.0.20)\njson (default: 2.18.0)\n"
        )
        self.assertFalse(gem.is_available(FakeContext(output=default_only)))
        self.assertEqual(
            gem.availability_status(FakeContext(output=default_only)), "[No Targets]"
        )

        with_custom = (
            "*** LOCAL GEMS ***\nbundler (default: 4.0.20)\ncommander (5.0.0)\n"
        )
        self.assertTrue(gem.is_available(FakeContext(output=with_custom)))
        self.assertEqual(
            gem.availability_status(FakeContext(output=with_custom)), "[Active]"
        )
        self.assertFalse(gem.is_available(FakeContext(installed=False)))
        self.assertEqual(
            gem.availability_status(FakeContext(installed=False)), "[Not Installed]"
        )


if __name__ == "__main__":
    unittest.main()
