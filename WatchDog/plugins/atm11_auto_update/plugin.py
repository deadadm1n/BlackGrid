import asyncio
import glob
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

from wrapper.core.commands import CommandResult
from wrapper.core.plugin_base import WrapperPlugin as BaseWrapperPlugin
from wrapper.core.server_process import ServerProcess


class UpdateCheckUnavailable(RuntimeError):
    pass


class WrapperPlugin(BaseWrapperPlugin):
    name = "atm11_auto_update"

    ATM11_FILES_URL = "https://www.curseforge.com/minecraft/modpacks/all-the-mods-11/files/all"
    ATM11_PROJECT_ID = 1148445
    ATM11_FILES_API_URL = (
        f"https://www.curseforge.com/api/v1/mods/{ATM11_PROJECT_ID}/files"
        "?pageIndex=0&pageSize=50&sort=dateCreated&sortDescending=true"
    )

    def __init__(self, settings=None):
        self.settings = settings or {}
        self.ctx = None
        self.task = None
        self.running = False
        self.applying = False

    async def register_events(self, ctx):
        self.ctx = ctx

    async def on_wrapper_start(self, ctx):
        self.ctx = ctx

        if not self.settings.get("enabled", False):
            self.ctx.logger.info("[ATM11Update] Disabled")
            return

        self.running = True
        self.task = asyncio.create_task(self.check_loop())
        asyncio.create_task(self.catch_up_update_notifications())

        self.ctx.logger.info(
            "[ATM11Update] Enabled. Checking every %s minutes.",
            self.settings.get("check_interval_minutes", 60),
        )

    async def register_commands(self, ctx):
        self.ctx = ctx
        registry = ctx.command_registry

        registry.register(
            "atm11 update status",
            self.cmd_status,
            "Show ATM11 update status",
            owner=self.name,
            usage="watchdog atm11 update status",
        )
        registry.register(
            "minecraft update status",
            self.cmd_status,
            "Show Minecraft pack update status",
            owner=self.name,
            usage="watchdog minecraft update status",
        )
        registry.register(
            "atm11 update changelog",
            self.cmd_changelog,
            "Post the installed ATM11 changelog to Discord",
            owner=self.name,
            usage="watchdog atm11 update changelog",
        )
        registry.register(
            "minecraft update changelog",
            self.cmd_changelog,
            "Post the installed Minecraft pack changelog to Discord",
            owner=self.name,
            usage="watchdog minecraft update changelog",
        )
        registry.register(
            "atm11 update check",
            self.cmd_check,
            "Check CurseForge for a new ATM11 ServerFiles update",
            owner=self.name,
            usage="watchdog atm11 update check",
        )
        registry.register(
            "minecraft update check",
            self.cmd_check,
            "Check CurseForge for a new Minecraft pack update",
            owner=self.name,
            usage="watchdog minecraft update check",
        )
        registry.register(
            "atm11 update download",
            self.cmd_download,
            "Download the available ATM11 update without installing it",
            owner=self.name,
            usage="watchdog atm11 update download",
        )
        registry.register(
            "minecraft update download",
            self.cmd_download,
            "Download the available Minecraft pack update without installing it",
            owner=self.name,
            usage="watchdog minecraft update download",
        )
        registry.register(
            "atm11 update apply",
            self.cmd_apply,
            "Stop ATM11, install the downloaded update, validate startup, and rollback on failure",
            owner=self.name,
            usage="watchdog atm11 update apply",
        )
        registry.register(
            "minecraft update apply",
            self.cmd_apply,
            "Stop Minecraft, install the downloaded pack update, validate startup, and rollback on failure",
            owner=self.name,
            usage="watchdog minecraft update apply",
        )
        registry.register(
            "atm11 update install",
            self.cmd_install_latest,
            "Download and install the latest ATM11 ServerFiles update",
            owner=self.name,
            usage="watchdog atm11 update install [force]",
        )
        registry.register(
            "minecraft update install",
            self.cmd_install_latest,
            "Download and install the latest Minecraft ServerFiles update",
            owner=self.name,
            usage="watchdog minecraft update install [force]",
        )
        registry.register(
            "atm11 update clear",
            self.cmd_clear,
            "Clear available/pending ATM11 update state",
            owner=self.name,
            usage="watchdog atm11 update clear",
        )
        registry.register(
            "minecraft update clear",
            self.cmd_clear,
            "Clear available/pending Minecraft update state",
            owner=self.name,
            usage="watchdog minecraft update clear",
        )

    async def on_wrapper_stop(self, ctx):
        self.ctx = ctx or self.ctx
        self.running = False

        if self.task:
            self.task.cancel()

            try:
                await self.task
            except asyncio.CancelledError:
                pass

        if self.ctx:
            self.ctx.logger.info("[ATM11Update] Stopped")

    async def check_loop(self):
        interval_minutes = int(self.settings.get("check_interval_minutes", 60))
        interval_seconds = max(interval_minutes, 1) * 60

        initial_delay = int(self.settings.get("initial_check_delay_seconds", 60))
        await asyncio.sleep(max(initial_delay, 0))

        while self.running:
            try:
                if self.applying:
                    self.ctx.logger.info("[ATM11Update] Check skipped while manual apply is running")
                else:
                    await self.check_for_update()
            except UpdateCheckUnavailable as e:
                self.ctx.logger.warning("[ATM11Update] Check skipped: %s", e)
            except Exception:
                self.ctx.logger.exception("[ATM11Update] Check failed")

            await asyncio.sleep(interval_seconds)

    async def check_for_update(self):
        latest = await self.fetch_latest_serverfiles()

        file_id = int(latest["file_id"])
        display_name = latest["display_name"]
        file_name = latest["file_name"]

        state = self.load_state()
        pending = self.load_pending()

        installed_file_id = int(state.get("installed_file_id", 0) or 0)
        failed_file_ids = set(int(x) for x in state.get("failed_file_ids", []))

        self.ctx.logger.info(
            "[ATM11Update] Latest detected ServerFiles: %s | fileId=%s",
            display_name,
            file_id,
        )

        if file_id == installed_file_id:
            available = self.load_available()

            if available and int(available.get("file_id", 0) or 0) == file_id:
                self.clear_available()

            self.ctx.logger.info("[ATM11Update] No update available")
            return

        if file_id in failed_file_ids and self.settings.get("postpone_failed_file_ids", True):
            self.ctx.logger.warning(
                "[ATM11Update] Latest fileId=%s already failed before. Waiting for newer update.",
                file_id,
            )
            return

        if pending and int(pending.get("file_id", 0) or 0) == file_id:
            self.ctx.logger.info(
                "[ATM11Update] Update already downloaded and pending next reset: %s",
                pending.get("display_name", file_name),
            )
            return

        available = {
            **latest,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "status": "available_manual_download",
        }
        self.save_available(available)

        message = (
            f"[ATM11Update] New update available: {display_name} | fileId={file_id}. "
            "Use `watchdog atm11 update download` then `watchdog atm11 update apply` when ready."
        )
        self.ctx.logger.warning(message)
        await self.notify_discord(message)

        if self.settings.get("auto_download", False):
            self.ctx.logger.warning("[ATM11Update] auto_download=true; downloading update package")
            await self.download_and_prepare(
                latest,
                install_at_next_restart=self.settings.get("auto_apply_on_scheduled_restart", False),
            )

    async def fetch_latest_serverfiles(self):
        return await asyncio.to_thread(self.fetch_latest_serverfiles_sync)

    def fetch_latest_serverfiles_sync(self):
        manual_latest = self.get_manual_serverfiles_update()

        if manual_latest:
            return manual_latest

        api_error = None
        manifest_error = None
        candidates = []

        try:
            api_latest = self.get_curseforge_api_serverfiles_update()
        except UpdateCheckUnavailable as e:
            api_error = e
        else:
            if api_latest:
                candidates.append(api_latest)

        try:
            manifest_latest = self.get_manifest_serverfiles_update()
        except UpdateCheckUnavailable as e:
            manifest_error = e
            if self.ctx:
                self.ctx.logger.warning("[ATM11Update] Manifest source unavailable: %s", e)
        else:
            if manifest_latest:
                candidates.append(manifest_latest)

        if candidates:
            return max(candidates, key=lambda item: int(item.get("file_id", 0) or 0))

        if not self.settings.get("curseforge_scrape_fallback", True):
            if api_error:
                raise UpdateCheckUnavailable(str(api_error)) from api_error

            if manifest_error:
                raise UpdateCheckUnavailable(str(manifest_error)) from manifest_error

            raise UpdateCheckUnavailable(
                "No manual, CurseForge API, or manifest update source is configured, and CurseForge scraping fallback is disabled."
            )

        request = urllib.request.Request(
            self.ATM11_FILES_URL,
            headers={
                "User-Agent": "Mozilla/5.0 Watchdog-ATM11-Updater",
                "Accept": "text/html",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                html = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise UpdateCheckUnavailable(
                    "CurseForge returned HTTP 403 while checking ATM11 ServerFiles. "
                    "Automatic checking is unavailable from this host right now."
                ) from e
            raise UpdateCheckUnavailable(f"CurseForge returned HTTP {e.code} while checking updates") from e
        except urllib.error.URLError as e:
            raise UpdateCheckUnavailable(f"Could not reach CurseForge: {e.reason}") from e

        matches = []

        # Primary pattern:
        # Finds CurseForge file detail links with nearby ServerFiles text.
        link_pattern = re.compile(
            r'href="(?P<href>/minecraft/modpacks/all-the-mods-11/files/(?P<file_id>\d+))"[^>]*>(?P<title>.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )

        for match in link_pattern.finditer(html):
            href = match.group("href")
            file_id = int(match.group("file_id"))
            raw_title = match.group("title")

            title = self.strip_html(raw_title)

            if "serverfiles" not in title.lower() and "server files" not in title.lower():
                continue

            matches.append({
                "file_id": file_id,
                "display_name": title,
                "file_name": self.safe_zip_name(title),
                "page_url": "https://www.curseforge.com" + href,
                "download_url": f"https://www.curseforge.com/api/v1/mods/{self.ATM11_PROJECT_ID}/files/{file_id}/download",
            })

        if not matches:
            # Fallback pattern:
            # Search wider chunks around file links, then look for ServerFiles nearby.
            loose_pattern = re.compile(
                r'/minecraft/modpacks/all-the-mods-11/files/(?P<file_id>\d+)',
                re.IGNORECASE,
            )

            seen = set()

            for match in loose_pattern.finditer(html):
                file_id = int(match.group("file_id"))

                if file_id in seen:
                    continue

                seen.add(file_id)

                start = max(match.start() - 500, 0)
                end = min(match.end() + 1000, len(html))
                chunk = html[start:end]
                chunk_text = self.strip_html(chunk)

                if "serverfiles" not in chunk_text.lower() and "server files" not in chunk_text.lower():
                    continue

                title = self.extract_serverfiles_title(chunk_text) or f"ServerFiles-{file_id}"

                matches.append({
                    "file_id": file_id,
                    "display_name": title,
                    "file_name": self.safe_zip_name(title),
                    "page_url": f"https://www.curseforge.com/minecraft/modpacks/all-the-mods-11/files/{file_id}",
                    "download_url": f"https://www.curseforge.com/api/v1/mods/{self.ATM11_PROJECT_ID}/files/{file_id}/download",
                })

        if not matches:
            raise RuntimeError("Could not find ServerFiles entry on CurseForge page")

        # File IDs increase over time. Highest ID should be newest.
        matches.sort(key=lambda item: item["file_id"], reverse=True)
        return matches[0]

    def get_curseforge_api_serverfiles_update(self):
        if not self.settings.get("curseforge_api_enabled", True):
            return None

        files_payload = self.fetch_json(
            self.ATM11_FILES_API_URL,
            "CurseForge API file list",
        )
        files = files_payload.get("data") if isinstance(files_payload, dict) else None

        if not isinstance(files, list):
            raise UpdateCheckUnavailable("CurseForge API file list is missing data")

        for pack_file in files:
            if not isinstance(pack_file, dict):
                continue

            if not pack_file.get("hasServerPack") and not pack_file.get("additionalServerPackFilesCount"):
                continue

            pack_file_id = pack_file.get("id")

            if not pack_file_id:
                continue

            additional_url = (
                f"https://www.curseforge.com/api/v1/mods/"
                f"{self.ATM11_PROJECT_ID}/files/{pack_file_id}/additional-files"
            )
            additional_payload = self.fetch_json(
                additional_url,
                "CurseForge API additional files",
            )
            additional_files = (
                additional_payload.get("data")
                if isinstance(additional_payload, dict)
                else None
            )

            if not isinstance(additional_files, list):
                continue

            for server_file in additional_files:
                if not isinstance(server_file, dict):
                    continue

                file_id = server_file.get("id")
                display_name = str(
                    server_file.get("displayName")
                    or server_file.get("fileName")
                    or f"ServerFiles-{file_id}"
                ).strip()

                if not file_id:
                    continue

                if "serverfiles" not in display_name.lower() and "server files" not in display_name.lower():
                    continue

                return {
                    "file_id": int(file_id),
                    "display_name": display_name,
                    "file_name": str(server_file.get("fileName") or self.safe_zip_name(display_name)),
                    "page_url": (
                        "https://www.curseforge.com/minecraft/modpacks/"
                        f"all-the-mods-11/files/{file_id}"
                    ),
                    "download_url": (
                        f"https://www.curseforge.com/api/v1/mods/"
                        f"{self.ATM11_PROJECT_ID}/files/{file_id}/download"
                    ),
                    "changelog_file_id": int(pack_file_id),
                    "changelog_url": (
                        "https://www.curseforge.com/minecraft/modpacks/"
                        f"all-the-mods-11/files/{pack_file_id}/changelog"
                    ),
                    "source": "curseforge_api",
                }

        raise UpdateCheckUnavailable("Could not find an ATM11 ServerFiles entry in the CurseForge API")

    def fetch_json(self, url, description):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 Watchdog-ATM11-Updater",
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            raise UpdateCheckUnavailable(f"{description} returned HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise UpdateCheckUnavailable(f"Could not reach {description}: {e.reason}") from e
        except json.JSONDecodeError as e:
            raise UpdateCheckUnavailable(f"{description} returned invalid JSON") from e

    def get_manual_serverfiles_update(self):
        manual_download_url = str(self.settings.get("manual_download_url", "") or "").strip()
        manual_file_id = str(self.settings.get("manual_file_id", "") or "").strip()

        if not manual_download_url and not manual_file_id:
            return None

        if manual_file_id:
            if not manual_file_id.isdigit():
                raise UpdateCheckUnavailable("manual_file_id must be numeric")

            file_id = int(manual_file_id)
        else:
            file_id = self.extract_file_id_from_url(manual_download_url)

            if not file_id:
                raise UpdateCheckUnavailable("manual_download_url must include a CurseForge file id")

        display_name = str(
            self.settings.get("manual_display_name", "") or f"ServerFiles-{file_id}"
        ).strip()

        page_url = str(self.settings.get("manual_page_url", "") or "").strip()

        if not page_url:
            page_url = f"https://www.curseforge.com/minecraft/modpacks/all-the-mods-11/files/{file_id}"

        if not manual_download_url:
            manual_download_url = (
                f"https://www.curseforge.com/api/v1/mods/"
                f"{self.ATM11_PROJECT_ID}/files/{file_id}/download"
            )

        return {
            "file_id": file_id,
            "display_name": display_name,
            "file_name": self.safe_zip_name(display_name),
            "page_url": page_url,
            "download_url": manual_download_url,
            "source": "manual_config",
        }

    def get_manifest_serverfiles_update(self):
        manifest_url = str(self.settings.get("manifest_url", "") or "").strip()

        if not manifest_url:
            return None

        request = urllib.request.Request(
            manifest_url,
            headers={
                "User-Agent": "WatchDog-ATM11-Updater",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                manifest = json.loads(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            raise UpdateCheckUnavailable(
                f"ATM11 update manifest returned HTTP {e.code}: {manifest_url}"
            ) from e
        except urllib.error.URLError as e:
            raise UpdateCheckUnavailable(
                f"Could not reach ATM11 update manifest: {e.reason}"
            ) from e
        except json.JSONDecodeError as e:
            raise UpdateCheckUnavailable(
                f"ATM11 update manifest is not valid JSON: {manifest_url}"
            ) from e

        if not isinstance(manifest, dict):
            raise UpdateCheckUnavailable("ATM11 update manifest must be a JSON object")

        data = manifest.get("atm11_serverfiles", manifest)

        if not isinstance(data, dict):
            raise UpdateCheckUnavailable("ATM11 update manifest entry must be a JSON object")

        file_id = self.first_present(
            data,
            "file_id",
            "serverfiles_file_id",
            "atm11_serverfiles_file_id",
        )

        if file_id is None:
            raise UpdateCheckUnavailable("ATM11 update manifest is missing file_id")

        file_id = str(file_id).strip()

        if not file_id.isdigit():
            raise UpdateCheckUnavailable("ATM11 update manifest file_id must be numeric")

        file_id = int(file_id)

        display_name = str(
            self.first_present(data, "display_name", "name", "title") or f"ServerFiles-{file_id}"
        ).strip()
        page_url = str(data.get("page_url") or "").strip()
        download_url = str(data.get("download_url") or "").strip()

        if not page_url:
            page_url = f"https://www.curseforge.com/minecraft/modpacks/all-the-mods-11/files/{file_id}"

        if not download_url:
            download_url = (
                f"https://www.curseforge.com/api/v1/mods/"
                f"{self.ATM11_PROJECT_ID}/files/{file_id}/download"
            )

        latest = {
            "file_id": file_id,
            "display_name": display_name,
            "file_name": self.safe_zip_name(display_name),
            "page_url": page_url,
            "download_url": download_url,
            "source": "manifest",
        }

        for key in ("changelog", "changelog_url", "changelog_file_id", "changelog_source_url"):
            if data.get(key):
                latest[key] = data[key]

        return latest

    def first_present(self, data, *keys):
        for key in keys:
            value = data.get(key)

            if value not in (None, ""):
                return value

        return None

    def extract_file_id_from_url(self, url):
        match = re.search(r"/files/(\d+)", url)

        if match:
            return int(match.group(1))

        match = re.search(r"/files/(\d+)/download", url)

        if match:
            return int(match.group(1))

        return None

    def strip_html(self, text):
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def extract_serverfiles_title(self, text):
        match = re.search(
            r"(ServerFiles[-_ ]?[0-9][A-Za-z0-9.\-_]*)",
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        match = re.search(
            r"(Server Files[-_ ]?[0-9][A-Za-z0-9.\-_]*)",
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        return None

    def safe_zip_name(self, title):
        cleaned = re.sub(r"[^A-Za-z0-9.\-_]+", "-", title).strip("-")

        if not cleaned:
            cleaned = "ServerFiles"

        if not cleaned.lower().endswith(".zip"):
            cleaned += ".zip"

        return cleaned

    async def download_and_prepare(self, latest, install_at_next_restart=False):
        file_id = int(latest["file_id"])
        file_name = latest["file_name"]

        update_dir = self.update_dir()
        downloads_dir = update_dir / "downloads"
        extracted_dir = update_dir / "extracted" / str(file_id)

        downloads_dir.mkdir(parents=True, exist_ok=True)

        zip_path = downloads_dir / f"{file_id}-{file_name}"

        if extracted_dir.exists():
            shutil.rmtree(extracted_dir)

        extracted_dir.mkdir(parents=True, exist_ok=True)

        self.ctx.logger.warning("[ATM11Update] Downloading: %s", latest["download_url"])

        await asyncio.to_thread(
            self.download_file,
            latest["download_url"],
            zip_path,
        )

        self.ctx.logger.warning("[ATM11Update] Extracting update package")

        await asyncio.to_thread(
            self.extract_zip,
            zip_path,
            extracted_dir,
        )

        pack_root = self.find_pack_root(extracted_dir)

        if not pack_root:
            raise RuntimeError("Could not find server pack root inside extracted zip")

        pending_status = (
            "install_at_next_restart"
            if install_at_next_restart
            else "downloaded_pending_manual_apply"
        )

        pending = {
            "file_id": file_id,
            "file_name": file_name,
            "display_name": latest["display_name"],
            "page_url": latest["page_url"],
            "download_url": latest["download_url"],
            "zip_path": str(zip_path),
            "extract_dir": str(extracted_dir),
            "pack_root": str(pack_root),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "status": pending_status,
        }

        for key in ("changelog", "changelog_url", "changelog_file_id", "changelog_source_url"):
            if latest.get(key):
                pending[key] = latest[key]

        self.save_pending(pending)

        if install_at_next_restart:
            self.ctx.logger.warning(
                "[ATM11Update] Update downloaded and queued for next scheduled restart: %s",
                latest["display_name"],
            )
            await self.notify_discord(
                f"[ATM11Update] Downloaded update: {latest['display_name']}. "
                "It will install during the next scheduled restart."
            )
        else:
            self.ctx.logger.warning(
                "[ATM11Update] Update downloaded and pending manual apply: %s",
                latest["display_name"],
            )
            await self.notify_discord(
                f"[ATM11Update] Downloaded update: {latest['display_name']}. "
                "Use `watchdog atm11 update apply` when ready."
            )

    def download_file(self, url, path):
        tmp_path = path.with_suffix(path.suffix + ".tmp")

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 Watchdog-ATM11-Updater",
                "Accept": "application/zip,application/octet-stream,*/*",
            },
        )

        with urllib.request.urlopen(request, timeout=180) as response:
            with open(tmp_path, "wb") as out:
                shutil.copyfileobj(response, out)

        if tmp_path.stat().st_size < 1024:
            raise RuntimeError(f"Downloaded file is too small: {tmp_path}")

        tmp_path.replace(path)

    def extract_zip(self, zip_path, extract_dir):
        try:
            extract_root = Path(extract_dir).resolve()
            with zipfile.ZipFile(zip_path, "r") as archive:
                for member in archive.infolist():
                    member_path = (extract_root / member.filename).resolve()
                    try:
                        member_path.relative_to(extract_root)
                    except ValueError:
                        raise RuntimeError(f"Unsafe zip path blocked: {member.filename}")

                archive.extractall(extract_dir)
        except zipfile.BadZipFile as e:
            raise RuntimeError(f"Downloaded file is not a valid zip: {zip_path}") from e

    def find_pack_root(self, extract_dir):
        scored = []

        paths = [extract_dir] + [p for p in extract_dir.rglob("*") if p.is_dir()]

        for path in paths:
            score = 0

            if (path / "mods").is_dir():
                score += 5

            if (path / "config").is_dir():
                score += 4

            if (path / "defaultconfigs").is_dir():
                score += 3

            if (path / "kubejs").is_dir():
                score += 3

            if (path / "startserver.sh").exists():
                score += 2

            if (path / "server-setup-config.yaml").exists():
                score += 2

            if score:
                scored.append((score, path))

        if not scored:
            return None

        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    # Called by auto_restart plugin before scheduled restart stops/starts server.
    async def before_scheduled_restart(self, ctx=None):
        self.ctx = ctx or self.ctx
        pending = self.load_pending()

        if not pending:
            self.ctx.logger.info("[ATM11Update] No pending update for this reset")
            return

        if pending.get("status") != "install_at_next_restart":
            self.ctx.logger.info(
                "[ATM11Update] Pending update requires manual apply; skipping scheduled restart install"
            )
            return

        await self.announce_update_apply(pending)
        await self.install_pending_update(pending)

    async def cmd_status(self, args):
        state = self.load_state()
        available = self.load_available()
        pending = self.load_pending()

        parts = []

        if state.get("installed_display_name"):
            parts.append(f"installed={state.get('installed_display_name')} ({state.get('installed_file_id')})")
        else:
            parts.append("installed=unknown")

        if available:
            parts.append(f"available={available.get('display_name')} ({available.get('file_id')})")

        if pending:
            parts.append(f"pending={pending.get('display_name')} ({pending.get('file_id')}) status={pending.get('status')}")

        return CommandResult(
            message="ATM11 update status: " + " | ".join(parts),
            data={
                "state": state,
                "available": available or {},
                "pending": pending or {},
            },
        )

    async def cmd_changelog(self, args):
        state = self.load_state()
        posted = await self.notify_changelog_channel(state)

        if not posted:
            return CommandResult(ok=False, message="No changelog text was available to post.")

        return CommandResult(message="Posted installed ATM11 changelog to Discord.")

    async def cmd_check(self, args):
        try:
            latest = await self.fetch_latest_serverfiles()
        except UpdateCheckUnavailable as e:
            return CommandResult(ok=False, message=str(e))

        state = self.load_state()
        installed_file_id = int(state.get("installed_file_id", 0) or 0)

        if int(latest["file_id"]) == installed_file_id:
            available = self.load_available()

            if available and int(available.get("file_id", 0) or 0) == int(latest["file_id"]):
                self.clear_available()

            return CommandResult(
                message=f"ATM11 is already current: {latest['display_name']} ({latest['file_id']})",
                data={"latest": latest},
            )

        available = {
            **latest,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "status": "available_manual_download",
        }
        self.save_available(available)
        await self.notify_discord(
            f"[ATM11Update] New update available: {latest['display_name']} | fileId={latest['file_id']}. "
            "Use `watchdog atm11 update download` then `watchdog atm11 update apply`."
        )

        return CommandResult(
            message=f"Update available: {latest['display_name']} ({latest['file_id']}). Run watchdog atm11 update download.",
            data={"available": available},
        )

    async def cmd_download(self, args):
        latest = self.load_available()

        if not latest:
            try:
                latest = await self.fetch_latest_serverfiles()
            except UpdateCheckUnavailable as e:
                return CommandResult(ok=False, message=str(e))

            self.save_available({
                **latest,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "status": "available_manual_download",
            })

        pending = self.load_pending()

        if pending and int(pending.get("file_id", 0) or 0) == int(latest["file_id"]):
            return CommandResult(
                message=f"Update is already downloaded: {pending.get('display_name')} ({pending.get('file_id')})",
                data={"pending": pending},
            )

        await self.download_and_prepare(latest)
        pending = self.load_pending()

        return CommandResult(
            message=f"Downloaded update: {latest['display_name']}. Run watchdog atm11 update apply when ready.",
            data={"pending": pending or {}},
        )

    async def cmd_apply(self, args):
        pending = self.load_pending()

        if not pending:
            return CommandResult(ok=False, message="No downloaded update is pending. Run watchdog atm11 update download first.")

        if pending.get("status") == "installed_waiting_for_boot_validation":
            return CommandResult(ok=False, message="An update is already installed and waiting for boot validation.")

        if pending.get("status") == "installing":
            return CommandResult(
                ok=False,
                message=(
                    "A previous update apply was interrupted while installing. "
                    "Inspect pending.json and the backup before retrying, or run watchdog atm11 update clear."
                ),
                data={"pending": pending},
            )

        server = getattr(self.ctx, "server_process", None)
        process = getattr(server, "process", None) if server else None
        was_running = bool(process and process.returncode is None)

        self.applying = True
        self.ctx.logger.warning("[ATM11Update] Manual update apply started: %s", pending.get("display_name"))
        self.ctx.logger.warning("[ATM11Update] This can take several minutes while the server is backed up and validated.")
        await self.notify_discord(f"[ATM11Update] Manual apply started: {pending.get('display_name')}")

        try:
            if was_running:
                await self.announce_update_apply(pending)
                self.ctx.server_stop_requested = True
                await server.stop()
                self.ctx.server_stop_requested = False

            await self.install_pending_update(pending)

            new_server = ServerProcess(self.ctx)
            started = await new_server.start()

            if started:
                await self.after_scheduled_restart_success(self.ctx)

                if getattr(self.ctx, "plugin_loader", None):
                    await self.ctx.plugin_loader.run_hook("after_server_start")

                self.ctx.server_output_task = asyncio.create_task(self.ctx.server_process.read_output_forever())
                await self.notify_discord(f"[ATM11Update] Update applied successfully: {pending.get('display_name')}")

                return CommandResult(
                    message=f"Update applied and startup validated: {pending.get('display_name')}",
                    data={"file_id": pending.get("file_id")},
                )

            await self.after_scheduled_restart_failed(self.ctx)

            rollback_server = ServerProcess(self.ctx)
            rollback_started = await rollback_server.start()

            if rollback_started:
                if getattr(self.ctx, "plugin_loader", None):
                    await self.ctx.plugin_loader.run_hook("after_server_start")

                self.ctx.server_output_task = asyncio.create_task(self.ctx.server_process.read_output_forever())

            await self.notify_discord(
                f"[ATM11Update] Update failed startup validation and rollback was attempted: {pending.get('display_name')}"
            )

            return CommandResult(
                ok=False,
                message=(
                    "Update failed startup validation; rollback "
                    + ("started successfully." if rollback_started else "also failed to start.")
                ),
                data={"file_id": pending.get("file_id"), "rollback_started": rollback_started},
            )
        except Exception as e:
            self.ctx.logger.exception("[ATM11Update] Manual update apply failed")
            pending["status"] = "apply_failed"
            pending["error"] = str(e)
            pending["failed_at"] = datetime.now(timezone.utc).isoformat()
            self.save_pending(pending)
            await self.notify_discord(f"[ATM11Update] Manual apply failed: {e}")
            return CommandResult(
                ok=False,
                message=f"Update apply failed: {e}",
                data={"file_id": pending.get("file_id"), "pending_status": pending.get("status")},
            )
        finally:
            self.ctx.server_stop_requested = False
            self.applying = False

    async def announce_update_apply(self, pending):
        if not self.settings.get("announce_before_apply", True):
            return

        delay_seconds = int(self.settings.get("update_announcement_delay_seconds", 300) or 0)

        if delay_seconds <= 0:
            return

        server = getattr(self.ctx, "server_process", None)
        process = getattr(server, "process", None) if server else None

        if not server or not process or process.returncode is not None:
            return

        minutes = max(1, round(delay_seconds / 60))
        display_name = str(pending.get("display_name") or "the server update")
        message = (
            f"Server update {display_name} will start in {minutes} minute"
            f"{'' if minutes == 1 else 's'}. Please get somewhere safe."
        )

        self.ctx.logger.warning("[ATM11Update] Announcing update delay: %s", message)
        await server.send_command(f"say {message}")
        await self.notify_discord(f"[ATM11Update] {message}")

        if delay_seconds > 60:
            await asyncio.sleep(delay_seconds - 60)
            reminder = "Server update starts in 1 minute. Please get somewhere safe."
            self.ctx.logger.warning("[ATM11Update] Announcing update reminder: %s", reminder)
            await server.send_command(f"say {reminder}")
            await self.notify_discord(f"[ATM11Update] {reminder}")
            await asyncio.sleep(60)
        else:
            await asyncio.sleep(delay_seconds)

    async def cmd_install_latest(self, args):
        force = any(str(arg).lower() in {"force", "--force"} for arg in args)

        if self.applying:
            return CommandResult(ok=False, message="An ATM11 update is already running.")

        try:
            latest = await self.fetch_latest_serverfiles()
        except UpdateCheckUnavailable as e:
            return CommandResult(ok=False, message=str(e))

        state = self.load_state()
        latest_file_id = int(latest["file_id"])
        installed_file_id = int(state.get("installed_file_id", 0) or 0)

        if latest_file_id == installed_file_id and not force:
            return CommandResult(
                message=(
                    f"ATM11 is already current: {latest['display_name']} ({latest_file_id}). "
                    "Use `watchdog atm11 update install force` to reinstall it."
                ),
                data={"latest": latest},
            )

        pending = self.load_pending()

        if pending and pending.get("status") in {"installing", "installed_waiting_for_boot_validation"}:
            return CommandResult(
                ok=False,
                message=(
                    "An ATM11 update is already in progress or waiting for validation. "
                    "Inspect pending.json or run watchdog atm11 update status."
                ),
                data={"pending": pending},
            )

        self.save_available({
            **latest,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "status": "available_install_requested",
        })

        if not pending or int(pending.get("file_id", 0) or 0) != latest_file_id or force:
            self.ctx.logger.warning(
                "[ATM11Update] One-shot install downloading latest ServerFiles: %s",
                latest["display_name"],
            )
            await self.download_and_prepare(latest)

        return await self.cmd_apply(args)

    async def cmd_clear(self, args):
        self.clear_available()
        self.clear_pending()
        return CommandResult(message="Cleared ATM11 available and pending update state.")

    # Called by auto_restart plugin after server validates boot.
    async def after_scheduled_restart_success(self, ctx=None):
        self.ctx = ctx or self.ctx
        pending = self.load_pending()

        if not pending:
            await asyncio.to_thread(self.cleanup_old_backups)
            return

        if pending.get("status") != "installed_waiting_for_boot_validation":
            await asyncio.to_thread(self.cleanup_old_backups)
            return

        state = self.load_state()

        state["installed_file_id"] = pending["file_id"]
        state["installed_file_name"] = pending["file_name"]
        state["installed_display_name"] = pending.get("display_name")
        state["installed_at"] = datetime.now(timezone.utc).isoformat()
        state["last_successful_backup"] = pending.get("backup_path")

        for key in ("changelog", "changelog_url", "changelog_file_id", "changelog_source_url"):
            if pending.get(key):
                state[key] = pending[key]
            else:
                state.pop(key, None)

        self.save_state(state)
        self.clear_pending()
        self.clear_available()

        await asyncio.to_thread(self.cleanup_old_backups)

        self.ctx.logger.warning(
            "[ATM11Update] Update confirmed successful: %s",
            state["installed_display_name"],
        )
        await self.notify_installed_update_channels(state)

    # Called by auto_restart plugin after updated server fails startup validation.
    async def after_scheduled_restart_failed(self, ctx=None):
        self.ctx = ctx or self.ctx
        pending = self.load_pending()

        if not pending:
            return

        if pending.get("status") != "installed_waiting_for_boot_validation":
            return

        self.ctx.logger.error("[ATM11Update] Server failed after update. Rolling back.")

        await self.rollback_from_pending(pending)

        state = self.load_state()
        failed = state.get("failed_file_ids", [])

        failed_file_id = int(pending["file_id"])

        if failed_file_id not in failed:
            failed.append(failed_file_id)

        state["failed_file_ids"] = failed
        state["last_failed_file_id"] = failed_file_id
        state["last_failed_name"] = pending.get("display_name")
        state["last_failed_at"] = datetime.now(timezone.utc).isoformat()

        self.save_state(state)
        self.clear_pending()

        self.ctx.logger.error(
            "[ATM11Update] Rolled back update and postponed fileId=%s",
            failed_file_id,
        )

    async def install_pending_update(self, pending):
        server_dir = self.server_dir()
        pack_root = Path(pending["pack_root"]).resolve()

        if not server_dir.exists():
            raise RuntimeError(f"Server folder missing: {server_dir}")

        if not pack_root.exists():
            raise RuntimeError(f"Prepared update missing: {pack_root}")

        file_id = int(pending["file_id"])
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_path = self.backup_dir() / f"atm11-before-{file_id}-{timestamp}"

        try:
            self.ctx.logger.warning("[ATM11Update] Backing up entire server folder: %s", backup_path)

            await asyncio.to_thread(
                self.backup_entire_server,
                server_dir,
                backup_path,
            )

            pending["backup_path"] = str(backup_path)
            pending["status"] = "installing"
            pending["install_started_at"] = datetime.now(timezone.utc).isoformat()
            self.save_pending(pending)

            self.ctx.logger.warning("[ATM11Update] Installing prepared ATM11 update")

            await asyncio.to_thread(
                self.install_update_files,
                pack_root,
                server_dir,
            )

            pending["status"] = "installed_waiting_for_boot_validation"
            pending["install_finished_at"] = datetime.now(timezone.utc).isoformat()
            self.save_pending(pending)
        except Exception as e:
            pending["status"] = "install_failed"
            pending["error"] = str(e)
            pending["failed_at"] = datetime.now(timezone.utc).isoformat()
            self.save_pending(pending)
            raise

        self.ctx.logger.warning("[ATM11Update] Update installed. Awaiting startup validation.")

    def backup_entire_server(self, server_dir, backup_path):
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        if backup_path.exists():
            shutil.rmtree(backup_path)

        ignore = shutil.ignore_patterns(
            "logs",
            "crash-reports",
            "debug",
            "*.log",
            "session.lock",
        )

        shutil.copytree(server_dir, backup_path, ignore=ignore)

    def install_update_files(self, pack_root, server_dir):
        preserved_mods_dir = self.update_dir() / "preserved_mods"
        preserved_paths_dir = self.update_dir() / "preserved_paths"

        if preserved_mods_dir.exists():
            shutil.rmtree(preserved_mods_dir)

        if preserved_paths_dir.exists():
            shutil.rmtree(preserved_paths_dir)

        preserved_mods_dir.mkdir(parents=True, exist_ok=True)
        preserved_paths_dir.mkdir(parents=True, exist_ok=True)

        mods_dir = server_dir / "mods"
        preserve_patterns = self.settings.get("preserve_custom_mods", [])
        preserve_paths = self.settings.get("preserve_paths", [])

        preserved_mods = []
        preserved_paths = self.collect_preserved_paths(server_dir, preserved_paths_dir, preserve_paths)

        if mods_dir.exists():
            for pattern in preserve_patterns:
                for src in mods_dir.glob(pattern):
                    if src.is_file():
                        dst = preserved_mods_dir / src.name
                        shutil.copy2(src, dst)
                        preserved_mods.append(dst)

        replace_dirs = self.settings.get("replace_dirs", [])
        replace_files = self.settings.get("replace_files", [])

        for name in replace_dirs:
            src = pack_root / name
            dst = server_dir / name

            if dst.exists():
                shutil.rmtree(dst)

            if src.exists() and src.is_dir():
                shutil.copytree(src, dst)

        for name in replace_files:
            src = pack_root / name
            dst = server_dir / name

            if dst.exists():
                dst.unlink()

            if src.exists() and src.is_file():
                shutil.copy2(src, dst)

                if dst.name.endswith(".sh"):
                    dst.chmod(dst.stat().st_mode | 0o111)

        final_mods_dir = server_dir / "mods"
        final_mods_dir.mkdir(parents=True, exist_ok=True)

        for src in preserved_mods:
            shutil.copy2(src, final_mods_dir / src.name)

        self.restore_preserved_paths(server_dir, preserved_paths)

    def collect_preserved_paths(self, server_dir, preserve_dir, patterns):
        preserved = []

        for pattern in patterns:
            matches = self.find_preserved_matches(server_dir, pattern)

            for src in matches:
                try:
                    relative = src.relative_to(server_dir)
                except ValueError:
                    continue

                dst = preserve_dir / relative

                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("session.lock"))
                elif src.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                else:
                    continue

                preserved.append((dst, relative, src.is_dir()))

        return preserved

    def find_preserved_matches(self, server_dir, pattern):
        pattern_text = str(pattern).strip()

        if not pattern_text:
            return []

        server_dir = server_dir.resolve()
        candidate_pattern = Path(pattern_text)

        if candidate_pattern.is_absolute():
            raw_matches = glob.glob(pattern_text)
        else:
            raw_matches = glob.glob(str(server_dir / pattern_text))

        matches = []

        for match in raw_matches:
            src = Path(match).resolve()

            try:
                src.relative_to(server_dir)
            except ValueError:
                self.ctx.logger.warning("[ATM11Update] Skipping preserved path outside server dir: %s", src)
                continue

            matches.append(src)

        return matches

    def restore_preserved_paths(self, server_dir, preserved):
        for src, relative, is_dir in preserved:
            dst = server_dir / relative

            if is_dir:
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    async def rollback_from_pending(self, pending):
        server_dir = self.server_dir()
        backup_path = Path(pending["backup_path"]).resolve()

        if not backup_path.exists():
            raise RuntimeError(f"Backup missing, cannot rollback: {backup_path}")

        server = getattr(self.ctx, "server_process", None)

        if server:
            await server.stop()

        if server_dir.exists():
            shutil.rmtree(server_dir)

        self.ctx.logger.warning("[ATM11Update] Restoring backup: %s", backup_path)

        await asyncio.to_thread(
            shutil.copytree,
            backup_path,
            server_dir,
        )

    def cleanup_old_backups(self):
        backup_dir = self.backup_dir()
        keep_days = int(self.settings.get("keep_backups_days", 7))
        cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)

        if not backup_dir.exists():
            return

        for path in backup_dir.iterdir():
            if not path.is_dir():
                continue

            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)

            if modified < cutoff:
                shutil.rmtree(path)

    def server_dir(self):
        value = self.settings.get("server_dir", "atm11")
        if self.ctx:
            return self.ctx.resolve_path(value)
        return Path(value).resolve()

    def update_dir(self):
        value = self.settings.get("update_dir", "updates/atm11")
        path = self.ctx.resolve_path(value) if self.ctx else Path(value).resolve()

        path.mkdir(parents=True, exist_ok=True)

        return path

    def backup_dir(self):
        value = self.settings.get("backup_dir", "backups/atm11_updates")
        path = self.ctx.resolve_path(value) if self.ctx else Path(value).resolve()

        path.mkdir(parents=True, exist_ok=True)

        return path

    def state_path(self):
        return self.update_dir() / "state.json"

    def pending_path(self):
        return self.update_dir() / "pending.json"

    def available_path(self):
        return self.update_dir() / "available.json"

    def load_state(self):
        path = self.state_path()

        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text())
        except Exception:
            return {}

    def save_state(self, data):
        path = self.state_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

    def load_pending(self):
        path = self.pending_path()

        if not path.exists():
            return None

        try:
            return json.loads(path.read_text())
        except Exception:
            return None

    def save_pending(self, data):
        path = self.pending_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

    def clear_pending(self):
        path = self.pending_path()

        if path.exists():
            path.unlink()

    def load_available(self):
        path = self.available_path()

        if not path.exists():
            return None

        try:
            return json.loads(path.read_text())
        except Exception:
            return None

    def save_available(self, data):
        path = self.available_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

    def clear_available(self):
        path = self.available_path()

        if path.exists():
            path.unlink()

    async def notify_discord(self, message):
        if not self.settings.get("notify_discord", True):
            return

        plugin_loader = getattr(self.ctx, "plugin_loader", None)

        if not plugin_loader:
            return

        discord_plugin = plugin_loader.plugins.get("discord_bot")

        if not discord_plugin:
            return

        send_discord = getattr(discord_plugin, "send_discord", None)

        if callable(send_discord):
            await send_discord(f"```ansi\n{message}\n```")

    async def notify_version_channel(self, state):
        channel_id = int(self.settings.get("version_channel_id", 0) or 0)

        if not channel_id:
            return False

        plugin_loader = getattr(self.ctx, "plugin_loader", None)

        if not plugin_loader:
            return False

        discord_plugin = plugin_loader.plugins.get("discord_bot")

        if not discord_plugin:
            return False

        send_discord = getattr(discord_plugin, "send_discord", None)

        if not callable(send_discord):
            return False

        display_name = state.get("installed_display_name") or state.get("installed_file_name") or "unknown"
        file_id = state.get("installed_file_id") or "unknown"
        message = (
            "**The Veil has stabilized.**\n"
            f"AetherReach is now running `{display_name}`.\n"
            f"ServerFiles file id: `{file_id}`"
        )

        return bool(await send_discord(message, channel_id=channel_id))

    async def notify_installed_update_channels(self, state, *, force=False):
        file_id = int(state.get("installed_file_id", 0) or 0)

        if not file_id:
            return False

        sent_any = False
        version_sent = int(state.get("version_notified_file_id", 0) or 0) == file_id
        changelog_sent = int(state.get("changelog_notified_file_id", 0) or 0) == file_id

        if force or not version_sent:
            if await self.notify_version_channel(state):
                state["version_notified_file_id"] = file_id
                state["version_notified_at"] = datetime.now(timezone.utc).isoformat()
                sent_any = True

        if force or not changelog_sent:
            if await self.notify_changelog_channel(state):
                refreshed_state = self.load_state()
                refreshed_state["changelog_notified_file_id"] = file_id
                refreshed_state["changelog_notified_at"] = datetime.now(timezone.utc).isoformat()

                for key, value in state.items():
                    refreshed_state.setdefault(key, value)

                state = refreshed_state
                sent_any = True

        self.save_state(state)
        return sent_any

    async def catch_up_update_notifications(self):
        delay = int(self.settings.get("notification_catchup_delay_seconds", 30) or 0)
        await asyncio.sleep(max(delay, 0))

        if not self.running:
            return

        state = self.load_state()
        file_id = int(state.get("installed_file_id", 0) or 0)

        if not file_id:
            return

        version_sent = int(state.get("version_notified_file_id", 0) or 0) == file_id
        changelog_sent = int(state.get("changelog_notified_file_id", 0) or 0) == file_id

        if version_sent and changelog_sent:
            return

        self.ctx.logger.warning("[ATM11Update] Catching up missed update Discord notification(s)")
        await self.notify_installed_update_channels(state)

    async def notify_changelog_channel(self, state):
        channel_id = int(self.settings.get("changelog_channel_id", 0) or 0)

        if not channel_id:
            return False

        changelog = self.format_discord_changelog(state.get("changelog"))

        if not changelog:
            changelog = await asyncio.to_thread(self.fetch_changelog_for_state, state)

        if not changelog:
            return False

        send_discord = self.get_discord_sender()

        if not callable(send_discord):
            return False

        display_name = state.get("installed_display_name") or state.get("installed_file_name") or "unknown"
        message = f"**All the Mods 11 changelog:** `{display_name}`"

        if changelog:
            message += f"\n\n{changelog}"

        return bool(await send_discord(message, channel_id=channel_id))

    def fetch_changelog_for_state(self, state):
        file_id = state.get("changelog_file_id")

        if not file_id:
            return ""

        try:
            file_id = int(file_id)
        except (TypeError, ValueError):
            return ""

        url = f"https://www.curseforge.com/api/v1/mods/{self.ATM11_PROJECT_ID}/files/{file_id}/change-log"

        try:
            payload = self.fetch_json(url, "CurseForge API changelog")
        except UpdateCheckUnavailable as e:
            self.ctx.logger.warning("[ATM11Update] Could not fetch changelog: %s", e)
            return ""

        body = ""

        if isinstance(payload, dict):
            body = str(payload.get("changelogBody") or payload.get("data") or "")

        changelog = self.html_changelog_to_text(body)
        formatted = self.format_discord_changelog(changelog)

        if formatted:
            current = self.load_state()
            current["changelog"] = changelog
            current["changelog_source_url"] = url
            self.save_state(current)

        return formatted

    def html_changelog_to_text(self, html):
        if not html:
            return ""

        text = str(html)
        text = re.sub(r"</li>\s*<li>", "\n* ", text, flags=re.IGNORECASE)
        text = re.sub(r"<li>", "* ", text, flags=re.IGNORECASE)
        text = re.sub(r"</li>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>\s*<p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</?(ul|ol)>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</?(strong|b)>", "**", text, flags=re.IGNORECASE)
        text = re.sub(r"</?(em|i)>", "_", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
        text = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def get_discord_sender(self):
        plugin_loader = getattr(self.ctx, "plugin_loader", None)

        if not plugin_loader:
            return None

        discord_plugin = plugin_loader.plugins.get("discord_bot")

        if not discord_plugin:
            return None

        return getattr(discord_plugin, "send_discord", None)

    def format_discord_changelog(self, changelog):
        if not changelog:
            return ""

        text = str(changelog).strip()
        skipped_patterns = [
            r"^_?Updated All the Mods_?$",
            r"^_?Neoforge Version is .+_?$",
            r"^\*\*ALWAYS REMEMBER TO BACKUP BEFORE UPDATING\*\*$",
        ]
        lines = []

        for line in text.splitlines():
            stripped = line.strip()

            if any(re.match(pattern, stripped, re.IGNORECASE) for pattern in skipped_patterns):
                continue

            lines.append(line)

        text = "\n".join(lines).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        max_length = 1500

        if len(text) > max_length:
            text = text[:max_length].rstrip() + "\n..."

        return text


Plugin = WrapperPlugin
