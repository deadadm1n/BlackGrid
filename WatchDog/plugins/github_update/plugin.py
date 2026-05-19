import asyncio
import fnmatch
import json
import re
import shutil
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from wrapper.core.commands import CommandResult
from wrapper.core.plugin_base import WrapperPlugin


class Plugin(WrapperPlugin):
    name = "github_update"

    def __init__(self, settings=None):
        super().__init__(settings=settings)
        self.ctx = None
        self.task = None
        self.running = False

    async def on_wrapper_start(self, ctx):
        self.ctx = ctx
        if not self.settings.get("check_on_start", False):
            return

        self.running = True
        self.task = asyncio.create_task(self.check_loop())

    async def on_wrapper_stop(self, ctx):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def check_loop(self):
        await asyncio.sleep(max(int(self.settings.get("initial_check_delay_seconds", 30)), 0))
        if not self.running:
            return

        try:
            await self.check_target("wrapper", None)
            for plugin_name in self.settings.get("managed_plugins", []):
                await self.check_target("plugin", plugin_name)
        except Exception:
            self.ctx.logger.exception("[GitHubUpdate] Startup update check failed")

    async def register_commands(self, ctx):
        self.ctx = ctx
        registry = ctx.command_registry

        registry.register(
            "github update status",
            self.cmd_status,
            "Show GitHub wrapper/plugin update state",
            owner=self.name,
            usage="wrapper github update status",
        )
        registry.register(
            "github update check",
            self.cmd_check,
            "Check GitHub releases for wrapper or plugin updates",
            owner=self.name,
            usage="wrapper github update check wrapper | wrapper github update check plugin <name>",
        )
        registry.register(
            "github update download",
            self.cmd_download,
            "Download an available wrapper or plugin update",
            owner=self.name,
            usage="wrapper github update download wrapper | wrapper github update download plugin <name>",
        )
        registry.register(
            "github update apply",
            self.cmd_apply,
            "Apply a downloaded wrapper or plugin update",
            owner=self.name,
            usage="wrapper github update apply wrapper | wrapper github update apply plugin <name>",
        )
        registry.register(
            "github update clear",
            self.cmd_clear,
            "Clear downloaded GitHub update state",
            owner=self.name,
            usage="wrapper github update clear wrapper | wrapper github update clear plugin <name>",
        )

    async def cmd_status(self, args):
        return CommandResult(
            message="GitHub update status",
            data={
                "installed": self.load_json(self.state_path("installed"), {}),
                "available": self.load_json(self.state_path("available"), {}),
                "pending": self.load_json(self.state_path("pending"), {}),
            },
        )

    async def cmd_check(self, args):
        package_type, plugin_name, error = self.parse_target(args)
        if error:
            return CommandResult(ok=False, message=error)

        available = await self.check_target(package_type, plugin_name)
        if not available:
            return CommandResult(message=f"No {self.target_label(package_type, plugin_name)} update available.")

        return CommandResult(
            message=(
                f"Update available for {self.target_label(package_type, plugin_name)}: "
                f"{available['version']} ({available['asset_name']}). Run wrapper github update download."
            ),
            data={"available": available},
        )

    async def cmd_download(self, args):
        package_type, plugin_name, error = self.parse_target(args)
        if error:
            return CommandResult(ok=False, message=error)

        available = await self.ensure_available(package_type, plugin_name)
        if not available:
            return CommandResult(message=f"No {self.target_label(package_type, plugin_name)} update available.")

        pending = await self.download_available(available)
        return CommandResult(
            message=f"Downloaded {self.target_label(package_type, plugin_name)} update {available['version']}. Run wrapper github update apply.",
            data={"pending": pending},
        )

    async def cmd_apply(self, args):
        package_type, plugin_name, error = self.parse_target(args)
        if error:
            return CommandResult(ok=False, message=error)

        key = self.target_key(package_type, plugin_name)
        pending_all = self.load_json(self.state_path("pending"), {})
        pending = pending_all.get(key)

        if not pending:
            return CommandResult(ok=False, message=f"No downloaded update pending for {self.target_label(package_type, plugin_name)}.")

        if package_type == "wrapper":
            await asyncio.to_thread(self.apply_wrapper_update, pending)
            message = "Wrapper update applied. Run wrapper reload or restart WatchDog when ready."
        else:
            await asyncio.to_thread(self.apply_plugin_update, pending)
            loader = getattr(self.ctx, "plugin_loader", None)
            if loader:
                await loader.reload_plugin(plugin_name)
                await loader.run_plugin_hook(plugin_name, "on_wrapper_start")
            message = f"Plugin update applied and reloaded: {plugin_name}"

        installed = self.load_json(self.state_path("installed"), {})
        installed[key] = {
            "version": pending["version"],
            "tag_name": pending["tag_name"],
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save_json(self.state_path("installed"), installed)

        pending_all.pop(key, None)
        self.save_json(self.state_path("pending"), pending_all)

        available_all = self.load_json(self.state_path("available"), {})
        available_all.pop(key, None)
        self.save_json(self.state_path("available"), available_all)

        return CommandResult(message=message, data={"installed": installed[key]})

    async def cmd_clear(self, args):
        package_type, plugin_name, error = self.parse_target(args)
        if error:
            return CommandResult(ok=False, message=error)

        key = self.target_key(package_type, plugin_name)
        for name in ["available", "pending"]:
            data = self.load_json(self.state_path(name), {})
            data.pop(key, None)
            self.save_json(self.state_path(name), data)

        return CommandResult(message=f"Cleared GitHub update state for {self.target_label(package_type, plugin_name)}.")

    async def check_target(self, package_type, plugin_name):
        latest = await asyncio.to_thread(self.fetch_latest_release, package_type, plugin_name)
        if not latest:
            return None

        key = self.target_key(package_type, plugin_name)
        current_version = self.current_version(package_type, plugin_name)

        if self.compare_versions(latest["version"], current_version) <= 0:
            return None

        available = {
            **latest,
            "package_type": package_type,
            "plugin_name": plugin_name,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

        available_all = self.load_json(self.state_path("available"), {})
        available_all[key] = available
        self.save_json(self.state_path("available"), available_all)

        self.ctx.logger.warning(
            "[GitHubUpdate] Update available for %s: %s",
            self.target_label(package_type, plugin_name),
            latest["version"],
        )

        if self.settings.get("auto_download", False):
            await self.download_available(available)

        return available

    async def ensure_available(self, package_type, plugin_name):
        key = self.target_key(package_type, plugin_name)
        available_all = self.load_json(self.state_path("available"), {})
        available = available_all.get(key)
        if available:
            return available
        return await self.check_target(package_type, plugin_name)

    async def download_available(self, available):
        key = self.target_key(available["package_type"], available.get("plugin_name"))
        download_dir = self.update_dir() / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        file_name = available["asset_name"]
        zip_path = download_dir / f"{available['tag_name']}-{file_name}"
        await asyncio.to_thread(self.download_file, available["asset_url"], zip_path)

        pending = {
            **available,
            "zip_path": str(zip_path),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }

        pending_all = self.load_json(self.state_path("pending"), {})
        pending_all[key] = pending
        self.save_json(self.state_path("pending"), pending_all)

        return pending

    def fetch_latest_release(self, package_type, plugin_name):
        repo = self.settings.get("repository", "deadadm1n/BlackGrid")
        releases = self.github_json(f"https://api.github.com/repos/{repo}/releases")

        tag_prefix = self.tag_prefix(package_type, plugin_name)
        asset_pattern = self.asset_pattern(package_type, plugin_name)
        candidates = []

        for release in releases:
            tag_name = release.get("tag_name", "")
            if release.get("draft") or not tag_name.startswith(tag_prefix):
                continue

            version = tag_name[len(tag_prefix):]
            if not self.valid_version(version):
                continue

            asset = self.find_asset(release.get("assets", []), asset_pattern)
            if not asset:
                continue

            candidates.append({
                "version": version,
                "tag_name": tag_name,
                "release_url": release.get("html_url"),
                "asset_name": asset.get("name"),
                "asset_url": asset.get("browser_download_url"),
            })

        if not candidates:
            return None

        candidates.sort(key=lambda item: self.version_tuple(item["version"]), reverse=True)
        return candidates[0]

    def github_json(self, url):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "WatchDog-GitHub-Updater",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def find_asset(self, assets, pattern):
        for asset in assets:
            name = asset.get("name", "")
            if fnmatch.fnmatch(name, pattern):
                return asset
        return None

    def download_file(self, url, path):
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        request = urllib.request.Request(url, headers={"User-Agent": "WatchDog-GitHub-Updater"})
        with urllib.request.urlopen(request, timeout=180) as response:
            with open(tmp_path, "wb") as out:
                shutil.copyfileobj(response, out)
        tmp_path.replace(path)

    def apply_wrapper_update(self, pending):
        zip_path = Path(pending["zip_path"]).resolve()
        extract_dir = self.extract_update(zip_path, pending["tag_name"])
        package_root = extract_dir / "WatchDog"
        if not package_root.is_dir():
            raise RuntimeError("Wrapper package is missing WatchDog/ root folder")

        preserve = set(self.settings.get("wrapper", {}).get("preserve_paths", [
            ".env",
            "config/wrapper.yaml",
            "logs",
            "state",
            "backups",
            "downloads",
            "tmp",
            "atm11",
            "updates",
        ]))

        self.copy_tree_contents(package_root, self.ctx.base_dir, preserve)

    def apply_plugin_update(self, pending):
        plugin_name = pending.get("plugin_name")
        if not plugin_name:
            raise RuntimeError("Plugin update is missing plugin_name")

        zip_path = Path(pending["zip_path"]).resolve()
        extract_dir = self.extract_update(zip_path, pending["tag_name"])
        package_root = extract_dir / "WatchDog" / "plugins" / plugin_name
        if not package_root.is_dir():
            raise RuntimeError(f"Plugin package is missing WatchDog/plugins/{plugin_name}/")

        target = self.ctx.base_dir / "plugins" / plugin_name
        target.mkdir(parents=True, exist_ok=True)
        self.copy_tree_contents(package_root, target, set())

    def extract_update(self, zip_path, tag_name):
        extract_dir = self.update_dir() / "extracted" / tag_name
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)

        root = extract_dir.resolve()
        with zipfile.ZipFile(zip_path, "r") as archive:
            for member in archive.infolist():
                member_path = (root / member.filename).resolve()
                try:
                    member_path.relative_to(root)
                except ValueError:
                    raise RuntimeError(f"Unsafe zip path blocked: {member.filename}")
            archive.extractall(extract_dir)

        return extract_dir

    def copy_tree_contents(self, source, target, preserve):
        backup_root = self.backup_dir() / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_root.mkdir(parents=True, exist_ok=True)

        for src in source.rglob("*"):
            if src.is_dir():
                continue

            rel = src.relative_to(source).as_posix()
            if self.is_preserved(rel, preserve):
                continue

            dst = target / rel
            if dst.exists():
                backup_dst = backup_root / rel
                backup_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, backup_dst)

            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

            if dst.suffix == ".sh":
                dst.chmod(dst.stat().st_mode | 0o111)

    def is_preserved(self, rel, preserve):
        rel = rel.replace("\\", "/")
        for item in preserve:
            item = str(item).strip("/").replace("\\", "/")
            if rel == item or rel.startswith(item + "/"):
                return True
        return False

    def parse_target(self, args):
        if not args:
            return None, None, "Usage: wrapper github update <check|download|apply|clear> wrapper | plugin <name>"

        first = args[0].lower()
        if first == "wrapper":
            return "wrapper", None, None
        if first == "plugin":
            if len(args) < 2:
                return None, None, "Usage: wrapper github update plugin <name>"
            plugin_name = args[1]
            if not re.match(r"^[A-Za-z0-9_-]+$", plugin_name):
                return None, None, "Plugin name must contain only letters, numbers, underscores, or dashes."
            return "plugin", plugin_name, None
        return None, None, "Target must be wrapper or plugin <name>."

    def target_key(self, package_type, plugin_name):
        return "wrapper" if package_type == "wrapper" else f"plugin:{plugin_name}"

    def target_label(self, package_type, plugin_name):
        return "wrapper" if package_type == "wrapper" else f"plugin {plugin_name}"

    def tag_prefix(self, package_type, plugin_name):
        if package_type == "wrapper":
            return self.settings.get("wrapper", {}).get("tag_prefix", "watchdog-v")
        template = self.settings.get("plugins", {}).get("tag_prefix_template", "watchdog-plugin-{name}-v")
        return template.format(name=plugin_name)

    def asset_pattern(self, package_type, plugin_name):
        if package_type == "wrapper":
            return self.settings.get("wrapper", {}).get("asset_pattern", "watchdog-wrapper-*.zip")
        template = self.settings.get("plugins", {}).get("asset_pattern_template", "watchdog-plugin-{name}-*.zip")
        return template.format(name=plugin_name)

    def current_version(self, package_type, plugin_name):
        key = self.target_key(package_type, plugin_name)
        installed = self.load_json(self.state_path("installed"), {})
        if key in installed:
            return installed[key].get("version", "0.0.0")
        if package_type == "wrapper":
            return self.settings.get("wrapper", {}).get("current_version", "0.0.0")
        versions = self.settings.get("plugins", {}).get("current_versions", {})
        return versions.get(plugin_name, "0.0.0")

    def update_dir(self):
        path = self.ctx.resolve_path(self.settings.get("update_dir", "updates/github"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def backup_dir(self):
        path = self.ctx.resolve_path(self.settings.get("backup_dir", "backups/github_updates"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def state_path(self, name):
        return self.update_dir() / f"{name}.json"

    def load_json(self, path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def save_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(path)

    def valid_version(self, value):
        return bool(re.match(r"^\d+\.\d+\.\d+(-[A-Za-z0-9][A-Za-z0-9.-]*)?$", value))

    def version_tuple(self, value):
        main, _, suffix = value.partition("-")
        numbers = tuple(int(part) for part in main.split("."))
        stable = 1 if not suffix else 0
        return (*numbers, stable, suffix)

    def compare_versions(self, left, right):
        left_tuple = self.version_tuple(left)
        right_tuple = self.version_tuple(right)
        return (left_tuple > right_tuple) - (left_tuple < right_tuple)
