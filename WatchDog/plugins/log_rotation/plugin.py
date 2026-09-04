from datetime import datetime, timedelta
from pathlib import Path
import shutil

from wrapper.core.plugin_base import WrapperPlugin


class Plugin(WrapperPlugin):
    name = "log_rotation"

    def __init__(self, settings=None):
        super().__init__(settings=settings)
        self.has_rotated_this_runtime = False

    async def on_wrapper_start(self, ctx):
        keep_days = int(self.settings.get("keep_days", 7))
        rotate_on_start = bool(self.settings.get("rotate_on_wrapper_start", True))

        mc_logs_dir = ctx.resolve_path(
            self.settings.get("minecraft_logs_dir", "atm11/logs")
        )

        wrapper_archive = ctx.logs_dir / "archive"
        mc_archive = mc_logs_dir / "archive"

        if rotate_on_start and not self.has_rotated_this_runtime:
            self.rotate_wrapper_log(ctx.logs_dir / "wrapper.log", wrapper_archive, ctx.logger)
            self.rotate_minecraft_logs(mc_logs_dir, mc_archive, ctx.logger)
            self.has_rotated_this_runtime = True
            ctx.logger.info("[LogRotation] Active logs rotated")

        self.cleanup_old(wrapper_archive, keep_days)
        self.cleanup_old(mc_archive, keep_days)

        ctx.logger.info("[LogRotation] Cleanup complete. Keeping %s days.", keep_days)

    async def on_wrapper_stop(self, ctx):
        # No active rotation here. Shutdown logs are still being written.
        pass

    def rotate_wrapper_log(self, log_file: Path, archive_dir: Path, logger=None):
        if not log_file.exists() or log_file.stat().st_size == 0:
            return

        archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target = archive_dir / f"wrapper_{timestamp}.log"

        self.copy_log(log_file, target, logger)
        self.truncate_live_log(log_file, logger)

    def truncate_live_log(self, log_file: Path, logger=None):
        # FileHandler keeps an open handle + offset, so a bare truncate would
        # leave a sparse hole. Reopen the handler stream after truncating.
        import logging

        actual = None
        if logger is not None:
            actual = logger
            while hasattr(actual, "logger"):
                actual = actual.logger

        handlers = getattr(actual, "handlers", []) if actual is not None else []
        reopened = False
        for handler in handlers:
            if not isinstance(handler, logging.FileHandler):
                continue
            try:
                if Path(handler.baseFilename).resolve() != log_file.resolve():
                    continue
            except OSError:
                continue
            handler.acquire()
            try:
                handler.flush()
                if handler.stream:
                    try:
                        handler.stream.close()
                    except Exception:
                        pass
                try:
                    with log_file.open("w", encoding="utf-8"):
                        pass
                except OSError as exc:
                    if logger:
                        logger.warning("[LogRotation] Could not truncate %s: %s", log_file, exc)
                    handler.setStream(log_file.open("a", encoding="utf-8"))
                    continue
                handler.setStream(log_file.open("a", encoding="utf-8"))
                reopened = True
            finally:
                handler.release()

        if not reopened:
            # No live handler owns this file; plain truncate is safe.
            try:
                with log_file.open("w", encoding="utf-8"):
                    pass
            except OSError as exc:
                if logger:
                    logger.warning("[LogRotation] Could not truncate %s: %s", log_file, exc)

    def rotate_minecraft_logs(self, logs_dir: Path, archive_dir: Path, logger=None):
        if not logs_dir.exists():
            return

        archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        latest = logs_dir / "latest.log"

        if latest.exists() and latest.stat().st_size > 0:
            self.copy_log(latest, archive_dir / f"latest_{timestamp}.log", logger)

        for file in logs_dir.iterdir():
            if not file.is_file():
                continue

            if file.name == "latest.log":
                continue

            if file.suffix == ".log":
                target = archive_dir / f"{file.stem}_{timestamp}.log"
                self.move_log(file, target, logger)

    def copy_log(self, source: Path, target: Path, logger=None):
        try:
            shutil.copy2(source, target)
        except PermissionError:
            if logger:
                logger.warning("[LogRotation] Skipping locked log file: %s", source)
        except OSError as exc:
            if logger:
                logger.warning("[LogRotation] Could not copy log file %s: %s", source, exc)

    def move_log(self, source: Path, target: Path, logger=None):
        try:
            shutil.move(str(source), str(target))
        except PermissionError:
            if logger:
                logger.warning("[LogRotation] Skipping locked log file: %s", source)
        except OSError as exc:
            if logger:
                logger.warning("[LogRotation] Could not rotate log file %s: %s", source, exc)

    def cleanup_old(self, archive_dir: Path, keep_days: int):
        if not archive_dir.exists():
            return

        cutoff = datetime.now() - timedelta(days=keep_days)

        for file in archive_dir.iterdir():
            if not file.is_file():
                continue

            modified = datetime.fromtimestamp(file.stat().st_mtime)

            if modified < cutoff:
                file.unlink()
