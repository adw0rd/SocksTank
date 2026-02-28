"""Deployment helpers for syncing the project to Raspberry Pi hosts."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import tomllib
import urllib.error
import urllib.request

import typer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DEFAULT_SERVICE_NAME = "sockstank"
DEFAULT_TARGET_DIR = "~/sockstank"
RSYNC_EXCLUDES = (
    ".claude",
    ".worktrees",
    ".git",
    ".venv",
    ".DS_Store",
    "frontend/node_modules",
    "dataset",
    "__pycache__",
    "*.pyc",
)


@dataclass(slots=True)
class DeployTarget:
    """Remote deployment target."""

    host: str
    user: str | None = None

    @property
    def ssh_target(self) -> str:
        if self.user:
            return f"{self.user}@{self.host}"
        return self.host


def resolve_host(host_arg: str | None, host_option: str | None) -> str:
    """Resolve the deploy host from positional and optional forms."""
    if host_arg and host_option and host_arg != host_option:
        raise typer.BadParameter("Host mismatch: positional host and --host must match")
    host = host_option or host_arg
    if not host:
        raise typer.BadParameter("Host is required: use './main.py deploy rpi5' or '--host rpi5'")
    return host


def run_deploy(
    host: str,
    user: str | None = None,
    *,
    target_dir: str = DEFAULT_TARGET_DIR,
    port: int = 8080,
    service: str = DEFAULT_SERVICE_NAME,
    skip_build: bool = False,
    skip_install: bool = False,
    skip_restart: bool = False,
    dry_run: bool = False,
) -> None:
    """Deploy the current workspace to a remote host."""
    target = DeployTarget(host=host, user=user)

    typer.echo(f"[deploy] Target: {target.ssh_target}:{target_dir}")
    _local_preflight(skip_build=skip_build)
    remote_caps = _remote_preflight(target, dry_run=dry_run)

    _ensure_remote_dirs(target, target_dir, dry_run=dry_run)
    if not skip_build:
        _build_frontend(dry_run=dry_run)
    _rsync_project(target, target_dir, dry_run=dry_run)
    if not skip_install:
        _install_remote_dependencies(target, target_dir, prefer_uv=remote_caps["has_uv"], dry_run=dry_run)
    if not skip_restart:
        _restart_remote_service(
            target,
            target_dir,
            port=port,
            service=service,
            has_systemd=remote_caps["has_systemd"],
            dry_run=dry_run,
        )
        _wait_for_healthcheck(host, port=port, dry_run=dry_run)

    typer.echo(f"[deploy] Done. Open: http://{host}:{port}")


def run_restart(
    host: str,
    user: str | None = None,
    *,
    target_dir: str = DEFAULT_TARGET_DIR,
    port: int = 8080,
    service: str = DEFAULT_SERVICE_NAME,
    dry_run: bool = False,
) -> None:
    """Restart SocksTank on a remote host and wait for health check."""
    target = DeployTarget(host=host, user=user)

    typer.echo(f"[restart] Target: {target.ssh_target}:{target_dir}")
    _require_local_command("ssh")
    _remote_check(target, "command -v python3 >/dev/null 2>&1", "python3", dry_run=dry_run)
    remote_caps = _detect_remote_capabilities(target, dry_run=dry_run)
    _restart_remote_service(
        target,
        target_dir,
        port=port,
        service=service,
        has_systemd=remote_caps["has_systemd"],
        dry_run=dry_run,
    )
    _wait_for_healthcheck(host, port=port, dry_run=dry_run)
    typer.echo(f"[restart] Done. Open: http://{host}:{port}")


def run_logs(
    host: str,
    user: str | None = None,
    *,
    service: str = DEFAULT_SERVICE_NAME,
    lines: int = 100,
    follow: bool = False,
    dry_run: bool = False,
) -> None:
    """Show remote SocksTank logs."""
    target = DeployTarget(host=host, user=user)

    typer.echo(f"[logs] Target: {target.ssh_target}")
    _require_local_command("ssh")
    remote_caps = _detect_remote_capabilities(target, dry_run=dry_run)
    _show_remote_logs(
        target,
        service=service,
        lines=lines,
        follow=follow,
        has_systemd=remote_caps["has_systemd"],
        dry_run=dry_run,
    )


def run_install_service(
    host: str,
    user: str | None = None,
    *,
    target_dir: str = DEFAULT_TARGET_DIR,
    service: str = DEFAULT_SERVICE_NAME,
    dry_run: bool = False,
) -> None:
    """Upload and install the bundled systemd unit on a remote host."""
    target = DeployTarget(host=host, user=user)
    unit_path = PROJECT_ROOT / "scripts" / f"{service}.service"

    if not unit_path.exists():
        raise typer.BadParameter(f"Unit file not found: {unit_path}")

    typer.echo(f"[install-service] Target: {target.ssh_target}:{target_dir}")
    _require_local_command("ssh")
    _require_local_command("scp")
    _remote_check(target, "command -v systemctl >/dev/null 2>&1", "systemctl", dry_run=dry_run)
    _require_passwordless_sudo(target, dry_run=dry_run)
    _ensure_remote_ssh_locale(target, dry_run=dry_run)
    _ensure_remote_dirs(target, target_dir, dry_run=dry_run)

    remote_user = _detect_remote_login_user(target, dry_run=dry_run)
    remote_unit = f"{target_dir}/scripts/{service}.service"
    rendered_unit = _render_service_unit(unit_path, remote_user=remote_user)
    try:
        _copy_file_to_remote(target, rendered_unit, remote_unit, dry_run=dry_run)
        _run_remote(
            target,
            (
                f"sudo cp {_quote_remote_path(remote_unit)} /etc/systemd/system/{shlex.quote(service)}.service && "
                "sudo systemctl daemon-reload && "
                f"sudo systemctl enable --now {shlex.quote(service)}"
            ),
            dry_run=dry_run,
        )
    finally:
        if rendered_unit.exists():
            rendered_unit.unlink()
    typer.echo(f"[install-service] Installed and started {service}.service")


def _local_preflight(*, skip_build: bool) -> None:
    _require_local_command("rsync")
    _require_local_command("ssh")
    _require_local_command("python3")
    if not skip_build:
        _require_local_command("npm")


def _require_local_command(command: str) -> None:
    if shutil.which(command):
        return
    raise typer.BadParameter(f"Required local command not found: {command}")


def _remote_preflight(target: DeployTarget, *, dry_run: bool) -> dict[str, bool | None]:
    _remote_check(target, "command -v python3 >/dev/null 2>&1", "python3", dry_run=dry_run)
    _remote_check(target, "command -v rsync >/dev/null 2>&1", "rsync", dry_run=dry_run)
    return _detect_remote_capabilities(target, dry_run=dry_run)


def _require_passwordless_sudo(target: DeployTarget, *, dry_run: bool) -> None:
    command = "sudo -n true"
    if dry_run:
        typer.echo(f"[dry-run] ssh {target.ssh_target} {command}")
        return
    result = _run_remote(target, command, check=False)
    if result.returncode != 0:
        raise typer.BadParameter("Remote user must have passwordless sudo for systemd installation")


def _detect_remote_capabilities(target: DeployTarget, *, dry_run: bool) -> dict[str, bool | None]:
    has_uv: bool | None = None
    has_systemd: bool | None = None
    if dry_run:
        typer.echo("[deploy] Remote toolchain: uv=unknown, systemd=unknown")
    else:
        has_uv = _run_remote(target, "command -v uv >/dev/null 2>&1", check=False).returncode == 0
        has_systemd = _run_remote(target, "command -v systemctl >/dev/null 2>&1", check=False).returncode == 0
        typer.echo(f"[deploy] Remote toolchain: uv={'yes' if has_uv else 'no'}, systemd={'yes' if has_systemd else 'no'}")
    return {"has_uv": has_uv, "has_systemd": has_systemd}


def _preferred_ssh_locale() -> str | None:
    for key in ("LC_ALL", "LANG"):
        value = os.environ.get(key)
        if not value:
            continue
        normalized = value.strip()
        if normalized and normalized not in {"C", "POSIX"}:
            return normalized
    return "en_US.UTF-8"


def _normalize_locale_for_list(locale_name: str) -> str:
    normalized = locale_name.strip().lower()
    if normalized.endswith(".utf-8"):
        normalized = normalized[:-6] + ".utf8"
    return normalized


def _ensure_remote_ssh_locale(target: DeployTarget, *, dry_run: bool) -> None:
    locale_name = _preferred_ssh_locale()
    if not locale_name:
        return

    if dry_run:
        typer.echo(f"[dry-run] Ensure remote locale exists: {locale_name}")
        return

    list_name = _normalize_locale_for_list(locale_name)
    locale_check = _run_remote(
        target,
        f"locale -a | tr '[:upper:]' '[:lower:]' | grep -Fxq {shlex.quote(list_name)}",
        check=False,
    )
    if locale_check.returncode == 0:
        return

    locale_gen_name = locale_name.replace(".utf8", ".UTF-8")
    typer.echo(f"[install-service] Generating missing remote locale: {locale_name}")
    command = (
        f"sudo sed -i 's/^# \\({locale_gen_name} UTF-8\\)$/\\1/' /etc/locale.gen && " f"sudo locale-gen {shlex.quote(locale_gen_name)}"
    )
    _run_remote(target, command)


def _detect_remote_login_user(target: DeployTarget, *, dry_run: bool) -> str:
    if dry_run:
        typer.echo(f"[dry-run] ssh {target.ssh_target} whoami")
        return target.user or "remote-user"
    result = _run_remote(target, "whoami", capture_output=True)
    remote_user = result.stdout.strip()
    if not remote_user:
        raise typer.BadParameter("Unable to detect remote login user")
    return remote_user


def _remote_check(target: DeployTarget, command: str, label: str, *, dry_run: bool) -> None:
    if dry_run:
        typer.echo(f"[dry-run] ssh {target.ssh_target} {command}")
        return
    result = _run_remote(target, command, check=False)
    if result.returncode != 0:
        raise typer.BadParameter(f"Required remote command not found: {label}")


def _ensure_remote_dirs(target: DeployTarget, target_dir: str, *, dry_run: bool) -> None:
    quoted_dir = _quote_remote_path(target_dir)
    _run_remote(target, f"mkdir -p {quoted_dir} {quoted_dir}/run", dry_run=dry_run)


def _build_frontend(*, dry_run: bool) -> None:
    typer.echo("[deploy] Building frontend")
    _run_local(["npm", "run", "build"], cwd=FRONTEND_DIR, dry_run=dry_run)


def _rsync_project(target: DeployTarget, target_dir: str, *, dry_run: bool) -> None:
    typer.echo("[deploy] Syncing project")
    cmd = ["rsync", "-az"]
    for pattern in RSYNC_EXCLUDES:
        cmd.extend(["--exclude", pattern])
    cmd.extend([f"{PROJECT_ROOT}/", f"{target.ssh_target}:{target_dir}/"])
    _run_local(cmd, dry_run=dry_run)


def _install_remote_dependencies(target: DeployTarget, target_dir: str, *, prefer_uv: bool | None, dry_run: bool) -> None:
    dependencies = _runtime_dependencies()
    if not dependencies:
        typer.echo("[deploy] No runtime dependencies declared in pyproject.toml")
        return
    dep_args = " ".join(shlex.quote(dep) for dep in dependencies)
    if prefer_uv is True:
        typer.echo("[deploy] Installing dependencies via uv")
        command = f"uv pip install --system {dep_args}"
    elif prefer_uv is False:
        typer.echo("[deploy] Installing dependencies via pip")
        command = f"python3 -m pip install {dep_args} --break-system-packages"
    else:
        typer.echo("[deploy] Installing dependencies via auto (uv preferred, pip fallback)")
        command = (
            "if command -v uv >/dev/null 2>&1; then "
            f"uv pip install --system {dep_args}; "
            "else "
            f"python3 -m pip install {dep_args} --break-system-packages; "
            "fi"
        )
    _run_remote(target, command, dry_run=dry_run)


def _restart_remote_service(
    target: DeployTarget,
    target_dir: str,
    *,
    port: int,
    service: str,
    has_systemd: bool | None,
    dry_run: bool,
) -> None:
    typer.echo("[deploy] Restarting remote service")
    if has_systemd is True and _service_exists(target, service, dry_run=dry_run):
        _run_remote(target, f"sudo systemctl restart {shlex.quote(service)}", dry_run=dry_run)
        return

    quoted_dir = _quote_remote_path(target_dir)
    if has_systemd is None and dry_run:
        command = (
            f"if systemctl cat {shlex.quote(service)}.service >/dev/null 2>&1; then "
            f"sudo systemctl restart {shlex.quote(service)}; "
            "else "
            "pkill -f '^python3 .*main.py serve' >/dev/null 2>&1 || true; "
            f"cd {quoted_dir} && nohup python3 main.py serve --host 0.0.0.0 --port {port} > /tmp/sockstank.log 2>&1 < /dev/null & "
            "fi"
        )
        _run_remote(target, command, dry_run=dry_run)
        return

    _run_remote(target, "pkill -f '^python3 .*main.py serve' >/dev/null 2>&1 || true", dry_run=dry_run)
    start_command = (
        f"cd {quoted_dir} && " f"nohup python3 main.py serve --host 0.0.0.0 --port {port} > /tmp/sockstank.log 2>&1 < /dev/null &"
    )
    _run_remote(target, start_command, dry_run=dry_run)


def _service_exists(target: DeployTarget, service: str, *, dry_run: bool) -> bool:
    command = f"systemctl cat {shlex.quote(service)}.service >/dev/null 2>&1"
    if dry_run:
        typer.echo(f"[dry-run] ssh {target.ssh_target} {command}")
        return True
    return _run_remote(target, command, check=False).returncode == 0


def _show_remote_logs(
    target: DeployTarget,
    *,
    service: str,
    lines: int,
    follow: bool,
    has_systemd: bool | None,
    dry_run: bool,
) -> None:
    follow_flag = " -f" if follow else ""
    if has_systemd is True and _service_exists(target, service, dry_run=dry_run):
        _run_remote(target, f"sudo journalctl -u {shlex.quote(service)} -n {lines} --no-pager{follow_flag}", dry_run=dry_run)
        return

    if has_systemd is None and dry_run:
        command = (
            f"if systemctl cat {shlex.quote(service)}.service >/dev/null 2>&1; then "
            f"sudo journalctl -u {shlex.quote(service)} -n {lines} --no-pager{follow_flag}; "
            "else "
            f"tail -n {lines}{follow_flag} /tmp/sockstank.log; "
            "fi"
        )
        _run_remote(target, command, dry_run=dry_run)
        return

    _run_remote(target, f"tail -n {lines}{follow_flag} /tmp/sockstank.log", dry_run=dry_run)


def _wait_for_healthcheck(host: str, *, port: int, dry_run: bool) -> None:
    url = f"http://{host}:{port}/api/status"
    if dry_run:
        typer.echo(f"[dry-run] GET {url}")
        return

    typer.echo(f"[deploy] Waiting for {url}")
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    typer.echo(f"[deploy] Health check OK ({response.status})")
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
            continue
    raise typer.BadParameter(f"Health check failed: {url}")


def _run_local(cmd: list[str], *, cwd: Path | None = None, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    display = " ".join(shlex.quote(part) for part in cmd)
    if cwd:
        display = f"(cd {shlex.quote(str(cwd))} && {display})"
    if dry_run:
        typer.echo(f"[dry-run] {display}")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    env = _sanitized_locale_env() if cmd and cmd[0] in {"rsync", "scp"} else None
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, env=env)


def _copy_file_to_remote(target: DeployTarget, source: Path, destination: str, *, dry_run: bool) -> subprocess.CompletedProcess[str]:
    cmd = ["scp", str(source), f"{target.ssh_target}:{destination}"]
    return _run_local(cmd, dry_run=dry_run)


def _quote_remote_path(path: str) -> str:
    if path == "~":
        return "$HOME"
    if path.startswith("~/"):
        return f"$HOME/{shlex.quote(path[2:])}"
    return shlex.quote(path)


def _runtime_dependencies() -> list[str]:
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)
    project = data.get("project", {})
    dependencies = project.get("dependencies", [])
    return [str(dep) for dep in dependencies]


def _render_service_unit(template_path: Path, *, remote_user: str) -> Path:
    home_dir = f"/home/{remote_user}"
    rendered = template_path.read_text(encoding="utf-8").replace("__SOCKSTANK_USER__", remote_user).replace("__SOCKSTANK_HOME__", home_dir)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".service", delete=False) as fh:
        fh.write(rendered)
        return Path(fh.name)


def _sanitized_locale_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("LANG", None)
    env.pop("LC_ALL", None)
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    return env


def _run_remote(
    target: DeployTarget,
    command: str,
    *,
    check: bool = True,
    capture_output: bool = False,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = ["ssh", target.ssh_target, f"sh -lc {shlex.quote(command)}"]
    if dry_run:
        typer.echo(f"[dry-run] {' '.join(shlex.quote(part) for part in cmd)}")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.run(cmd, check=check, text=True, capture_output=capture_output, env=_sanitized_locale_env())
