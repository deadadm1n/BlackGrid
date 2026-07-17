from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

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
        print("BlackGrid startup requirements:")
        print("- Git")
        print(f"- Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")
        print()

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
    report = Report("BlackGrid startup requirement check")

    # Keep this intentionally tiny. This check is for starting BlackGrid itself,
    # not for starting Minecraft, ATM11, Java, tmux, Discord, or any other server goblin.
    # Server/game requirements belong in WatchDog/server_system_check.py after the user picks a server.
    check_python(report)
    check_git(report)

    report.info(
        "Server-specific requirements are checked later.",
        "Java, game files, ports, tmux, manifests, and server-specific tools are checked after the user picks a server.",
    )

    return report


def check_python(report: Report) -> None:
    py = sys.version_info
    version = f"{py.major}.{py.minor}.{py.micro}"
    if (py.major, py.minor) >= MIN_PYTHON:
        report.ok("Python version is supported.", version)
        return

    report.fail(
        "Python is too old for BlackGrid.",
        f"Found Python {version}. Install Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ and run BlackGrid again.",
    )


def check_git(report: Report) -> None:
    git_path = shutil.which("git")
    if not git_path:
        report.fail(
            "Git is not installed or is not on PATH.",
            "Install Git first, then reopen the terminal and run BlackGrid again.",
        )
        return

    version = git_version()
    if version:
        report.ok("Git is available.", version)
    else:
        report.ok("Git is available.", git_path)
        report.warn("Could not read Git version.", "BlackGrid can still start; this is just less pretty output.")


def git_version() -> str:
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return ""

    return (result.stdout or result.stderr or "").strip()


if __name__ == "__main__":
    raise SystemExit(main())
