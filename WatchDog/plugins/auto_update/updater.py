from __future__ import annotations
import datetime as dt, json, shutil, tempfile
from pathlib import Path
import requests
from .patcher import apply_patches
from .safe_extract import safe_extract_zip

INSTALLED_VERSION_FILE = 'installed_version.json'
PENDING_UPDATE_FILE = 'pending_update.json'

class AutoUpdatePluginCore:
    def __init__(self, settings: dict):
        self.settings = settings

    async def before_server_start(self, ctx):
        if not self.settings.get('update_enabled', False):
            ctx.logger.info('[AutoUpdate] Update checks disabled')
            return
        latest = self.get_latest_version()
        installed = self.read_json(ctx.state_file(INSTALLED_VERSION_FILE), default={})
        latest_id = latest.get('file_id')
        installed_id = installed.get('file_id')
        ctx.logger.info('[AutoUpdate] Installed=%s Latest=%s', installed_id, latest_id)
        if latest_id == installed_id:
            ctx.logger.info('[AutoUpdate] No update found')
            return
        ctx.logger.info('[AutoUpdate] Update found: %s', latest.get('display_name'))
        backup_path = self.create_backup(ctx)
        pending = {
            'from_file_id': installed_id,
            'to_file_id': latest_id,
            'display_name': latest.get('display_name'),
            'download_url': latest.get('download_url'),
            'backup_path': str(backup_path),
            'started_at': dt.datetime.now(dt.UTC).isoformat(),
            'reason': 'Pending startup validation',
        }
        try:
            self.perform_update(ctx, latest)
            self.write_json(ctx.state_file(PENDING_UPDATE_FILE), pending)
            ctx.logger.info('[AutoUpdate] Pending update written')
        except Exception as e:
            ctx.logger.exception('[AutoUpdate] Update failed before startup; rolling back')
            self.rollback(ctx, backup_path)
            self.write_update_log(ctx, f'Update failed before startup. Rolled back. Reason: {e}')
            raise

    async def after_server_start(self, ctx):
        pending_file = ctx.state_file(PENDING_UPDATE_FILE)
        if not pending_file.exists():
            return
        pending = self.read_json(pending_file, default={})
        installed = {
            'file_id': pending.get('to_file_id'),
            'display_name': pending.get('display_name'),
            'installed_at': dt.datetime.now(dt.UTC).isoformat(),
        }
        self.write_json(ctx.state_file(INSTALLED_VERSION_FILE), installed)
        pending_file.unlink(missing_ok=True)
        self.write_update_log(ctx, f"Update succeeded: {pending.get('from_file_id')} -> {pending.get('to_file_id')}")
        ctx.logger.info('[AutoUpdate] Update committed successfully')

    async def on_server_failed_start(self, ctx, error):
        pending_file = ctx.state_file(PENDING_UPDATE_FILE)
        if not pending_file.exists():
            ctx.logger.info('[AutoUpdate] No pending update to roll back')
            return
        pending = self.read_json(pending_file, default={})
        backup_path = Path(pending.get('backup_path', ''))
        ctx.logger.error('[AutoUpdate] Startup failed after update; rolling back')
        self.rollback(ctx, backup_path)
        msg = f"Update reverted. From={pending.get('from_file_id')} To={pending.get('to_file_id')} Reason={error}"
        self.write_update_log(ctx, msg)
        pending_file.unlink(missing_ok=True)

    def get_latest_version(self) -> dict:
        mode = self.settings.get('mode', 'manual_url')
        if mode == 'manual_url':
            return {
                'file_id': self.settings.get('latest_file_id', 0),
                'display_name': self.settings.get('latest_display_name', 'Manual update'),
                'download_url': self.settings.get('download_url', ''),
            }
        if mode == 'curseforge_api':
            raise NotImplementedError('CurseForge API mode needs your API key/project setup.')
        raise ValueError(f'Unknown auto_update mode: {mode}')

    def perform_update(self, ctx, latest: dict):
        download_url = latest.get('download_url')
        if not download_url:
            raise ValueError('download_url is empty')
        with tempfile.TemporaryDirectory(dir=ctx.tmp_dir) as tmp:
            tmp_dir = Path(tmp)
            zip_path = tmp_dir / 'server-pack.zip'
            extracted_dir = tmp_dir / 'extracted'
            extracted_dir.mkdir(parents=True, exist_ok=True)
            self.download_file(ctx, download_url, zip_path)
            safe_extract_zip(zip_path, extracted_dir)
            source_root = self.find_server_pack_root(extracted_dir)
            self.copy_over(ctx, source_root, ctx.server_dir)
            patch_file = ctx.resolve_path(self.settings.get('patch_file', 'plugins/auto_update/patches.yaml'))
            apply_patches(server_dir=ctx.server_dir, patch_yaml=patch_file, logger=ctx.logger)

    def download_file(self, ctx, url: str, destination: Path):
        ctx.logger.info('[AutoUpdate] Downloading: %s', url)
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with destination.open('wb') as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

    def find_server_pack_root(self, extracted_dir: Path) -> Path:
        children = list(extracted_dir.iterdir())
        if len(children) == 1 and children[0].is_dir():
            return children[0]
        return extracted_dir

    def copy_over(self, ctx, source: Path, target: Path):
        ctx.logger.info('[AutoUpdate] Copying update files over server folder')
        target.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            dst = target / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)

    def create_backup(self, ctx) -> Path:
        timestamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = ctx.backups_dir / f'server-backup-{timestamp}'
        ctx.logger.info('[AutoUpdate] Creating backup: %s', backup_path)
        shutil.copytree(ctx.server_dir, backup_path, ignore=shutil.ignore_patterns('logs','crash-reports','*.log'))
        return backup_path

    def rollback(self, ctx, backup_path: Path):
        if not backup_path.exists():
            raise FileNotFoundError(f'Rollback backup not found: {backup_path}')
        ctx.logger.warning('[AutoUpdate] Rolling back server from: %s', backup_path)
        if ctx.server_dir.exists():
            shutil.rmtree(ctx.server_dir)
        shutil.copytree(backup_path, ctx.server_dir)

    def read_json(self, path: Path, default):
        if not path.exists(): return default
        return json.loads(path.read_text(encoding='utf-8'))

    def write_json(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=4), encoding='utf-8')

    def write_update_log(self, ctx, message: str):
        line = f'{dt.datetime.now().isoformat()} | {message}\n'
        with ctx.log_file('update.log').open('a', encoding='utf-8') as f:
            f.write(line)
