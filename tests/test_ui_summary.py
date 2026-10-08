import contextlib
import io
import re
import unittest

from modules.base import UpdateContext
from ui import StepResult, UI


def render_summary(result, verbose=True):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        UI(is_interactive=False, verbose=verbose).print_summary(
            [{"name": "Example Module", "key": "example", "result": result}], 1.0
        )
    return re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())


class SummaryFormattingTests(unittest.TestCase):
    def test_warning_uses_a_plain_diagnostic_category_and_nested_details(self):
        output = render_summary(
            StepResult(
                "warning",
                "Update check unavailable",
                warnings=["Mirror timed out"],
                error_output="retry later",
            )
        )

        self.assertIn("── Warnings ", output)
        self.assertIn("  [!] Example Module: warning", output)
        self.assertIn("    - Update check unavailable", output)
        self.assertIn("    - Mirror timed out", output)
        self.assertIn("    - retry later", output)

    def test_error_uses_failed_label_and_nested_details(self):
        output = render_summary(
            StepResult("error", "Update failed", details=["one package updated"], error_output="bad mirror")
        )

        self.assertIn("── Errors ", output)
        self.assertIn("  [✗] Example Module: failed", output)
        self.assertIn("    - one package updated", output)
        self.assertIn("    - bad mirror", output)
        self.assertNotIn("    - Update failed", output)

    def test_no_updates_message_has_a_neutral_status_marker(self):
        output = render_summary(StepResult("warning", "warning"))

        self.assertIn("  [-] No package updates were applied.", output)

    def test_warning_category_uses_summary_color_with_colored_marker(self):
        result = StepResult("warning", "warning", warnings=["notice"])
        raw_output = io.StringIO()
        with contextlib.redirect_stdout(raw_output):
            UI(is_interactive=False, verbose=True).print_summary(
                [{"name": "Example Module", "key": "example", "result": result}], 1.0
            )

        rendered = raw_output.getvalue()
        self.assertIn("\033[1;36m── Warnings ", rendered)
        self.assertIn("\033[1;33m[!]\033[0m Example Module: warning", rendered)
        warning_section = rendered.split("\033[0m", 1)[1].split("\033[36m", 1)[0]
        self.assertNotIn("\033[1;31m", warning_section)

    def test_error_category_uses_summary_color_with_colored_marker(self):
        result = StepResult("error", "failed", error_output="details")
        raw_output = io.StringIO()
        with contextlib.redirect_stdout(raw_output):
            UI(is_interactive=False, verbose=True).print_summary(
                [{"name": "Example Module", "key": "example", "result": result}], 1.0
            )

        rendered = raw_output.getvalue()
        self.assertIn("\033[1;36m── Errors ", rendered)
        self.assertIn("\033[1;31m[✗]\033[0m Example Module: failed", rendered)

    def test_warnings_remain_hidden_without_verbose_mode(self):
        output = render_summary(StepResult("warning", "Update check unavailable"), verbose=False)

        self.assertNotIn("Warnings", output)
        self.assertNotIn("Update check unavailable", output)

    def test_verbose_step_shows_command_errors_live_and_in_the_summary(self):
        context = UpdateContext(verbose=True)

        def fail_step():
            context.command_log.append(
                {
                    "command": ["example-command"],
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "registry unavailable",
                    "output_withheld": False,
                }
            )
            return StepResult("error", "Update failed")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = UI(is_interactive=False, verbose=True).run_step(
                "Example Module", fail_step, ctx=context
            )

        self.assertEqual(result.status, "error")
        self.assertIn("registry unavailable", output.getvalue())

        summary = render_summary(result)
        self.assertIn("registry unavailable", summary)

    def test_verbose_step_shows_full_warning_output_live_and_in_the_summary(self):
        context = UpdateContext(verbose=True)

        def successful_step():
            context.command_log.append(
                {
                    "command": ["example-command"],
                    "returncode": 0,
                    "stdout": (
                        "Completed successfully\n"
                        "Warning: Calling postflight is deprecated\n"
                        "Please report this issue to the tap maintainer\n"
                        "  /home/brew/Library/Taps/example/Casks/tool.rb:36\n"
                    ),
                    "stderr": "",
                    "output_withheld": False,
                }
            )
            return StepResult("unchanged")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = UI(is_interactive=False, verbose=True).run_step(
                "Example Module", successful_step, ctx=context
            )

        self.assertIn("Completed successfully", output.getvalue())
        self.assertIn("deprecated", output.getvalue())
        self.assertIn("Please report this issue", output.getvalue())
        self.assertIn("/Casks/tool.rb:36", output.getvalue())
        self.assertIn("[!] Example Module: warning", output.getvalue())
        self.assertNotIn("Example Module: up to date", output.getvalue())
        summary = render_summary(result)
        self.assertIn("deprecated", summary)
        self.assertIn("Please report this issue", summary)
        self.assertIn("/Casks/tool.rb:36", summary)


if __name__ == "__main__":
    unittest.main()
