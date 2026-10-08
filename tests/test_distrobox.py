import unittest

from modules.distrobox import DistroboxModule


class FakeContext:
    dry_run = False

    def __init__(self, output, returncode=0):
        self.output = output
        self.returncode = returncode

    def run_cmd(self, command):
        return self.returncode, self.output, ""


class DistroboxResultTests(unittest.TestCase):
    def test_container_headers_and_nothing_to_do_are_not_reported_as_updates(self):
        output = """\
Upgrading arch...
:: Starting full system upgrade...
 there is nothing to do
Upgrading fedora...
Updating and loading repositories:
Repositories loaded.
Nothing to do.
"""

        result = DistroboxModule().run(FakeContext(output))

        self.assertEqual(result.status, "unchanged")

    def test_package_upgrade_inside_a_container_is_reported(self):
        output = """\
Upgrading arch...
:: Starting full system upgrade...
upgrading example-package...
"""

        result = DistroboxModule().run(FakeContext(output))

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.details, ["arch"])


if __name__ == "__main__":
    unittest.main()
