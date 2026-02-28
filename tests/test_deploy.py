"""Unit tests for deploy orchestration helpers."""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
