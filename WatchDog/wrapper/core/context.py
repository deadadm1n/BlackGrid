from pathlib import Path
from wrapper.core.commands import CommandRegistry
from wrapper.core.config import Config
from wrapper.core.events import EventBus
from wrapper.core.aetherreach_client import AetherReachClient

class WrapperContext:
    def __init__(self, config: Config, logger):
        self.shutdown_requested = False
        self.config = config
        self.logger = logger
        if config.path.parent.name == "config":
            self.base_dir = config.path.parent.parent.resolve()
        else:
            self.base_dir = config.path.parent.resolve()
        self.logs_dir = self._resolve_path(config.get('paths.logs_dir', 'logs'))
        self.state_dir = self._resolve_path(config.get('paths.state_dir', 'state'))
        self.backups_dir = self._resolve_path(config.get('paths.backups_dir', 'backups'))
        self.downloads_dir = self._resolve_path(config.get('paths.downloads_dir', 'downloads'))
        self.tmp_dir = self._resolve_path(config.get('paths.tmp_dir', 'tmp'))
        self.server_dir = self._resolve_path(config.get("server.directory", "server"))
        
        self.minecraft_console_log = self.logs_dir / "minecraft_console.log"
        
        for path in [
            self.logs_dir,
            self.state_dir,
            self.backups_dir,
            self.downloads_dir,
            self.tmp_dir,
        ]:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise RuntimeError(f"Cannot create WatchDog directory {path}: {exc}") from exc
        
        self.server_process = None
        self.server_output_task = None
        self.server_stop_requested = False
        self.event_bus = EventBus(logger)
        self.command_registry = CommandRegistry(logger)
        self.aetherreach = AetherReachClient(config, logger)

    def _resolve_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (self.base_dir / path).resolve()

    def resolve_path(self, value: str) -> Path:
        return self._resolve_path(value)

    def state_file(self, name: str) -> Path:
        return self.state_dir / name

    def log_file(self, name: str) -> Path:
        return self.logs_dir / name
