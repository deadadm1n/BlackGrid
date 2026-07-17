from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
WATCHDOG_DIR = REPO_ROOT / "WatchDog"
MANIFEST_PATH = REPO_ROOT / "configs" / "atm11-serverfiles.json"
MIN_PYTHON = (3, 10)


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
                for line in check.detail.splitlines():
                    print(f"     {line}")
        print()
        if self.failed:
            print("Result: BlackGrid cannot start yet. Fix the FAIL items first.")
        else:
            print("Result: BlackGrid has the minimum stuff it needs to start.")


def main() -> int:
    report = run_checks()
    report.print()
    return 1 if report.failed else 0


def run_checks() -> Report:
    report = Report("BlackGrid system check")

    py = sys.version_info
    version = f"{py.major}.{py.minor}.{py.micro}"
    if (py.major, py.minor) >= MIN_PYTHON:
        report.ok("Python version is supported.", version)
    else:
        report.fail("Python is too old.", f"Found {version}. Need Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+.")

    report.info("Platform detected.", f"{platform.system()} {platform.release()} ({platform.machine()})")

    if REPO_ROOT.exists():
        report.ok("BlackGrid repo root exists.", str(REPO_ROOT))
    else:
        report.fail("BlackGrid repo root is missing.", str(REPO_ROOT))

    for path, label in [
        (REPO_ROOT / "blackgrid.py", "BlackGrid setup shell"),
        (WATCHDOG_DIR, "WatchDog source folder"),
        (WATCHDOG_DIR / "main.py", "WatchDog main entrypoint"),
        (WATCHDOG_DIR / "requirements.txt", "WatchDog requirements"),
        (MANIFEST_PATH, "ATM11 ServerFiles manifest"),
    ]:
        if path.exists():
            report.ok(f"Found {label}.", str(path))
        else:
            report.fail(f"Missing {label}.", str(path))

    check_manifest(report)
    check_write_access(report, REPO_ROOT)
    check_external_commands(report)
    check_network_hint(report)

    return report


def check_manifest(report: Report) -> None:
    if not MANIFEST_PATH.exists():
        return
    try:
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        data = payload.get("atm11_serverfiles", payload)
    except Exception as exc:
        report.fail("ATM11 manifest is not valid JSON.", str(exc))
        return

    missing = [key for key in ("file_id", "display_name", "download_url") if not data.get(key)]
    if missing:
        report.fail("ATM11 manifest is missing required fields.", ", ".join(missing))
    else:
        report.ok("ATM11 manifest has the minimum fields.", f"{data.get('display_name')} ({data.get('file_id')})")


def check_write_access(report: Report, path: Path) -> None:
    probe = path / ".blackgrid-system-check.tmp"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        report.ok("BlackGrid repo folder is writable.")
    except OSError as exc:
        report.fail("BlackGrid repo folder is not writable.", str(exc))


def check_external_commands(report: Report) -> None:
    if os.name == "nt":
        if shutil.which("powershell") or shutil.which("pwsh"):
            report.ok("PowerShell is available for Windows helper checks.")
        else:
            report.warn("PowerShell was not found.", "BlackGrid can still run, but Windows process/log helper checks may be weaker.")
    else:
        if shutil.which("bash"):
            report.ok("bash is available.")
        else:
            report.warn("bash was not found.", "Unix launch scripts expect bash.")
        if shutil.which("tmux"):
            report.ok("tmux is available for detached WatchDog sessions.")
        else:
            report.warn("tmux was not found.", "Linux servers can still be generated, but detached terminal reattach needs tmux installed.")


def check_network_hint(report: Report) -> None:
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=3):
            report.ok("Basic outbound network check passed.")
    except OSError:
        report.warn("Basic outbound network check failed.", "Creating a new ATM11 server needs internet access to download ServerFiles. Wrapping an existing server can still work.")


if __name__ == "__main__":
    raise SystemExit(main())
