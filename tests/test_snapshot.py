import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from modules.snapshot import SnapshotModule
from modules.base import UpdateContext


class SnapshotTests(unittest.TestCase):
    def test_module_is_available_only_for_snapper_btrfs_root_configuration(self):
        module = SnapshotModule()
        context = Mock()
        context.which.return_value = "/usr/bin/snapper"

        with (
            patch("modules.snapshot._root_filesystem_type", return_value="ext4"),
            patch("modules.snapshot.os.path.isfile", return_value=True),
        ):
            self.assertFalse(module.is_available(context))

        with (
            patch("modules.snapshot._root_filesystem_type", return_value="btrfs"),
            patch("modules.snapshot.os.path.isfile", return_value=False),
        ):
            self.assertFalse(module.is_available(context))

        with (
            patch("modules.snapshot._root_filesystem_type", return_value="btrfs"),
            patch("modules.snapshot.os.path.isfile", return_value=True),
        ):
            self.assertTrue(module.is_available(context))

    def test_configured_cooldown_prevents_redundant_snapshot(self):
        module = SnapshotModule(cooldown_hours=8)
        context = UpdateContext()
        context.run_cmd = Mock(side_effect=AssertionError("snapshot should be skipped"))

        with (
            tempfile.TemporaryDirectory() as cache_dir,
            patch.dict(os.environ, {"XDG_CACHE_HOME": cache_dir}),
        ):
            stamp_path = os.path.join(cache_dir, "topgrade_snapper_stamp")
            with open(stamp_path, "w", encoding="utf-8") as stamp:
                stamp.write("previous snapshot")

            result = module.run(context)

        self.assertEqual(result.status, "unchanged")
        self.assertEqual(result.message, "cooldown active")
        context.run_cmd.assert_not_called()


if __name__ == "__main__":
    unittest.main()
