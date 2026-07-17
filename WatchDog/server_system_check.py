from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Check:
    level: str
    message: str
    detail: str = ""


class Report:
    def __init__(self, title: str):
        self.title = title
        self.checks: list[Check] = []

    def ok(self, message: str, detail: str = "") -> None:
        self.checks.append(Check("OK", message, detail))

    def info(self, message: str, detail: str = "") -> None:
        self.checks.append(Check("INFO", message, detail))

    def warn(self, message: str, detail: str = "") -> None:
        self.checks.append(Check("WARN", message, detail))

    def fail(self, message: str, detail: str = "") -> None:
        self.checks.append(Check("FAIL", message, detail))

    @property
    def failed(self) -> bool:
        return any(check.level == "FAIL" for check in self.checks)

    def print(self) -> None:
        print(f"\n{self.title}")
        print("-" * len(self.title))
        for check in self.checks:
            print(f"[{check.level}] {check.message}")
            if check.detail:
                for line in str(check.detail).splitlines():
                    print(f"     {line}")
        print()
        if self.failed:
            print("Result: WatchDog will not start this server yet. Fix the FAIL items first.")
        else:
            print("Result: minimum server startup checks passed.")


def run_server_system_check(config_path: str | Path) -> int:
    report = build_report(Path(config_path))
    report.print()
    return 1 if report.failed else 0


def build_report(config_path: Path) -> Report:
    report = Report("WatchDog server system check")
    config_path = config_path.expanduser().resolve()

    if not config_path.exists():
        report.fail("WatchDog config file does not exist.", str(config_path))
        return report
    report.ok("WatchDog config file exists.", str(config_path))

    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        report.fail("WatchDog config could not be parsed as YAML.", str(exc))
        return report
    report.ok("WatchDog config parsed as YAML.")

    base_dir = config_path.parent.parent if config_path.parent.name == "config" else config_path.parent
    server_dir = resolve_path(base_dir, get(config, "server.directory", "server"))
    check_server_dir(report, server_dir)
    check_runtime_dirs(report, base_dir, config)
    check_start_script(report, server_dir, get(config, "server.start_script", "auto"))
    check_java(report, config)
    check_enabled_ports(report, config, server_dir)
    check_enabled_auth(report, config)

    return report


def check_server_dir(report: Report, server_dir: Path) -> None:
    if server_dir.is_dir():
        report.ok("Server directory exists.", str(server_dir))
    else:
        report.fail("Server directory does not exist.", str(server_dir))


def check_runtime_dirs(report: Report, base_dir: Path, config: dict) -> None:
    for key, default in [
        ("paths.logs_dir", "logs"),
        ("paths.state_dir", "state"),
        ("paths.backups_dir", "backups"),
        ("paths.downloads_dir", "downloads"),
        ("paths.tmp_dir", "tmp"),
    ]:
        path = resolve_path(base_dir, get(config, key, default))
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".watchdog-system-check.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            report.ok(f"Runtime path is writable: {key}", str(path))
        except OSError as exc:
            report.fail(f"Runtime path is not writable: {key}", f"{path}\n{exc}")


def check_start_script(report: Report, server_dir: Path, configured: str) -> None:
    if str(configured).lower() != "auto":
        path = resolve_path(server_dir, str(configured))
        if path.exists():
            report.ok("Configured start script exists.", str(path))
        else:
            report.fail("Configured start script does not exist.", str(path))
        return

    candidates = [
        "startserver.bat", "run.bat", "start.bat", "startserver.cmd", "run.cmd",
        "startserver.sh", "run.sh", "start.sh",
    ]
    found = [name for name in candidates if (server_dir / name).exists()]
    if found:
        report.ok("Auto start script candidate found.", ", ".join(found))
    else:
        report.fail("No usable server start script found.", "Expected one of: " + ", ".join(candidates))


def check_java(report: Report, config: dict) -> None:
    configured = expand_env_default(str(get(config, "server.java_executable", "auto") or "auto"))
    required = int_or_default(get(config, "server.required_java_major", 0), 0)
    java = resolve_java(configured)
    if not java:
        report.fail("Java executable was not found.", "Set server.java_executable, ATM11_JAVA, JAVA_HOME, or PATH.")
        return

    report.ok("Java executable found.", java)
    major = java_major(java)
    if major is None:
        report.warn("Could not determine Java version.", "WatchDog will try anyway, but startup may fail if the game needs a newer Java.")
        return

    if required and major < required:
        report.fail("Java version is too old.", f"Found Java {major}. Required Java {required}.")
    else:
        report.ok("Java version meets the configured requirement.", f"Found Java {major}. Required {required or 'not set'}.")


def check_enabled_ports(report: Report, config: dict, server_dir: Path) -> None:
    ports: dict[str, int] = {}
    props = read_server_properties(server_dir / "server.properties")
    if props:
        ports["minecraft.server-port"] = int_or_default(props.get("server-port"), 25565)
        if truthy(props.get("enable-query")):
            ports["minecraft.query.port"] = int_or_default(props.get("query.port"), ports["minecraft.server-port"])
        if truthy(props.get("enable-rcon")):
            ports["minecraft.rcon.port"] = int_or_default(props.get("rcon.port"), 25575)
    else:
        report.info("server.properties was not found yet.", "Skipping Minecraft port bind checks until the server creates it or you add one.")

    if bool(get(config, "web_panel.enabled", False)):
        ports["watchdog.web_panel.port"] = int_or_default(get(config, "web_panel.port", 8080), 8080)
    if bool(get(config, "bridges.minecraft_events.enabled", False)):
        ports["watchdog.minecraft_events.port"] = int_or_default(get(config, "bridges.minecraft_events.port", 25591), 25591)

    seen: dict[int, list[str]] = {}
    for label, port in ports.items():
        seen.setdefault(port, []).append(label)
    conflicts = {port: labels for port, labels in seen.items() if len(labels) > 1}
    if conflicts:
        detail = "\n".join(f"{port}: {', '.join(labels)}" for port, labels in conflicts.items())
        report.fail("Two enabled services are configured for the same port.", detail)

    for label, port in ports.items():
        if not (1 <= int(port) <= 65535):
            report.fail(f"{label} is not a valid TCP port.", str(port))
        elif port_available(port):
            report.ok(f"Port {port} is available for {label}.")
        else:
            report.warn(f"Port {port} is already in use for {label}.", "If this is the same live server already running, stop it before letting WatchDog start it.")


def check_enabled_auth(report: Report, config: dict) -> None:
    if bool(get(config, "web_panel.enabled", False)):
        host = str(get(config, "web_panel.host", "127.0.0.1"))
        token = expand_env_default(str(get(config, "web_panel.token", "") or ""))
        if host in {"0.0.0.0", "::"} and not token:
            report.fail("Web panel is exposed without a token.", "Set WEB_PANEL_TOKEN or bind the panel to 127.0.0.1.")
        else:
            report.ok("Web panel auth/bind minimum check passed.")

    if bool(get(config, "discord_bot.enabled", False)):
        token = expand_env_default(str(get(config, "discord_bot.token", "") or ""))
        channel = int_or_default(get(config, "discord_bot.channel_id", 0), 0)
        if not token or token in {"PUT_TOKEN_HERE", "PUT_DISCORD_TOKEN_HERE"}:
            report.fail("Discord bot is enabled without a usable token.")
        if not channel:
            report.fail("Discord bot is enabled without channel_id.")
        if token and channel:
            report.ok("Discord bot minimum config is present.")


def resolve_path(base_dir: Path, value: str) -> Path:
    text = str(value or "")
    path = Path(text)
    return path if path.is_absolute() else (base_dir / path).resolve()


def resolve_java(configured: str) -> str | None:
    if configured and configured.lower() != "auto":
        return configured if Path(configured).exists() or shutil.which(configured) else None
    if os.environ.get("ATM11_JAVA"):
        return os.environ["ATM11_JAVA"]
    if os.environ.get("JAVA_HOME"):
        candidate = Path(os.environ["JAVA_HOME"]) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if candidate.exists():
            return str(candidate)
    return shutil.which("java")


def expand_env_default(value: str) -> str:
    text = str(value or "").strip()
    match = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}", text)
    if not match:
        return text
    name = match.group(1)
    default = match.group(3) or ""
    return os.environ.get(name) or default


def java_major(java: str) -> int | None:
    try:
        result = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=8, check=False)
    except Exception:
        return None
    text = (result.stderr or "") + "\n" + (result.stdout or "")
    match = re.search(r'version "([0-9]+)(?:\.([0-9]+))?', text)
    if not match:
        return None
    first = int(match.group(1))
    second = int(match.group(2) or 0)
    return second if first == 1 else first


def read_server_properties(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    props: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key.strip()] = value.strip()
    return props


def get(config: dict, dotted: str, default=None):
    value = config
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def truthy(value) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "on"}


def int_or_default(value, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", int(port)))
            return True
        except OSError:
            return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run WatchDog's minimum server startup checks.")
    parser.add_argument("--config", default="config/wrapper.yaml")
    args = parser.parse_args()
    raise SystemExit(run_server_system_check(args.config))
