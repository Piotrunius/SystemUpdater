import io
import unittest
from contextlib import redirect_stdout

from modules.flatpak import FlatpakModule
from ui import StepResult, UI


class FakeContext:
    dry_run = False

    def __init__(self, responses):
        self.responses = iter(responses)

    def run_cmd(self, *_args, **_kwargs):
        return next(self.responses)


class FlatpakTests(unittest.TestCase):
    def test_end_of_life_runtime_warning_is_preserved_without_failing_update(self):
        warning = (
            "Info: org.freedesktop.Platform.ffmpeg-full is end-of-life, with reason: "
            "org.freedesktop.Platform 24.08 is no longer receiving fixes and security updates."
        )
        context = FakeContext(
            [
                (0, f"{warning}\nNothing to update.\n", ""),
                (0, "Nothing to update.\n", ""),
            ]
        )

        result = FlatpakModule().run(context)

        self.assertEqual(result.status, "unchanged")
        self.assertEqual(result.warnings, [warning])

    def test_summary_prints_warnings_attached_to_successful_steps(self):
        warning = "A Flatpak runtime is end-of-life."
        output = io.StringIO()
        with redirect_stdout(output):
            UI(is_interactive=False, verbose=True).print_summary(
                [
                    {
                        "name": "Flatpak Packages",
                        "key": "flatpak",
                        "result": StepResult("unchanged", warnings=[warning]),
                    }
                ],
                total_elapsed=1,
            )

        self.assertIn("Warnings", output.getvalue())
        self.assertIn(warning, output.getvalue())

    def test_normal_summary_hides_warnings(self):
        warning = "A Flatpak runtime is end-of-life."
        output = io.StringIO()
        with redirect_stdout(output):
            UI(is_interactive=False).print_summary(
                [
                    {
                        "name": "Flatpak Packages",
                        "key": "flatpak",
                        "result": StepResult("unchanged", warnings=[warning]),
                    }
                ],
                total_elapsed=1,
            )

        self.assertNotIn("Warnings", output.getvalue())
        self.assertNotIn(warning, output.getvalue())

    def test_normal_step_displays_warning_as_neutral_up_to_date(self):
        output = io.StringIO()
        with redirect_stdout(output):
            UI(is_interactive=False).print_result(
                "Device Firmware", StepResult("warning", "warning")
            )

        self.assertIn("Device Firmware: up to date", output.getvalue())
        self.assertIn("[—]", output.getvalue())
        self.assertNotIn("!", output.getvalue())

    def test_verbose_step_keeps_warning_indicator(self):
        output = io.StringIO()
        with redirect_stdout(output):
            UI(is_interactive=False, verbose=True).print_result(
                "Device Firmware", StepResult("warning", "warning")
            )

        self.assertIn("Device Firmware: warning", output.getvalue())
        self.assertIn("!", output.getvalue())


if __name__ == "__main__":
    unittest.main()
