import contextlib
import io
import re
import unittest

from modules.base import UpdateContext
from ui import UI, StepResult, suppress_terminal_echo


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
            StepResult(
                "error",
                "Update failed",
                details=["one package updated"],
                error_output="bad mirror",
            )
        )

        self.assertIn("── Errors ", output)
        self.assertIn("  [✗] Example Module: failed", output)
        self.assertIn("    - one package updated", output)
        self.assertIn("    - bad mirror", output)
        self.assertNotIn("    - Update failed", output)

    def test_no_updates_message_has_a_neutral_status_marker(self):
        output = render_summary(StepResult("warning", "warning"))

        self.assertIn("  [—] All components are up to date.", output)

    def test_no_updates_message_has_dim_em_dash_marker(self):
        raw_output = io.StringIO()
        with contextlib.redirect_stdout(raw_output):
            UI(is_interactive=False, verbose=False).print_summary(
                [
                    {
                        "name": "Example Module",
                        "key": "example",
                        "result": StepResult("unchanged"),
                    }
                ],
                1.0,
            )
        raw = raw_output.getvalue()
        self.assertIn("\033[2m[—]\033[0m All components are up to date.", raw)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", raw)
        self.assertIn("  [—] All components are up to date.", plain)

    def test_warning_category_uses_summary_color_with_colored_marker(self):
        result = StepResult("warning", "warning", warnings=["notice"])
        raw_output = io.StringIO()
        with contextlib.redirect_stdout(raw_output):
            UI(is_interactive=False, verbose=True).print_summary(
                [{"name": "Example Module", "key": "example", "result": result}], 1.0
            )

        rendered = raw_output.getvalue()
        self.assertIn("\033[1;36m── Warnings ", rendered)
        self.assertIn(
            "\033[2m[\033[0m\033[1;33m!\033[0m\033[2m]\033[0m Example Module: warning",
            rendered,
        )
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
        self.assertIn(
            "\033[2m[\033[0m\033[1;31m✗\033[0m\033[2m]\033[0m Example Module: failed",
            rendered,
        )

    def test_warnings_remain_hidden_without_verbose_mode(self):
        output = render_summary(
            StepResult("warning", "Update check unavailable"), verbose=False
        )

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
        plain_output = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        self.assertIn("[!] Example Module: warning", plain_output)
        self.assertNotIn("Example Module: up to date", plain_output)
        summary = render_summary(result)
        self.assertIn("deprecated", summary)
        self.assertIn("Please report this issue", summary)
        self.assertIn("/Casks/tool.rb:36", summary)

    def test_single_entity_module_displays_version_inline_without_sublist(self):
        # Nuvio Desktop
        nuvio_res = StepResult(
            "ok", "updated", details=["0.1.28-alpha -> 0.1.29-alpha"]
        )
        out_nuvio = io.StringIO()
        with contextlib.redirect_stdout(out_nuvio):
            UI(is_interactive=False).print_summary(
                [{"name": "Nuvio Desktop", "key": "nuvio", "result": nuvio_res}], 1.0
            )
        plain_nuvio = re.sub(r"\x1b\[[0-9;]*m", "", out_nuvio.getvalue())
        self.assertIn("• Nuvio Desktop: 0.1.28-alpha -> 0.1.29-alpha", plain_nuvio)
        self.assertNotIn("- 0.1.28-alpha", plain_nuvio)

        # Oh My Zsh
        omz_res = StepResult("ok", "updated", details=["60c9a7a -> 9f9b28a"])
        out_omz = io.StringIO()
        with contextlib.redirect_stdout(out_omz):
            UI(is_interactive=False).print_summary(
                [{"name": "Oh My Zsh", "key": "omz", "result": omz_res}], 1.0
            )
        plain_omz = re.sub(r"\x1b\[[0-9;]*m", "", out_omz.getvalue())
        self.assertIn("• Oh My Zsh: 60c9a7a -> 9f9b28a", plain_omz)
        self.assertNotIn("- 60c9a7a", plain_omz)

    def test_multi_package_module_displays_list_of_packages(self):
        brew_res = StepResult(
            "ok",
            "3 packages upgraded",
            details=[
                "certifi: 2026.7.22 -> 2026.7.22_1",
                "bun: 1.2.0 -> 1.2.4",
                "antigravity-cli-linux -> 1.3.3",
            ],
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            UI(is_interactive=False).print_summary(
                [{"name": "Homebrew", "key": "brew", "result": brew_res}], 1.0
            )
        plain = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        self.assertIn("• Homebrew: 3 packages upgraded", plain)
        self.assertIn("- certifi: 2026.7.22 -> 2026.7.22_1", plain)
        self.assertIn("- bun: 1.2.0 -> 1.2.4", plain)
        self.assertIn("- antigravity-cli-linux -> 1.3.3", plain)

    def test_multi_package_large_updates_are_capped_at_10_and_sorted_by_importance(
        self,
    ):
        packages = [
            "libssh2: 1.11.1_6 -> 1.11.1_7",
            "libgit2: 1.9.7_1 -> 1.9.7_2",
            "systemd: 262 -> 262_1",
            "python@3.14: 3.14.8 -> 3.14.8_1",
            "libngtcp2: 1.25.0 -> 1.25.0_1",
            "pipewire: 1.6.9 -> 1.6.9_1",
            "node: 26.11.0 -> 26.11.0_1",
            "antigravity-cli-linux: 1.3.0 -> 1.3.1",
            "ffmpeg: 9.0.2 -> 9.0.2_1",
            "cups: 2.4.20 -> 2.4.20_1",
            "libxml2: 2.12.0 -> 2.12.1",
            "libjpeg: 9e -> 9f",
            "pulseaudio: 17.0 -> 17.0_1",
            "systemupdater: 0.1.6 -> 0.1.7",
        ]
        brew_res = StepResult("ok", "14 packages upgraded", details=packages)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            UI(is_interactive=False).print_summary(
                [{"name": "Homebrew", "key": "brew", "result": brew_res}], 1.0
            )
        plain = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        self.assertIn("• Homebrew: 14 packages upgraded", plain)

        # Core/major tools must be shown in the top 10
        self.assertIn("- systemd: 262 -> 262_1", plain)
        self.assertIn("- python@3.14: 3.14.8 -> 3.14.8_1", plain)
        self.assertIn("- node: 26.11.0 -> 26.11.0_1", plain)
        self.assertIn("- antigravity-cli-linux: 1.3.0 -> 1.3.1", plain)
        self.assertIn("- pipewire: 1.6.9 -> 1.6.9_1", plain)
        self.assertIn("- systemupdater: 0.1.6 -> 0.1.7", plain)

        # Truncated libraries must be in the remainder
        self.assertIn("- (+4 more packages)", plain)
        self.assertNotIn("- libxml2: 2.12.0 -> 2.12.1", plain)
        self.assertNotIn("- libjpeg: 9e -> 9f", plain)

    def test_live_output_shows_exact_count_for_multi_package_modules(self):
        ui = UI(is_interactive=False)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            res = StepResult("ok", "3 packages upgraded", duration=2.5)
            ui.print_result("Homebrew", res)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        self.assertIn("[✓] Homebrew: 3 packages upgraded (2.5s)", plain)

    def test_live_output_shows_warning_in_verbose_mode_when_warnings_present(self):
        ui = UI(is_interactive=False, verbose=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            res = StepResult(
                "ok",
                "1 package updated",
                warnings=["System reboot required to complete pending updates"],
                duration=2.5,
            )
            ui.print_result("Device Firmware", res)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        self.assertIn("[!] Device Firmware: warning (2.5s)", plain)

    def test_live_output_shows_updated_for_single_entity_modules(self):
        ui = UI(is_interactive=False)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            res = StepResult(
                "ok", "updated", details=["60c9a7a -> 9f9b28a"], duration=0.5
            )
            ui.print_result("Oh My Zsh", res)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        self.assertIn("[✓] Oh My Zsh: updated (0.5s)", plain)

    def test_summary_reboot_required_handling_normal_vs_verbose(self):
        fw_res = StepResult(
            "ok",
            "1 package updated",
            details=["UEFI System Firmware -> 1.2.0"],
            warnings=["System reboot required to complete pending updates"],
            reboot_required=True,
        )

        # Normal mode: clean 1:1 output, no reboot banners or warnings
        output_normal = io.StringIO()
        with contextlib.redirect_stdout(output_normal):
            UI(is_interactive=False, verbose=False).print_summary(
                [{"name": "Device Firmware", "key": "firmware", "result": fw_res}], 1.0
            )
        plain_normal = re.sub(r"\x1b\[[0-9;]*m", "", output_normal.getvalue())
        self.assertIn("• Device Firmware: 1 package updated", plain_normal)
        self.assertIn("- UEFI System Firmware -> 1.2.0", plain_normal)
        self.assertNotIn("reboot required", plain_normal.lower())
        self.assertNotIn("Warnings", plain_normal)

        # Verbose mode: warning appears in Warnings section without (Device Firmware) appended
        output_verbose = io.StringIO()
        with contextlib.redirect_stdout(output_verbose):
            UI(is_interactive=False, verbose=True).print_summary(
                [{"name": "Device Firmware", "key": "firmware", "result": fw_res}], 1.0
            )
        plain_verbose = re.sub(r"\x1b\[[0-9;]*m", "", output_verbose.getvalue())
        self.assertIn("• Device Firmware: 1 package updated", plain_verbose)
        self.assertIn("- UEFI System Firmware -> 1.2.0", plain_verbose)
        self.assertIn("── Warnings", plain_verbose)
        self.assertIn("[!] Device Firmware: warning", plain_verbose)
        self.assertIn(
            "- System reboot required to complete pending updates", plain_verbose
        )
        self.assertNotIn("(Device Firmware)", plain_verbose)

    def test_check_packages_require_reboot(self):
        from ui import check_packages_require_reboot

        # Packages that trigger reboot
        self.assertTrue(
            check_packages_require_reboot(["kernel-core: 6.13.0 -> 6.13.2"])[0]
        )
        self.assertTrue(check_packages_require_reboot(["linux-zen -> 6.13.1"])[0])
        self.assertTrue(check_packages_require_reboot(["systemd: 256 -> 257"])[0])
        self.assertTrue(check_packages_require_reboot(["glibc: 2.40 -> 2.41"])[0])
        self.assertTrue(check_packages_require_reboot(["libc6 -> 2.39"])[0])

        # Packages that do not trigger reboot
        self.assertFalse(
            check_packages_require_reboot(["python@3.14: 3.14.0 -> 3.14.1"])[0]
        )
        self.assertFalse(
            check_packages_require_reboot(["systemupdater: 0.1.6 -> 0.1.7"])[0]
        )
        self.assertFalse(check_packages_require_reboot(["node: 22.0 -> 22.1"])[0])

    def test_complete_step_triggers_reboot_for_kernel_update(self):
        ui = UI(is_interactive=False, verbose=True)
        res = StepResult(
            "ok", "1 package upgraded", details=["kernel-core: 6.13.0 -> 6.13.2"]
        )
        ui._complete_step(res, None, command_start=0)

        self.assertTrue(res.reboot_required)
        self.assertIn(
            "System reboot required to complete pending updates", res.warnings
        )

    def test_complete_step_ignores_lvfs_triaged_issue_in_command_log(self):
        ui = UI(is_interactive=False, verbose=True)
        ctx = UpdateContext(verbose=True)
        ctx.command_log.append(
            {
                "command": ["fwupdmgr", "refresh", "--force"],
                "returncode": 0,
                "stdout": (
                    "Successfully downloaded new metadata:\n"
                    "Update failure is a known issue, visit this URL for more information: "
                    "https://github.com/fwupd/fwupd/wiki/LVFS-Triaged-Issue:-dbx-does-not-apply-on-reboot"
                ),
                "stderr": "",
                "output_withheld": False,
            }
        )
        res = StepResult("unchanged")
        ui._complete_step(res, ctx, command_start=0)

        self.assertEqual(res.status, "unchanged")
        self.assertEqual(res.warnings, [])

    def test_complete_step_ignores_glib_credentials_socket_warning_in_command_log(self):
        ui = UI(is_interactive=False, verbose=True)
        ctx = UpdateContext(verbose=True)
        ctx.command_log.append(
            {
                "command": [
                    "flatpak",
                    "run",
                    "it.mijorus.gearlever",
                    "--list-updates",
                    "--json",
                ],
                "returncode": 0,
                "stdout": '{"schema_version": 1, "updates": []}',
                "stderr": (
                    "** (process:523340): WARNING **: 06:23:41.134: "
                    "Error writing credentials to socket: Error sending message: Broken pipe"
                ),
                "output_withheld": False,
            }
        )
        res = StepResult("unchanged")
        ui._complete_step(res, ctx, command_start=0)

        self.assertEqual(res.status, "unchanged")
        self.assertEqual(res.warnings, [])

    def test_personalized_unit_nouns_in_summary_and_resolve(self):
        ui = UI(is_interactive=False, verbose=False)
        gearlever_res = StepResult(
            "ok", "updated", details=["Waywallen", "Steam Art Manager"]
        )
        msg = ui._resolve_ok_msg("Gear Lever", gearlever_res)
        self.assertEqual(msg, "2 appimages updated")

        firmware_res = StepResult("ok", "updated", details=["UEFI System Firmware"])
        msg_fw = ui._resolve_ok_msg("Device Firmware", firmware_res)
        self.assertEqual(msg_fw, "1 device updated")

        docker_res = StepResult(
            "ok", "updated", details=["mariadb:10.11", "redis:alpine"]
        )
        msg_docker = ui._resolve_ok_msg("Docker", docker_res)
        self.assertEqual(msg_docker, "2 images updated")

        distrobox_res = StepResult("ok", "updated", details=["arch", "fedora"])
        msg_distrobox = ui._resolve_ok_msg("Distrobox", distrobox_res)
        self.assertEqual(msg_distrobox, "2 containers updated")

        rust_res = StepResult("ok", "updated", details=["stable", "nightly"])
        msg_rust = ui._resolve_ok_msg("Rust", rust_res)
        self.assertEqual(msg_rust, "2 toolchains updated")

        agents_res = StepResult("ok", "updated", details=["skill-a", "skill-b"])
        msg_agents = ui._resolve_ok_msg("Agents", agents_res)
        self.assertEqual(msg_agents, "2 skills updated")

        uv_res = StepResult("ok", "updated", details=["ruff", "black"])
        msg_uv = ui._resolve_ok_msg("uv", uv_res)
        self.assertEqual(msg_uv, "2 tools updated")

        pipx_res = StepResult("ok", "updated", details=["ansible", "httpie"])
        msg_pipx = ui._resolve_ok_msg("Pipx", pipx_res)
        self.assertEqual(msg_pipx, "2 apps updated")

    def test_print_interrupted_renders_clean_banner_and_message(self):
        ui = UI(is_interactive=False, verbose=False)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ui.print_interrupted()
        raw = output.getvalue()
        self.assertIn("\033[1;36m── Interrupted ", raw)
        self.assertIn(
            "\033[2m[\033[0m\033[1;35m~\033[0m\033[2m]\033[0m Update cancelled by user.",
            raw,
        )
        self.assertTrue(raw.startswith("\n"))
        self.assertNotIn("State preserved", raw)
        self.assertNotIn("during", raw)

    def test_print_summary_renders_interrupted_section_inside_single_frame(self):
        ui = UI(is_interactive=False, verbose=False)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ui.print_summary([], 5.0, interrupted=True)
        raw = output.getvalue()
        self.assertIn("── Summary ─ 5s ", raw)
        self.assertIn("\033[2m[—]\033[0m All components are up to date.", raw)
        self.assertIn("── Interrupted ", raw)
        self.assertIn(
            "\033[2m[\033[0m\033[1;35m~\033[0m\033[2m]\033[0m Update cancelled by user.",
            raw,
        )
        self.assertEqual(raw.count("── Summary ─"), 1)
        self.assertEqual(raw.count("── Interrupted "), 1)

    def test_suppress_terminal_echo_executes_safely(self):
        with suppress_terminal_echo():
            x = 42
        self.assertEqual(x, 42)

    def test_run_step_handles_keyboard_interrupt(self):
        ui = UI(is_interactive=False, verbose=False)
        ctx = UpdateContext(verbose=False)

        def interrupt_step():
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            ui.run_step("Test Module", interrupt_step, ctx=ctx)

    def test_running_frames_contains_three_rotations_without_hyphen(self):
        from ui import RUNNING_FRAMES

        self.assertEqual(len(RUNNING_FRAMES), 3)
        for frame in RUNNING_FRAMES:
            self.assertNotIn("-", frame)
        self.assertIn("|", RUNNING_FRAMES[0])
        self.assertIn("/", RUNNING_FRAMES[1])
        self.assertIn("\\", RUNNING_FRAMES[2])

    def test_verbose_step_uses_colon_marker(self):
        ui = UI(is_interactive=False, verbose=True)
        ctx = UpdateContext(verbose=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):

            def run_dummy():
                ctx.notify_command_started()
                return StepResult("ok", "done")

            ui.run_step("Test Verbose", run_dummy, ctx=ctx)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        self.assertIn("  [:] Test Verbose...", plain)

    def test_summary_ends_with_border_without_redundant_trailing_newline(self):
        ui = UI(is_interactive=False, verbose=False)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ui.print_summary([], 5.0)
        raw = output.getvalue()
        self.assertTrue(raw.endswith("\033[0m\n"))
        self.assertFalse(raw.endswith("\033[0m\n\n"))

    def test_summary_sections_have_single_empty_line_between_them(self):
        ui = UI(is_interactive=False, verbose=True)
        results = [
            {
                "name": "WarnMod",
                "key": "warn",
                "result": StepResult("warning", "warning"),
            },
            {"name": "ErrMod", "key": "err", "result": StepResult("error", "failed")},
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ui.print_summary(results, 5.0, interrupted=True)
        raw = output.getvalue()
        self.assertIn("date.\n\n", raw)
        self.assertIn("failed\n\n", raw)
        self.assertIn("warning\n\n", raw)

    def test_summary_updates_applied_has_checkmark_marker(self):
        ui = UI(is_interactive=False, verbose=False)
        results = [
            {
                "name": "Flatpak",
                "key": "flatpak",
                "result": StepResult("ok", "1 app updated", details=["app1"]),
            }
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ui.print_summary(results, 5.0)
        raw = output.getvalue()
        self.assertIn(
            "\033[2m[\033[0m\033[1;32m✓\033[0m\033[2m]\033[0m Updated components:",
            raw,
        )
        plain = re.sub(r"\x1b\[[0-9;]*m", "", raw)
        self.assertIn("  [✓] Updated components:", plain)

    def test_verbose_steps_have_blank_line_separation(self):
        ui = UI(is_interactive=False, verbose=True)
        ctx = UpdateContext(verbose=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ui.print_category("System Core")

            def step1():
                ctx.notify_command_started()
                return StepResult("ok", "up to date")

            def step2():
                ctx.notify_command_started()
                return StepResult("ok", "up to date")

            ui.run_step("Step 1", step1, ctx=ctx)
            ui.run_step("Step 2", step2, ctx=ctx)

        plain = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        self.assertIn("(0.1s)\n\n  [:] Step 2...", plain)

    def test_verbose_live_command_output_matches_log_format(self):
        ctx = UpdateContext(verbose=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ctx.run_cmd(["echo", "hello world"])
        raw = output.getvalue()
        self.assertIn("\033[2m$\033[0m \033[1mecho 'hello world'\033[0m", raw)
        self.assertIn("        \033[2mstdout:\033[0m", raw)
        self.assertIn("          \033[2mhello world\033[0m", raw)


if __name__ == "__main__":
    unittest.main()
