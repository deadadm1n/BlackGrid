import re
from collections import deque

from wrapper.core.events import (
    ConsoleLineEvent,
    PlayerJoinEvent,
    PlayerLeaveEvent,
    ChatMessageEvent,
    ServerCrashEvent,
)


# Chat is now handled through:
# Minecraft -> WatchDog Helper -> HTTP -> Watchdog -> Discord
# So console regex chat relay should stay disabled.
CHAT_RELAY_FROM_LOGS = False

RECENT_ERRORS = deque(maxlen=25)


# Handles:
# DeadAdm1n joined the game
# [Founder] DeadAdm1n joined the game
# [minecraft/MinecraftServer]: [Founder] DeadAdm1n joined the game
JOIN_RE = re.compile(
    r"(?:\[[^\]]+\]\s*)?(?P<player>[A-Za-z0-9_]{3,16}) joined the game"
)

LEAVE_RE = re.compile(
    r"(?:\[[^\]]+\]\s*)?(?P<player>[A-Za-z0-9_]{3,16}) left the game"
)


# Fallback only. Normally disabled because HTTP bridge owns chat.
VANILLA_CHAT_RE = re.compile(
    r"\]: <(?P<player>[A-Za-z0-9_]{3,16})> (?P<message>.+)$"
)

RANKED_CHAT_RE = re.compile(
    r"\]: \[(?P<rank>[^\]]+)]\s*(?P<player>[A-Za-z0-9_]{3,16}):\s*(?P<message>.+)$"
)


ERROR_LEVEL_RE = re.compile(
    r"\[(?P<thread>[^\]]+)/(?P<level>ERROR|FATAL)]"
)

JAVA_EXCEPTION_RE = re.compile(
    r"(?P<exception>(?:[a-zA-Z_$][\w$]*\.)+[A-Za-z_$][\w$]*(?:Exception|Error))(?:: (?P<message>.*))?"
)

CAUSED_BY_RE = re.compile(
    r"Caused by:\s+(?P<exception>(?:[a-zA-Z_$][\w$]*\.)+[A-Za-z_$][\w$]*(?:Exception|Error))(?:: (?P<message>.*))?"
)

MISSING_DEP_RE = re.compile(
    r"Missing or unsupported mandatory dependencies|requires neoforge|ModLoadingException|Loading errors encountered",
    re.IGNORECASE,
)

CRASH_RE = re.compile(
    r"Crash report saved|This crash report has been saved|Exception in server tick loop|Encountered an unexpected exception|Failed to start the minecraft server|A fatal error has been detected|FatalStartupException",
    re.IGNORECASE,
)

IGNORED_ERROR_LINES = [
    "[ParserDebug]",
    "[Watchdog]",
    "[MinecraftEventReceiver]",
    "[DiscordBot]",
]

IGNORED_ERROR_PATTERNS = [
    # Netty probes native transports for multiple platforms during startup.
    # On Windows this can emit noisy ERROR stack traces for Linux/macOS-only
    # transports even though the server continues booting normally.
    re.compile(r"io\.netty\.channel\.(?:kqueue|epoll)\.Native"),
    re.compile(r"Only supported on (?:OSX/BSD|Linux)"),
    re.compile(r"An exception occurred processing Appender DebugFile"),
]


def clean_console_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\x1b\[[0-9;]*m", "", line)
    line = re.sub(r"\s+", " ", line)
    return line


def should_emit_error(raw: str) -> bool:
    normalized = clean_console_line(raw)

    if normalized in RECENT_ERRORS:
        return False

    RECENT_ERRORS.append(normalized)
    return True


def classify_error(line: str):
    clean = clean_console_line(line)

    if not clean:
        return None

    if any(ignored in clean for ignored in IGNORED_ERROR_LINES):
        return None

    if any(pattern.search(clean) for pattern in IGNORED_ERROR_PATTERNS):
        return None

    level_match = ERROR_LEVEL_RE.search(clean)
    log_level = level_match.group("level") if level_match else None
    is_error_level = level_match is not None
    is_fatal_level = log_level == "FATAL"
    is_missing_dep = MISSING_DEP_RE.search(clean) is not None
    is_crash = CRASH_RE.search(clean) is not None
    is_exception = JAVA_EXCEPTION_RE.search(clean) is not None
    is_caused_by = CAUSED_BY_RE.search(clean) is not None

    should_notify = is_fatal_level or is_missing_dep or is_crash or is_caused_by

    if not should_notify:
        return None

    title = "Server Error"
    severity = "ERROR"

    if is_missing_dep:
        title = "Missing / Unsupported Mod Dependency"
        severity = "FATAL"
    elif is_crash:
        title = "Server Crash Detected"
        severity = "FATAL"
    elif is_caused_by:
        title = "Java Exception Cause"
        severity = "ERROR"
    elif is_exception:
        title = "Java Exception"
        severity = "ERROR"

    exception_match = CAUSED_BY_RE.search(clean) or JAVA_EXCEPTION_RE.search(clean)

    exception_name = None
    exception_message = None

    if exception_match:
        exception_name = exception_match.groupdict().get("exception")
        exception_message = exception_match.groupdict().get("message")

    return {
        "title": title,
        "severity": severity,
        "raw": clean,
        "exception": exception_name,
        "message": exception_message,
    }


def format_error_for_discord(error: dict) -> str:
    title = error.get("title", "Server Error")
    severity = error.get("severity", "ERROR")
    raw = error.get("raw", "")
    exception = error.get("exception")
    message = error.get("message")

    lines = [
        "```ansi",
        f"[Watchdog] {title}",
        f"Severity: {severity}",
    ]

    if exception:
        lines.append(f"Exception: {exception}")

    if message:
        lines.append(f"Message: {message}")

    lines.append("")
    lines.append("Raw:")
    lines.append(raw[:1500])
    lines.append("```")

    return "\n".join(lines)


def parse_console_line(line: str):
    events = [ConsoleLineEvent(raw=line, line=line)]

    join = JOIN_RE.search(line)
    if join:
        events.append(
            PlayerJoinEvent(
                raw=line,
                player=join.group("player"),
            )
        )

    leave = LEAVE_RE.search(line)
    if leave:
        events.append(
            PlayerLeaveEvent(
                raw=line,
                player=leave.group("player"),
            )
        )

    if CHAT_RELAY_FROM_LOGS:
        chat = VANILLA_CHAT_RE.search(line) or RANKED_CHAT_RE.search(line)

        if chat:
            message = chat.group("message").strip()

            blocked_chat_messages = [
                "Set own game mode to",
                "Set the time to",
                "Teleported",
                "Gave ",
                "Killed ",
                "Saved the game",
                "Made ",
                "Reloading",
                "Unknown or incomplete command",
            ]

            if not any(blocked in message for blocked in blocked_chat_messages):
                events.append(
                    ChatMessageEvent(
                        raw=line,
                        player=chat.group("player"),
                        message=message,
                    )
                )

    error = classify_error(line)

    if error and should_emit_error(error["raw"]):
        events.append(
            ServerCrashEvent(
                raw=line,
                reason=format_error_for_discord(error),
            )
        )

    if len(events) > 1:
        print(
            f"[ParserDebug] Events: {[type(e).__name__ for e in events]} | {line}",
            flush=True,
        )

    return events
