from __future__ import annotations

import json
import os
import shutil
import stat
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
WATCHDOG_SOURCE = REPO_ROOT / "WatchDog"
ATM11_MANIFEST = REPO_ROOT / "configs" / "atm11-serverfiles.json"


class BlackGridError(RuntimeError):
    pass


def main() -> int:
    print("BlackGrid Setup Shell")
    print("=====================")
    print("BlackGrid creates the server cage. WatchDog keeps the gremlin alive.")
    print()

    while True:
        choice = menu(
            "What do you want BlackGrid to do?",
            [
                "Create a new Minecraft / ATM11 server",
                "Wrap an existing Minecraft / ATM11 server",
                "Exit",
            ],
        )

        try:
            if choice == 1:
                create_new_atm11_server()
            elif choice == 2:
                wrap_existing_atm11_server()
            else:
                print("Later. Try not to anger the server gremlins.")
                return 0
        except KeyboardInterrupt:
            print("\nCancelled.")
        except Exception as exc:
            print(f"\nBlackGrid hit a wall: {exc}")

        print()


def menu(title: str, items: list[str]) -> int:
    print(title)
    for index, item in enumerate(items, start=1):
        print(f"[{index}] {item}")

    while True:
        value = input("> ").strip()
        if value.isdigit() and 1 <= int(value) <= len(items):
            return int(value)
        print("Pick one of the numbers. The machine is not psychic yet.")


def ask(text: str, default: str | None = None) -> str:
    prompt = f"{text} [{default}]: " if default else f"{text}: "
    value = input(prompt).strip()
    return value or (default or "")


def yes_no(text: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        value = input(f"{text} [{suffix}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Type yes or no. Painful, but effective.")


def create_new_atm11_server() -> None:
    print("\nCreate new Minecraft / ATM11 server")
    print("This downloads the latest ATM11 ServerFiles known by the checked-in manifest.")
    print()

    server_name = slugify(ask("Server folder/name", "aetherreach"))
    install_root = resolve_user_path(
        ask(
            "Where should this standalone server live?",
            str(Path.cwd() / "BlackGridServers" / server_name),
        )
    )
    ensure_empty_or_confirm(install_root)

    manifest = load_atm11_manifest()
    server_dir = install_root / "server"
    watchdog_dir = install_root / "watchdog"
    downloads_dir = install_root / "downloads"
    manifests_dir = install_root / "manifests"

    for path in [install_root, server_dir, downloads_dir, manifests_dir]:
        path.mkdir(parents=True, exist_ok=True)

    print("\nInstalling detached WatchDog...")
    copy_watchdog(watchdog_dir)

    manifest_path = write_detached_manifest(manifests_dir, manifest)

    zip_path = downloads_dir / f"{manifest['file_id']}-{safe_name(manifest['display_name'])}.zip"
    print(f"\nDownloading ATM11 ServerFiles: {manifest['display_name']}")
    download_file(manifest["download_url"], zip_path)

    extracted_dir = downloads_dir / f"extract-{manifest['file_id']}"
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    print("Extracting server files...")
    safe_extract_zip(zip_path, extracted_dir)
    pack_root = find_pack_root(extracted_dir)
    if not pack_root:
        raise BlackGridError("Could not find a usable server pack root inside the downloaded zip.")

    print("Copying server files into the standalone server folder...")
    copy_tree_contents(pack_root, server_dir)

    if yes_no("Minecraft requires accepting the EULA before the server can run. Write eula=true now?", False):
        (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    else:
        print("Skipped EULA. The server will not fully start until eula.txt is accepted.")

    write_watchdog_config(watchdog_dir, install_root, server_dir, manifest_path, server_name)
    seed_atm11_update_state(install_root, manifest)
    write_start_scripts(install_root)
    print_done(install_root, server_name)


def wrap_existing_atm11_server() -> None:
    print("\nWrap existing Minecraft / ATM11 server")
    print("This does not move your live server folder. It creates a detached WatchDog beside it.")
    print()

    existing_server = resolve_user_path(ask("Path to the existing ATM11 server folder"))
    if not existing_server.is_dir():
        raise BlackGridError(f"Existing server folder was not found: {existing_server}")

    server_name = slugify(ask("Server name", existing_server.name or "aetherreach"))
    install_root = resolve_user_path(
        ask(
            "Where should this standalone WatchDog install live?",
            str(existing_server.parent / f"{server_name}-watchdog"),
        )
    )
    ensure_empty_or_confirm(install_root)

    manifest = load_atm11_manifest()
    watchdog_dir = install_root / "watchdog"
    manifests_dir = install_root / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    print("\nInstalling detached WatchDog...")
    copy_watchdog(watchdog_dir)

    manifest_path = write_detached_manifest(manifests_dir, manifest)
    write_watchdog_config(watchdog_dir, install_root, existing_server, manifest_path, server_name)
    write_start_scripts(install_root)
    print_done(install_root, server_name)


def print_done(install_root: Path, server_name: str) -> None:
    print("\nDone. BlackGrid is detached from this server now.")
    print(f"Server install: {install_root}")
    print(f"Server id: {server_name}")
    print()
    print("Start it later with:")
    if os.name == "nt":
        print(f"  {install_root / 'start-watchdog.bat'}")
    else:
        print(f"  {install_root / 'start-watchdog.sh'}")
    print()
    print("After that, WatchDog owns this one server. BlackGrid only comes back when you want to make or wrap another one.")


def ensure_empty_or_confirm(path: Path) -> None:
    if not path.exists():
        return
    visible = [item for item in path.iterdir() if item.name not in {".DS_Store", "Thumbs.db"}]
    if visible and not yes_no(f"Target folder already has stuff in it: {path}\nUse it anyway?", False):
        raise BlackGridError("Target folder is not empty.")


def resolve_user_path(value: str) -> Path:
    if not value:
        raise BlackGridError("A path is required.")
    return Path(value).expanduser().resolve()


def slugify(value: str) -> str:
    slug = "".join(char if char.isalnum() else "-" for char in value.strip().lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "server"


def safe_name(value: str) -> str:
    name = "".join(char if char.isalnum() or char in {".", "-", "_"} else "-" for char in str(value)).strip("-")
    return name or "serverfiles"


def load_atm11_manifest() -> dict:
    if not ATM11_MANIFEST.exists():
        raise BlackGridError(f"ATM11 manifest is missing: {ATM11_MANIFEST}")
    payload = json.loads(ATM11_MANIFEST.read_text(encoding="utf-8"))
    manifest = payload.get("atm11_serverfiles", payload)
    missing = [key for key in ["file_id", "display_name", "download_url"] if not manifest.get(key)]
    if missing:
        raise BlackGridError(f"ATM11 manifest is missing: {', '.join(missing)}")
    return manifest


def write_detached_manifest(manifests_dir: Path, manifest: dict) -> Path:
    path = manifests_dir / "atm11-serverfiles.json"
    path.write_text(json.dumps({"atm11_serverfiles": manifest}, indent=2) + "\n", encoding="utf-8")
    return path


def download_file(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BlackGrid-SetupShell", "Accept": "application/zip,application/octet-stream,*/*"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        with tmp_path.open("wb") as output:
            shutil.copyfileobj(response, output)
    if tmp_path.stat().st_size < 1024:
        tmp_path.unlink(missing_ok=True)
        raise BlackGridError("Downloaded file is suspiciously tiny. The server goblin probably handed us HTML instead of a zip.")
    tmp_path.replace(path)


def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            member_path = (destination / member.filename).resolve()
            try:
                member_path.relative_to(destination)
            except ValueError:
                raise BlackGridError(f"Unsafe zip path blocked: {member.filename}")
        archive.extractall(destination)


def find_pack_root(extracted_dir: Path) -> Path | None:
    scored: list[tuple[int, Path]] = []
    for path in [extracted_dir, *[p for p in extracted_dir.rglob("*") if p.is_dir()]]:
        score = 0
        if (path / "mods").is_dir():
            score += 5
        if (path / "config").is_dir():
            score += 4
        if (path / "defaultconfigs").is_dir():
            score += 3
        if (path / "kubejs").is_dir():
            score += 3
        if (path / "startserver.sh").exists() or (path / "startserver.bat").exists():
            score += 2
        if (path / "server-setup-config.yaml").exists():
            score += 2
        if score:
            scored.append((score, path))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def copy_tree_contents(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(item, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)
            if destination.suffix == ".sh":
                make_executable(destination)


def copy_watchdog(destination: Path) -> None:
    if not WATCHDOG_SOURCE.exists():
        raise BlackGridError(f"WatchDog source folder is missing: {WATCHDOG_SOURCE}")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        WATCHDOG_SOURCE,
        destination,
        ignore=shutil.ignore_patterns(
            ".venv", "__pycache__", "*.pyc", "logs", "state", "backups", "downloads", "tmp", "updates", "atm11", "server.zip", ".env"
        ),
    )
    for script in [destination / "start.sh"]:
        if script.exists():
            make_executable(script)


def make_executable(path: Path) -> None:
    if os.name == "nt":
        return
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def yaml_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def write_watchdog_config(watchdog_dir: Path, install_root: Path, server_dir: Path, manifest_path: Path, server_name: str) -> None:
    config_dir = watchdog_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    display_name = server_name.replace("-", " ").title().replace(" ", "")
    server_path = yaml_path(server_dir)
    content = f'''# Generated by BlackGrid Setup Shell.
# BlackGrid creates the standalone folder. WatchDog runs this one server.

wrapper:
  name: "WatchDog"
  debug: false

paths:
  logs_dir: "{yaml_path(install_root / 'logs')}"
  state_dir: "{yaml_path(install_root / 'state')}"
  backups_dir: "{yaml_path(install_root / 'backups')}"
  downloads_dir: "{yaml_path(install_root / 'downloads')}"
  tmp_dir: "{yaml_path(install_root / 'tmp')}"

server:
  directory: "{server_path}"
  start_script: "auto"
  java_executable: "${{ATM11_JAVA:-auto}}"
  required_java_major: 25
  stop_command: "stop"
  startup_timeout_seconds: 1800
  shutdown_timeout_seconds: 180
  show_minecraft_console: false
  save_minecraft_console_log: true
  environment:
    ATM11_RESTART: "false"
  startup_success_patterns:
    - 'For help, type "help"'
  startup_failure_patterns:
    - "Failed to start the minecraft server"
    - "Crash report saved"
    - "This crash report has been saved"
    - "A fatal error has been detected"
    - "FatalStartupException"
    - "session.lock: already locked"

bridges:
  aetherreach:
    enabled: false
    url: ""
    token: "${{AETHERREACH_BRIDGE_TOKEN:-}}"
    timeout_seconds: 3
  minecraft_events:
    enabled: false
    host: "127.0.0.1"
    port: 25591
    token: "${{MINECRAFT_EVENT_RECEIVER_TOKEN:-}}"

web_panel:
  enabled: false
  host: "127.0.0.1"
  port: 8080
  token: "${{WEB_PANEL_TOKEN:-}}"
  auth:
    required_op_level: 2
    code_ttl_seconds: 180
    session_ttl_seconds: 28800

plugins:
  atm11_auto_update:
    enabled: true
    server_dir: "{server_path}"
    update_dir: "{yaml_path(install_root / 'updates' / 'atm11')}"
    backup_dir: "{yaml_path(install_root / 'backups' / 'atm11_updates')}"
    check_interval_minutes: 60
    initial_check_delay_seconds: 60
    auto_download: true
    auto_apply_on_scheduled_restart: true
    manifest_url: "{manifest_path.resolve().as_uri()}"
    curseforge_scrape_fallback: true
    postpone_failed_file_ids: true
    keep_backups_days: 7
    notify_discord: false
    version_channel_id: 0
    changelog_channel_id: 0
    manual_file_id: ""
    manual_display_name: ""
    manual_page_url: ""
    manual_download_url: ""
    replace_dirs: ["config", "defaultconfigs", "kubejs", "libraries", "mods"]
    replace_files: ["run.sh", "startserver.sh", "server-setup-config.yaml", "user_jvm_args.txt"]
    preserve_custom_mods: ["watchdog_helper-*.jar", "watchdog_helper.jar", "aetherreachcore-*.jar", "worldedit-mod-7.4.3.jar"]
    preserve_paths: ["aetherreach", "config/watchdog_helper-common.toml", "config/aetherreachcore-common.toml", "world/serverconfig/ftbranks", "config/worldedit"]

  auto_restart:
    enabled: false
    enabled_monitoring: true
    restart_delay_seconds: 30
    post_stop_delay_seconds: 10
    max_crashes_in_window: 3
    crash_window_minutes: 10
    scheduled_restarts:
      enabled: false
      check_interval_seconds: 30
      times: []
    restart_countdown_seconds: [300, 60, 30, 10, 5, 4, 3, 2, 1]

  discord_bot:
    enabled: false
    server_name: "{display_name}"
    helper_name: "WatchDog"
    channel_id: 0
    guild_id: 0
    token: "${{DISCORD_BOT_TOKEN:-}}"
    ranks:
      enabled: false

  log_rotation:
    enabled: false
    keep_days: 7
    rotate_on_wrapper_start: true
    minecraft_logs_dir: "{yaml_path(server_dir / 'logs')}"

  minecraft_events:
    enabled: false

  website_status:
    enabled: false
    output_path: ""
    update_interval_seconds: 15
    server_name: "{display_name}"
    public_address: ""
    max_players: 0

  update_manager:
    enabled: false
    repository: ""
    update_dir: "{yaml_path(install_root / 'updates' / 'manager')}"
    backup_dir: "{yaml_path(install_root / 'backups' / 'update_manager')}"
    auto_download: false
    targets: {{}}

  auto_update:
    enabled: false
    mode: "manual_url"
    update_enabled: false
    latest_file_id: 0
    latest_display_name: ""
    download_url: ""
    patch_file: "plugins/auto_update/patches.yaml"
'''
    (config_dir / "wrapper.yaml").write_text(content, encoding="utf-8")


def seed_atm11_update_state(install_root: Path, manifest: dict) -> None:
    state_dir = install_root / "updates" / "atm11"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "installed_file_id": int(manifest.get("file_id", 0) or 0),
        "installed_display_name": manifest.get("display_name", ""),
        "installed_file_name": safe_name(manifest.get("display_name", "ServerFiles")),
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "source": "blackgrid_setup_shell",
    }
    for key in ("changelog", "changelog_url", "changelog_file_id", "changelog_source_url"):
        if manifest.get(key):
            state[key] = manifest[key]
    (state_dir / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def write_start_scripts(install_root: Path) -> None:
    bat = install_root / "start-watchdog.bat"
    bat.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "cd /D \"%~dp0watchdog\"\r\n"
        "if not exist \".venv\\Scripts\\python.exe\" (\r\n"
        "    python -m venv .venv\r\n"
        ")\r\n"
        "set \"PYTHON=.venv\\Scripts\\python.exe\"\r\n"
        "if not exist \".venv\\blackgrid-ready\" (\r\n"
        "    \"%PYTHON%\" -m pip install --upgrade pip\r\n"
        "    \"%PYTHON%\" -m pip install -r requirements.txt\r\n"
        "    echo ready> .venv\\blackgrid-ready\r\n"
        ")\r\n"
        "\"%PYTHON%\" main.py --config config/wrapper.yaml\r\n"
        "pause\r\n",
        encoding="utf-8",
    )

    sh = install_root / "start-watchdog.sh"
    sh.write_text(
        "#!/usr/bin/env bash\n"
        "set -Eeuo pipefail\n"
        "ROOT=\"$(cd -- \"$(dirname -- \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
        "cd \"$ROOT/watchdog\"\n"
        "chmod +x ./start.sh 2>/dev/null || true\n"
        "exec ./start.sh\n",
        encoding="utf-8",
    )
    make_executable(sh)


if __name__ == "__main__":
    raise SystemExit(main())
