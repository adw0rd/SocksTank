"""Unit tests for deploy orchestration helpers."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch

import typer

from server import deploy


class ResolveHostTests(unittest.TestCase):
    def test_accepts_positional_host(self) -> None:
        self.assertEqual(deploy.resolve_host("rpi5", None), "rpi5")

    def test_accepts_host_option(self) -> None:
        self.assertEqual(deploy.resolve_host(None, "rpi5"), "rpi5")

    def test_rejects_mismatched_hosts(self) -> None:
        with self.assertRaises(typer.BadParameter):
            deploy.resolve_host("rpi5", "rpi4")


class PathQuotingTests(unittest.TestCase):
    def test_quotes_home_directory(self) -> None:
        self.assertEqual(deploy._quote_remote_path("~"), "$HOME")
        self.assertEqual(deploy._quote_remote_path("~/sockstank"), "$HOME/sockstank")
        self.assertEqual(deploy._quote_remote_path("~/dir with spaces"), "$HOME/'dir with spaces'")


class ServiceUnitTests(unittest.TestCase):
    def test_renders_service_unit_for_remote_user(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".service", delete=False) as template_fh:
            template_fh.write(
                "User=__SOCKSTANK_USER__\n"
                "WorkingDirectory=__SOCKSTANK_HOME__/sockstank\n"
                "ExecStart=/usr/bin/python3 __SOCKSTANK_HOME__/sockstank/main.py serve\n"
            )
            template_path = Path(template_fh.name)

        rendered_path = deploy._render_service_unit(template_path, remote_user="zeus")
        try:
            rendered = rendered_path.read_text(encoding="utf-8")
            self.assertIn("User=zeus", rendered)
            self.assertIn("WorkingDirectory=/home/zeus/sockstank", rendered)
            self.assertIn("ExecStart=/usr/bin/python3 /home/zeus/sockstank/main.py serve", rendered)
        finally:
            template_path.unlink(missing_ok=True)
            rendered_path.unlink(missing_ok=True)


class LocaleEnvTests(unittest.TestCase):
    def test_sanitized_locale_env_uses_c_locale(self) -> None:
        with patch.dict("os.environ", {"LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"}, clear=False):
            env = deploy._sanitized_locale_env()
        self.assertEqual(env["LANG"], "C")
        self.assertEqual(env["LC_ALL"], "C")

    def test_normalizes_locale_for_locale_a(self) -> None:
        self.assertEqual(deploy._normalize_locale_for_list("en_US.UTF-8"), "en_us.utf8")
        self.assertEqual(deploy._normalize_locale_for_list("en_GB.utf8"), "en_gb.utf8")


class EnsureRemoteLocaleTests(unittest.TestCase):
    @patch("server.deploy._run_remote")
    @patch("server.deploy._preferred_ssh_locale", return_value="en_US.UTF-8")
    def test_skips_generation_when_locale_exists(self, _preferred_ssh_locale, run_remote) -> None:
        target = deploy.DeployTarget("rpi5")
        run_remote.return_value.returncode = 0

        deploy._ensure_remote_ssh_locale(target, dry_run=False)

        run_remote.assert_called_once_with(
            target,
            "locale -a | tr '[:upper:]' '[:lower:]' | grep -Fxq en_us.utf8",
            check=False,
        )

    @patch("server.deploy._run_remote")
    @patch("server.deploy._preferred_ssh_locale", return_value="en_US.UTF-8")
    def test_generates_missing_locale(self, _preferred_ssh_locale, run_remote) -> None:
        target = deploy.DeployTarget("rpi5")
        run_remote.return_value.returncode = 1

        deploy._ensure_remote_ssh_locale(target, dry_run=False)

        self.assertEqual(
            run_remote.call_args_list,
            [
                call(
                    target,
                    "locale -a | tr '[:upper:]' '[:lower:]' | grep -Fxq en_us.utf8",
                    check=False,
                ),
                call(
                    target,
                    "sudo sed -i 's/^# \\(en_US.UTF-8 UTF-8\\)$/\\1/' /etc/locale.gen && sudo locale-gen en_US.UTF-8",
                ),
            ],
        )


class InstallDependenciesTests(unittest.TestCase):
    @patch("server.deploy._run_remote")
    @patch("server.deploy._runtime_dependencies", return_value=["typer>=0.9", "fastapi>=0.104"])
    def test_prefers_uv_when_available(self, _runtime_dependencies, run_remote) -> None:
        target = deploy.DeployTarget("rpi5")

        deploy._install_remote_dependencies(target, "~/sockstank", prefer_uv=True, dry_run=False)

        run_remote.assert_called_once_with(
            target,
            "uv pip install --system 'typer>=0.9' 'fastapi>=0.104'",
            dry_run=False,
        )

    @patch("server.deploy._run_remote")
    @patch("server.deploy._runtime_dependencies", return_value=["typer>=0.9"])
    def test_falls_back_to_pip(self, _runtime_dependencies, run_remote) -> None:
        target = deploy.DeployTarget("rpi5")

        deploy._install_remote_dependencies(target, "~/sockstank", prefer_uv=False, dry_run=False)

        run_remote.assert_called_once_with(
            target,
            "python3 -m pip install 'typer>=0.9' --break-system-packages",
            dry_run=False,
        )

    @patch("server.deploy._run_remote")
    @patch("server.deploy._runtime_dependencies", return_value=["typer>=0.9"])
    def test_uses_auto_strategy_in_dry_run(self, _runtime_dependencies, run_remote) -> None:
        target = deploy.DeployTarget("rpi5")

        deploy._install_remote_dependencies(target, "~/sockstank", prefer_uv=None, dry_run=True)

        run_remote.assert_called_once_with(
            target,
            "if command -v uv >/dev/null 2>&1; then uv pip install --system 'typer>=0.9'; else python3 -m pip install 'typer>=0.9' --break-system-packages; fi",
            dry_run=True,
        )


class RestartServiceTests(unittest.TestCase):
    @patch("server.deploy._service_exists", return_value=True)
    @patch("server.deploy._run_remote")
    def test_restarts_systemd_service_when_available(self, run_remote, service_exists) -> None:
        target = deploy.DeployTarget("rpi5")

        deploy._restart_remote_service(target, "~/sockstank", port=8080, service="sockstank", has_systemd=True, dry_run=False)

        service_exists.assert_called_once_with(target, "sockstank", dry_run=False)
        run_remote.assert_called_once_with(target, "sudo systemctl restart sockstank", dry_run=False)

    @patch("server.deploy._run_remote")
    def test_fallback_restart_uses_separate_stop_and_start_commands(self, run_remote) -> None:
        target = deploy.DeployTarget("rpi5")

        deploy._restart_remote_service(target, "~/sockstank", port=8080, service="sockstank", has_systemd=False, dry_run=False)

        self.assertEqual(
            run_remote.call_args_list,
            [
                call(target, "pkill -f '^python3 .*main.py serve' >/dev/null 2>&1 || true", dry_run=False),
                call(
                    target,
                    "cd $HOME/sockstank && nohup python3 main.py serve --host 0.0.0.0 --port 8080 > /tmp/sockstank.log 2>&1 < /dev/null &",
                    dry_run=False,
                ),
            ],
        )

    @patch("server.deploy._run_remote")
    def test_dry_run_restart_uses_conditional_systemd_or_fallback(self, run_remote) -> None:
        target = deploy.DeployTarget("rpi5")

        deploy._restart_remote_service(target, "~/sockstank", port=8080, service="sockstank", has_systemd=None, dry_run=True)

        run_remote.assert_called_once_with(
            target,
            "if systemctl cat sockstank.service >/dev/null 2>&1; then sudo systemctl restart sockstank; else pkill -f '^python3 .*main.py serve' >/dev/null 2>&1 || true; cd $HOME/sockstank && nohup python3 main.py serve --host 0.0.0.0 --port 8080 > /tmp/sockstank.log 2>&1 < /dev/null & fi",
            dry_run=True,
        )


class LogsTests(unittest.TestCase):
    @patch("server.deploy._service_exists", return_value=True)
    @patch("server.deploy._run_remote")
    def test_reads_journalctl_when_service_exists(self, run_remote, service_exists) -> None:
        target = deploy.DeployTarget("rpi5")

        deploy._show_remote_logs(target, service="sockstank", lines=50, follow=False, has_systemd=True, dry_run=False)

        service_exists.assert_called_once_with(target, "sockstank", dry_run=False)
        run_remote.assert_called_once_with(target, "sudo journalctl -u sockstank -n 50 --no-pager", dry_run=False)

    @patch("server.deploy._run_remote")
    def test_reads_tail_fallback_without_systemd(self, run_remote) -> None:
        target = deploy.DeployTarget("rpi5")

        deploy._show_remote_logs(target, service="sockstank", lines=25, follow=True, has_systemd=False, dry_run=False)

        run_remote.assert_called_once_with(target, "tail -n 25 -f /tmp/sockstank.log", dry_run=False)

    @patch("server.deploy._run_remote")
    def test_dry_run_logs_uses_conditional_command(self, run_remote) -> None:
        target = deploy.DeployTarget("rpi5")

        deploy._show_remote_logs(target, service="sockstank", lines=10, follow=False, has_systemd=None, dry_run=True)

        run_remote.assert_called_once_with(
            target,
            "if systemctl cat sockstank.service >/dev/null 2>&1; then sudo journalctl -u sockstank -n 10 --no-pager; else tail -n 10 /tmp/sockstank.log; fi",
            dry_run=True,
        )


class RunDeployTests(unittest.TestCase):
    @patch("server.deploy._wait_for_healthcheck")
    @patch("server.deploy._restart_remote_service")
    @patch("server.deploy._install_remote_dependencies")
    @patch("server.deploy._rsync_project")
    @patch("server.deploy._build_frontend")
    @patch("server.deploy._ensure_remote_dirs")
    @patch("server.deploy._remote_preflight", return_value={"has_uv": False, "has_systemd": True})
    @patch("server.deploy._local_preflight")
    def test_orchestrates_steps_in_order(
        self,
        local_preflight,
        remote_preflight,
        ensure_remote_dirs,
        build_frontend,
        rsync_project,
        install_remote_dependencies,
        restart_remote_service,
        wait_for_healthcheck,
    ) -> None:
        deploy.run_deploy("rpi5", skip_build=False, skip_install=False, skip_restart=False, dry_run=False)

        target = deploy.DeployTarget("rpi5")
        local_preflight.assert_called_once_with(skip_build=False)
        remote_preflight.assert_called_once_with(target, dry_run=False)
        ensure_remote_dirs.assert_called_once_with(target, "~/sockstank", dry_run=False)
        build_frontend.assert_called_once_with(dry_run=False)
        rsync_project.assert_called_once_with(target, "~/sockstank", dry_run=False)
        install_remote_dependencies.assert_called_once_with(target, "~/sockstank", prefer_uv=False, dry_run=False)
        restart_remote_service.assert_called_once_with(
            target,
            "~/sockstank",
            port=8080,
            service="sockstank",
            has_systemd=True,
            dry_run=False,
        )
        wait_for_healthcheck.assert_called_once_with("rpi5", port=8080, dry_run=False)


class RunRestartTests(unittest.TestCase):
    @patch("server.deploy._wait_for_healthcheck")
    @patch("server.deploy._restart_remote_service")
    @patch("server.deploy._detect_remote_capabilities", return_value={"has_uv": False, "has_systemd": True})
    @patch("server.deploy._remote_check")
    @patch("server.deploy._require_local_command")
    def test_orchestrates_restart(
        self, require_local_command, remote_check, detect_remote_capabilities, restart_remote_service, wait_for_healthcheck
    ) -> None:
        deploy.run_restart("rpi5", dry_run=False)

        target = deploy.DeployTarget("rpi5")
        require_local_command.assert_called_once_with("ssh")
        remote_check.assert_called_once_with(target, "command -v python3 >/dev/null 2>&1", "python3", dry_run=False)
        detect_remote_capabilities.assert_called_once_with(target, dry_run=False)
        restart_remote_service.assert_called_once_with(
            target,
            "~/sockstank",
            port=8080,
            service="sockstank",
            has_systemd=True,
            dry_run=False,
        )
        wait_for_healthcheck.assert_called_once_with("rpi5", port=8080, dry_run=False)


class RunLogsTests(unittest.TestCase):
    @patch("server.deploy._show_remote_logs")
    @patch("server.deploy._detect_remote_capabilities", return_value={"has_uv": False, "has_systemd": True})
    @patch("server.deploy._require_local_command")
    def test_orchestrates_logs(self, require_local_command, detect_remote_capabilities, show_remote_logs) -> None:
        deploy.run_logs("rpi5", lines=20, follow=True, dry_run=False)

        target = deploy.DeployTarget("rpi5")
        require_local_command.assert_called_once_with("ssh")
        detect_remote_capabilities.assert_called_once_with(target, dry_run=False)
        show_remote_logs.assert_called_once_with(
            target,
            service="sockstank",
            lines=20,
            follow=True,
            has_systemd=True,
            dry_run=False,
        )


if __name__ == "__main__":
    unittest.main()
