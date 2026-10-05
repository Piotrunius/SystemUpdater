import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.containers_ext import PodmanModule, VagrantModule
from modules.devtools import BunModule, PnpmModule
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
                self.assertEqual(module.availability_status(FakeContext()), "[No Project]")
                (project / "Vagrantfile").touch()
                self.assertTrue(module.is_available(FakeContext()))
                self.assertFalse(module.is_available(FakeContext(installed=False)))

    def test_distrobox_requires_at_least_one_listed_container(self):
        module = DistroboxModule()
        header = "ID | NAME | STATUS | IMAGE\n"

        self.assertFalse(module.is_available(FakeContext(output=header)))
        self.assertTrue(
            module.is_available(FakeContext(output=header + "abc | dev | Up | fedora:latest\n"))
        )
        unavailable = FakeContext(output=header, return_code=1)
        self.assertTrue(module.is_available(unavailable))
        self.assertEqual(module.availability_status(unavailable), "[Unavailable]")

    def test_podman_distinguishes_empty_targets_from_probe_errors(self):
        module = PodmanModule()

        self.assertFalse(module.is_available(FakeContext(output="")))
        self.assertEqual(module.availability_status(FakeContext(output="")), "[No Targets]")
        unavailable = FakeContext(return_code=1)
        self.assertTrue(module.is_available(unavailable))
        self.assertEqual(module.availability_status(unavailable), "[Unavailable]")

    def test_bun_and_pnpm_report_missing_global_packages_as_no_targets(self):
        bun = BunModule()
        pnpm = PnpmModule()

        self.assertFalse(
            bun.is_available(
                FakeContext(error="error: No package.json was found for directory global", return_code=1)
            )
        )
        self.assertEqual(
            bun.availability_status(
                FakeContext(error="error: No package.json was found for directory global", return_code=1)
            ),
            "[No Targets]",
        )
        self.assertFalse(pnpm.is_available(FakeContext(output="No global packages found")))
        self.assertEqual(pnpm.availability_status(FakeContext(output="No global packages found")), "[No Targets]")
        self.assertTrue(bun.is_available(FakeContext(output="cowsay 1.6.0")))
        self.assertTrue(pnpm.is_available(FakeContext(output="Package | Version\nfoo | 1.0.0")))
        probe_error = FakeContext(error="registry is unavailable", return_code=1)
        self.assertTrue(bun.is_available(probe_error))
        self.assertEqual(bun.availability_status(probe_error), "[Unavailable]")


if __name__ == "__main__":
    unittest.main()
