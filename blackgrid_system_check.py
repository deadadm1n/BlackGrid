from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

MIN_PYTHON = (3, 10)
TROLL_REQUIREMENT = "Half a brain cell."


@dataclass
class Check:
    level: str
    message: str
    detail: str = ""
    troll: bool = False


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

    def fail(self, message: str, detail: str = "", *, troll: bool = False) -> None:
        self.checks.append(Check("FAIL", message, detail, troll))

    @property
    def failed(self) -> bool:
        return any(check.level == "FAIL" for check in self.checks)

    @property
    def real_failed(self) -> bool:
        return any(check.level == "FAIL" and not check.troll for check in self.checks)

    @property
    def troll_failed(self) -> bool:
        return any(check.level == "FAIL" and check.troll for check in self.checks)

    def print(self) -> None:
        print(f"\n{self.title}")
        print("-" * len(self.title))
        print("BlackGrid startup requirements:")
        print("- Git")
        print(f"- Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")
        print("- tmux")
        print(f"- {TROLL_REQUIREMENT}")
        print()

        for check in self.checks:
            print(f"[{check.level}] {check.message}")
            if check.detail:
                for line in check.detail.splitlines():
                    print(f"     {line}")
        print()

        if self.real_failed:
            print("Result: BlackGrid cannot start yet. Fix the real FAIL items first.")
        elif self.troll_failed:
            print("Result: BlackGrid found a fake catastrophic startup failure.")
        else:
            print("Result: BlackGrid has the minimum stuff it needs to start.")


def main() -> int:
    report = run_checks()
    report.print()

    if report.real_failed:
        return 1

    if report.troll_failed:
        if ask_continue_after_troll_failure():
            print("Continuing anyway. The silence is deafening.")
            return 0
        print("Closing out. We will now sit here and laugh in silence.")
        return 1

    return 0


def run_checks() -> Report:
    report = Report("BlackGrid startup requirement check")

    # Keep this focused on what BlackGrid needs before WatchDog gets to run
    # its selected-server check. Java, Minecraft files, ports, manifests, and
    # Discord settings are still server-specific and belong later.
    check_python(report)
    check_git(report)
    check_tmux(report)

    # Do not bury real startup failures under the joke. If a real requirement is
    # missing, show that instead. The troll fail only appears when the machine
    # passed the actual checks and BlackGrid is just being a gremlin.
    if not report.real_failed:
        check_half_brain_cell(report)

    report.info(
        "Server-specific requirements are checked later.",
        "Java, game files, ports, manifests, Discord settings, and per-game tools are checked after the user picks a server.",
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

    version = command_version(["git", "--version"])
    if version:
        report.ok("Git is available.", version)
    else:
        report.ok("Git is available.", git_path)
        report.warn("Could not read Git version.", "BlackGrid can still start; this is just less pretty output.")


def check_tmux(report: Report) -> None:
    tmux_path = shutil.which("tmux")
    if not tmux_path:
        report.fail(
            "tmux is not installed or is not on PATH.",
            "Install tmux before running BlackGrid. WatchDog uses it for detached server terminals and reattach support.",
        )
        return

    version = command_version(["tmux", "-V"])
    if version:
        report.ok("tmux is available.", version)
    else:
        report.ok("tmux is available.", tmux_path)
        report.warn("Could not read tmux version.", "BlackGrid can still start; this is just less pretty output.")


def check_half_brain_cell(report: Report) -> None:
    report.fail(
        TROLL_REQUIREMENT,
        "Optional but strongly recommended. BlackGrid failed to detect one. This may be a false positive. Probably.",
        troll=True,
    )


def ask_continue_after_troll_failure() -> bool:
    while True:
        try:
            value = input("Continue anyway? [y/N]: ").strip().lower()
        except EOFError:
            return False

        if not value:
            return False
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Type yes or no. The fake brain cell check cannot process interpretive dance yet.")


def command_version(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
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
