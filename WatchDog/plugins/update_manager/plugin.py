import asyncio
import fnmatch
import json
import re
import shutil
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from wrapper.core.commands import CommandResult
from wrapper.core.plugin_base import WrapperPlugin
from wrapper.core.server_process import ServerProcess


class Plugin(WrapperPlugin):
    name = "update_manager"

    def __init__(self, settings=None):
        super().__init__(settings=settings)
        self.ctx = None

    async def on_wrapper_start(self, ctx):
        self.ctx = ctx

    async def register_commands(self, ctx):
        self.ctx = ctx
        ctx.command_registry.register(
            "update",
            self.cmd_update,
            "Update WatchDog and the WatchDog Helper jar from GitHub releases",
            owner=self.name,
            usage="watchdog update [status|check|download|apply]",
        )

    async def cmd_update(self, args):
        action = args[0].lower() if args else "run"

        if action == "status":
            return CommandResult(
                message="Update status",
                data={
                    "installed": self.load_json(self.state_path("installed"), {}),
                    "available": self.load_json(self.state_path("available"), {}),
                    "pending": self.load_json(self.state_path("pending"), {}),
                    "targets": self.targets(),
                },
            )

        if action == "check":
            available = await self.check_all()
            return CommandResult(
                message=self.summary("Checked for updates", available),
                data={"available": available},
            )

        if action == "download":
            available = await self.check_all()
            pending = await self.download_all(available)
            return CommandResult(
                message=self.summary("Downloaded updates", pending),
                data={"pending": pending},
            )

        if action in {"apply", "run"}:
            available = await self.check_all()
            pending = await self.download_all(available)
            applied = await self.apply_all(pending)
            return CommandResult(
                message=self.summary("Applied updates", applied),
                data={"applied": applied},
            )

        return CommandResult(ok=False, message="Usage: watchdog update [status|check|download|apply]")

    async def check_all(self):
        available = {}
        for name, target in self.targets().items():
            latest = await asyncio.to_thread(self.fetch_latest_release, name, target)
            if not latest:
                continue

            current = self.current_version(name, target)
            if self.compare_versions(latest["version"], current) <= 0:
                continue

            available[name] = {**latest, "target": name, "type": target.get("type")}

        self.save_json(self.state_path("available"), available)
        return available

    async def download_all(self, available):
        if not available:
            available = self.load_json(self.state_path("available"), {})

        pending = self.load_json(self.state_path("pending"), {})
        download_dir = self.update_dir() / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        for name, item in available.items():
            file_name = item["asset_name"]
            target_path = download_dir / f"{item['tag_name']}-{file_name}"
            await asyncio.to_thread(self.download_file, item["asset_url"], target_path)
            pending[name] = {
                **item,
                "download_path": str(target_path),
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            }

        self.save_json(self.state_path("pending"), pending)
        return pending

    async def apply_all(self, pending):
        if not pending:
            pending = self.load_json(self.state_path("pending"), {})

        if not pending:
            return {}

        targets = self.targets()
        applied = {}
        helper_pending = [
            (name, item, targets[name])
            for name, item in pending.items()
            if targets.get(name, {}).get("type") == "minecraft_mod"
        ]
        wrapper_pending = [
            (name, item, targets[name])
            for name, item in pending.items()
            if targets.get(name, {}).get("type") == "wrapper"
        ]

        server_was_running = await self.stop_server_if_needed(bool(helper_pending))

        try:
            for name, item, target in helper_pending:
                await asyncio.to_thread(self.apply_minecraft_mod, item, target)
                applied[name] = self.applied_record(item)

            for name, item, target in wrapper_pending:
                await asyncio.to_thread(self.apply_wrapper, item, target)
                applied[name] = self.applied_record(item)

            installed = self.load_json(self.state_path("installed"), {})
            installed.update(applied)
            self.save_json(self.state_path("installed"), installed)
            self.save_json(self.state_path("pending"), {})
            self.save_json(self.state_path("available"), {})
        except Exception:
            self.ctx.logger.exception("[UpdateManager] Apply failed; attempting to restart server")
            if server_was_running:
                try:
                    await self.restart_server_after_update()
                except Exception:
                    self.ctx.logger.exception("[UpdateManager] Restart after failed apply also failed")
            raise

        if server_was_running:
            await self.restart_server_after_update()

        return applied

    async def stop_server_if_needed(self, needed):
        if not needed:
            return False

        server = getattr(self.ctx, "server_process", None)
        process = getattr(server, "process", None) if server else None
        running = bool(process and process.returncode is None)

        if running:
            self.ctx.logger.warning("[UpdateManager] Stopping server before WatchDog Helper jar update")
            self.ctx.server_stop_requested = True
            await server.stop()
            self.ctx.server_stop_requested = False

        return running

    async def restart_server_after_update(self):
        self.ctx.logger.warning("[UpdateManager] Restarting server after WatchDog Helper jar update")
        server = ServerProcess(self.ctx)
        started = await server.start()
        if not started:
            raise RuntimeError("Server failed startup validation after update")

        loader = getattr(self.ctx, "plugin_loader", None)
        if loader:
            await loader.run_hook("after_server_start")

        self.ctx.server_output_task = asyncio.create_task(self.ctx.server_process.read_output_forever())

    def apply_wrapper(self, item, target):
        package_root = self.extract_zip(Path(item["download_path"]), item["tag_name"]) / "WatchDog"
        if not package_root.is_dir():
            raise RuntimeError("WatchDog watchdog package is missing WatchDog/ root folder")

        preserve = set(target.get("preserve_paths", []))
        self.copy_tree_contents(package_root, self.ctx.base_dir, preserve)

    def apply_minecraft_mod(self, item, target):
        source = Path(item["download_path"]).resolve()
        install_dir = self.ctx.resolve_path(target.get("install_dir", "atm11/mods"))
        install_dir.mkdir(parents=True, exist_ok=True)

        backup_dir = self.backup_dir() / item["tag_name"]
        backup_dir.mkdir(parents=True, exist_ok=True)

        replace_patterns = target.get("replace_patterns") or [target.get("replace_pattern", item["asset_name"])]
        for pattern in replace_patterns:
            for old in install_dir.glob(pattern):
                if old.is_file():
                    shutil.copy2(old, backup_dir / old.name)
                    old.unlink()

        final_name = target.get("install_name") or item["asset_name"]
        shutil.copy2(source, install_dir / final_name)

    def fetch_latest_release(self, target_name, target):
        repo = str(self.settings.get("repository", "")).strip()
        if not repo:
            if self.ctx:
                self.ctx.logger.debug("[UpdateManager] No GitHub repository configured")
            return None

        releases = self.github_json(f"https://api.github.com/repos/{repo}/releases")
        tag_prefix = target["tag_prefix"]
        asset_pattern = target["asset_pattern"]
        candidates = []

        for release in releases:
            tag = release.get("tag_name", "")
            if release.get("draft") or not tag.startswith(tag_prefix):
                continue

            version = tag[len(tag_prefix):]
            if not self.valid_version(version):
                continue

            asset = self.find_asset(release.get("assets", []), asset_pattern)
            if not asset:
                continue

            candidates.append({
                "version": version,
                "tag_name": tag,
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
                "User-Agent": "WatchDog-UpdateManager",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def download_file(self, url, path):
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        request = urllib.request.Request(url, headers={"User-Agent": "WatchDog-UpdateManager"})
        with urllib.request.urlopen(request, timeout=180) as response:
            with open(tmp_path, "wb") as out:
                shutil.copyfileobj(response, out)
        tmp_path.replace(path)

    def extract_zip(self, zip_path, tag_name):
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

    def targets(self):
        return self.settings.get("targets", {})

    def current_version(self, name, target):
        installed = self.load_json(self.state_path("installed"), {})
        if name in installed:
            return installed[name].get("version", "0.0.0")
        return target.get("current_version", "0.0.0")

    def applied_record(self, item):
        return {
            "version": item["version"],
            "tag_name": item["tag_name"],
            "asset_name": item["asset_name"],
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }

    def update_dir(self):
        path = self.ctx.resolve_path(self.settings.get("update_dir", "updates/manager"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def backup_dir(self):
        path = self.ctx.resolve_path(self.settings.get("backup_dir", "backups/update_manager"))
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

    def find_asset(self, assets, pattern):
        for asset in assets:
            if fnmatch.fnmatch(asset.get("name", ""), pattern):
                return asset
        return None

    def is_preserved(self, rel, preserve):
        rel = rel.replace("\\", "/")
        for item in preserve:
            item = str(item).strip("/").replace("\\", "/")
            if rel == item or rel.startswith(item + "/"):
                return True
        return False

    def summary(self, prefix, items):
        if not items:
            return f"{prefix}: nothing to do."
        names = ", ".join(f"{name}={item.get('version')}" for name, item in items.items())
        return f"{prefix}: {names}"

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
