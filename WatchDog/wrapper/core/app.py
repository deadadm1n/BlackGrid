import asyncio
import os
import sys
from pathlib import Path

from wrapper.core.commands import CommandResult
from wrapper.core.config import Config
from wrapper.core.context import WrapperContext
from wrapper.core.logger import setup_logger
from wrapper.core.plugin_loader import PluginLoader
from wrapper.core.server_process import ServerProcess
from wrapper.core.minecraft_event_receiver import MinecraftEventReceiver
from wrapper.core.web_panel import WebPanel


class WrapperApp:
    def __init__(self, config_path: str = "config/wrapper.yaml"):
        config_path = Path(config_path)
        if not config_path.is_absolute():
            config_path = Path(__file__).resolve().parents[2] / config_path
        self.config_path = config_path

    def register_core_commands(self, ctx, plugins: PluginLoader):
        registry = ctx.command_registry

        def current_server_state():
            server = getattr(ctx, "server_process", None)
            process = getattr(server, "process", None) if server else None
            process_alive = bool(process and process.returncode is None)
            startup_validated = bool(getattr(server, "startup_validated", False))
            return server, process, process_alive, startup_validated

        async def start_server_controller():
            _server, _process, process_alive, _startup_validated = current_server_state()
            if process_alive:
                return CommandResult(ok=False, message="ATM11 server is already running")

            ctx.server_stop_requested = False

            server = ServerProcess(ctx)
            started = await server.start()

            if not started:
                await plugins.run_hook("on_server_failed_start", RuntimeError("Manual server start failed startup validation"))
                return CommandResult(ok=False, message="ATM11 server failed startup validation")

            await plugins.run_hook("after_server_start")
            ctx.server_output_task = asyncio.create_task(ctx.server_process.read_output_forever())
            return CommandResult(message="ATM11 server started")

        async def stop_server_controller():
            server, _process, process_alive, _startup_validated = current_server_state()
            if not server or not process_alive:
                ctx.server_stop_requested = True
                return CommandResult(message="ATM11 server is already stopped")

            ctx.server_stop_requested = True
            await server.stop()
            return CommandResult(message="ATM11 server stopped; watchdog is still running")

        async def restart_server_controller():
            server, _process, process_alive, _startup_validated = current_server_state()

            if process_alive:
                ctx.server_stop_requested = True
                await server.stop()

            return await start_server_controller()

        async def cmd_help(args):
            return CommandResult(
                message="Available watchdog commands",
                data={"commands": registry.list_commands()},
            )

        async def cmd_status(args):
            _server, _process, process_alive, startup_validated = current_server_state()
            bridge_status = {
                "ok": False,
                "bridge": "starting" if process_alive and not startup_validated else "offline",
            }
            if startup_validated:
                bridge_status = await ctx.aetherreach.status()
                if bridge_status is None:
                    bridge_status = {"ok": False, "bridge": "offline"}
            return CommandResult(
                message="watchdog status",
                data={
                    "watchdog": "online",
                    "server_running": process_alive,
                    "startup_validated": startup_validated,
                    "plugins": plugins.list_plugins(),
                    "aetherreach": bridge_status,
                },
            )

        async def cmd_server_status(args):
            _server, process, process_alive, startup_validated = current_server_state()
            return CommandResult(
                message="ATM11 server status",
                data={
                    "running": process_alive,
                    "startup_validated": startup_validated,
                    "pid": getattr(process, "pid", None) if process else None,
                    "manual_stop_requested": bool(getattr(ctx, "server_stop_requested", False)),
                    "server_dir": str(ctx.server_dir),
                },
            )

        async def cmd_plugins(args):
            return CommandResult(
                message="Loaded plugins",
                data={"plugins": plugins.list_plugins()},
            )

        async def cmd_plugin_reload(args):
            if not args:
                return CommandResult(ok=False, message="Usage: watchdog plugin reload <name>")

            plugin_name = args[0]
            plugin = await plugins.reload_plugin(plugin_name)

            await plugins.run_plugin_hook(plugin_name, "on_wrapper_start")
            if getattr(ctx, "server_process", None):
                process = getattr(ctx.server_process, "process", None)
                if process and process.returncode is None:
                    await plugins.run_plugin_hook(plugin_name, "after_server_start")

            return CommandResult(
                message=f"Reloaded plugin: {plugin_name}",
                data={"plugin": plugin_name, "class": type(plugin).__name__},
            )

        async def cmd_plugins_reload(args):
            await plugins.reload_all_plugins()
            await plugins.run_hook("on_wrapper_start")
            if getattr(ctx, "server_process", None):
                process = getattr(ctx.server_process, "process", None)
                if process and process.returncode is None:
                    await plugins.run_hook("after_server_start")

            return CommandResult(
                message="Reloaded all enabled plugins",
                data={"plugins": plugins.list_plugins()},
            )

        async def cmd_bridge_status(args):
            status = await ctx.aetherreach.status()
            return CommandResult(
                ok=status is not None,
                message="Helper bridge status" if status else "Helper bridge is unavailable",
                data={"aetherreach": status},
            )

        async def cmd_bridge_veil(args):
            message = " ".join(args).strip()
            if not message:
                return CommandResult(ok=False, message="Usage: watchdog bridge veil <message>")
            delivered = await ctx.aetherreach.veil(message)
            return CommandResult(ok=delivered, message="Veil message sent" if delivered else "Veil message failed")

        async def cmd_bridge_broadcast(args):
            message = " ".join(args).strip()
            if not message:
                return CommandResult(ok=False, message="Usage: watchdog bridge broadcast <message>")
            delivered = await ctx.aetherreach.broadcast(message)
            return CommandResult(ok=delivered, message="Broadcast sent" if delivered else "Broadcast failed")

        async def cmd_stop(args):
            ctx.shutdown_requested = True
            if ctx.server_process:
                await ctx.server_process.stop()
            return CommandResult(message="watchdog shutdown requested")

        async def cmd_server_start(args):
            return await start_server_controller()

        async def cmd_server_stop(args):
            return await stop_server_controller()

        async def cmd_server_restart(args):
            result = await restart_server_controller()
            if result.ok:
                result.message = "Minecraft server restarted"
            return result

        async def cmd_server_kill(args):
            server, _process, process_alive, _startup_validated = current_server_state()
            if not server or not process_alive:
                ctx.server_stop_requested = True
                return CommandResult(message="Minecraft server is already stopped")

            ctx.server_stop_requested = True
            await server.kill()
            return CommandResult(message="Minecraft server process killed; watchdog is still running")

        async def cmd_server_command(args):
            command = " ".join(args).strip()
            if not command:
                return CommandResult(ok=False, message="Usage: watchdog server command <minecraft command>")

            _server, _process, process_alive, _startup_validated = current_server_state()
            if not process_alive:
                return CommandResult(ok=False, message="Minecraft server is not running")

            await ctx.server_process.send_command(command)
            return CommandResult(message=f"Sent Minecraft command: {command}")

        async def cmd_reload(args):
            ctx.shutdown_requested = True
            if ctx.server_process:
                await ctx.server_process.stop()
            os.execv(sys.executable, [sys.executable] + sys.argv)

        registry.register("help", cmd_help, "List registered watchdog commands", usage="watchdog help")
        registry.register("commands", cmd_help, "List registered watchdog commands", usage="watchdog commands")
        registry.register("status", cmd_status, "Show WatchDog, server, plugin, and bridge status", usage="watchdog status")
        registry.register("plugins", cmd_plugins, "List loaded plugins", usage="watchdog plugins")
        registry.register("plugin reload", cmd_plugin_reload, "Hot-load or reload one plugin", usage="watchdog plugin reload <name>")
        registry.register("reload-plugin", cmd_plugin_reload, "Compatibility alias for plugin reload", usage="watchdog reload-plugin <name>")
        registry.register("plugins reload", cmd_plugins_reload, "Reload all enabled plugins", usage="watchdog plugins reload")
        registry.register("reload-plugins", cmd_plugins_reload, "Compatibility alias for plugins reload", usage="watchdog reload-plugins")
        registry.register("bridge status", cmd_bridge_status, "Show helper bridge status", usage="watchdog bridge status")
        registry.register("bridge veil", cmd_bridge_veil, "Send a helper message in-game", usage="watchdog bridge veil <message>")
        registry.register("bridge broadcast", cmd_bridge_broadcast, "Broadcast a message in-game", usage="watchdog bridge broadcast <message>")
        registry.register("server status", cmd_server_status, "Show Minecraft server status", usage="watchdog server status")
        registry.register("server start", cmd_server_start, "Start Minecraft while keeping Watchdog alive", usage="watchdog server start")
        registry.register("server stop", cmd_server_stop, "Gracefully stop Minecraft while keeping Watchdog alive", usage="watchdog server stop")
        registry.register("server restart", cmd_server_restart, "Gracefully restart Minecraft while keeping Watchdog alive", usage="watchdog server restart")
        registry.register("server kill", cmd_server_kill, "Force-kill Minecraft while keeping Watchdog alive", usage="watchdog server kill")
        registry.register("server command", cmd_server_command, "Send a Minecraft command", usage="watchdog server command <minecraft command>")
        registry.register("restart", cmd_reload, "Restart the full WatchDog process", usage="watchdog restart")
        registry.register("stop", cmd_stop, "Stop Minecraft and shut down Watchdog", usage="watchdog stop")
        registry.register("shutdown", cmd_stop, "Stop Minecraft and shut down Watchdog", usage="watchdog shutdown")
        registry.register("quit", cmd_stop, "Stop Minecraft and shut down Watchdog", usage="watchdog quit")
        registry.register("exit", cmd_stop, "Stop Minecraft and shut down Watchdog", usage="watchdog exit")
        registry.register("reload", cmd_reload, "Restart the full watchdog process", usage="watchdog reload")

    async def console_loop(self, ctx, plugins: PluginLoader):
        logger = ctx.logger
        logger.info("Console input enabled. Type Minecraft commands here.")
        logger.info("watchdog commands: watchdog status | watchdog server status | watchdog server stop | watchdog server start | watchdog server restart | watchdog stop")

        while True:
            try:
                command = await asyncio.to_thread(input)
            except EOFError:
                logger.info("Console input closed; waiting for server process to exit")
                if ctx.server_process:
                    await ctx.server_process.wait()
                break

            command = command.strip()

            if not command:
                continue

            lowered = command.lower()

            if lowered.startswith("watchdog") or lowered.startswith("wrapper"):
                try:
                    result = await ctx.command_registry.execute(command)
                except Exception as exc:
                    logger.exception("watchdog command failed: %s", command)
                    result = CommandResult(
                        ok=False,
                        message=f"watchdog command failed: {exc}",
                    )

                level = logger.info if result.ok else logger.warning
                level(
                    "%s%s",
                    result.message,
                    f" | {result.data}" if result.data else "",
                )

                if ctx.shutdown_requested:
                    break
                continue

            if not ctx.server_process:
                logger.warning("ATM11 server controller is not available")
                continue

            await ctx.server_process.send_command(command)

    async def run(self):
        config = Config(self.config_path)

        logs_dir = Path(config.get("paths.logs_dir", "logs"))
        if not logs_dir.is_absolute():
            logs_dir = config.path.parent.parent / logs_dir if config.path.parent.name == "config" else config.path.parent / logs_dir

        logger = setup_logger(
            logs_dir=logs_dir,
            debug=bool(config.get("wrapper.debug", False)),
        )

        ctx = WrapperContext(config=config, logger=logger)
        plugins = PluginLoader(ctx)
        ctx.plugin_loader = plugins
        ctx.minecraft_event_receiver = None
        ctx.web_panel = None

        try:
            logger.info("WatchDog booting: %s", config.get("wrapper.name", "Watchdog"))

            self.register_core_commands(ctx, plugins)
            await plugins.load_plugins()
            await plugins.register_events()
            await plugins.register_commands()
            
            receiver_cfg = config.get("bridges.minecraft_events", config.get("minecraft_event_receiver", {}))
            
            if receiver_cfg.get("enabled", True):
                ctx.minecraft_event_receiver = MinecraftEventReceiver(
                    ctx=ctx,
                    host=receiver_cfg.get("host", "127.0.0.1"),
                    port=int(receiver_cfg.get("port", 25591)),
                    token=receiver_cfg.get("token", ""),
                )
                await ctx.minecraft_event_receiver.start()
            
            web_cfg = config.get("web_panel", {})
            
            if web_cfg.get("enabled", False):
                ctx.web_panel = WebPanel(
                    ctx=ctx,
                    host=web_cfg.get("host", "127.0.0.1"),
                    port=int(web_cfg.get("port", 8080)),
                    token=web_cfg.get("token", ""),
                )
                await ctx.web_panel.start()
            
            await plugins.run_hook("on_wrapper_start")
            await plugins.run_hook("before_server_start")

            server = ServerProcess(ctx)
            started = await server.start()

            if started:
                await plugins.run_hook("after_server_start")
                logger.info("watchdog startup complete")

                ctx.server_output_task = asyncio.create_task(ctx.server_process.read_output_forever())

                try:
                    await self.console_loop(ctx, plugins)

                except KeyboardInterrupt:
                    logger.info("Shutdown requested by CTRL+C")
                    ctx.shutdown_requested = True
                    await ctx.server_process.stop()

                finally:
                    output_task = getattr(ctx, "server_output_task", None)
                    if output_task:
                        output_task.cancel()
                    try:
                        if output_task:
                            await output_task
                    except asyncio.CancelledError:
                        pass

                return

            error = RuntimeError("Server failed startup validation")
            await plugins.run_hook("on_server_failed_start", error)

            if getattr(server, "last_start_failure_reason", None) == "world_locked":
                raise RuntimeError(
                    "Server world is already locked by another Minecraft process. "
                    "Stop the existing server before starting the watchdog."
                )

            logger.info("Trying server start again after failure handling")

            server = ServerProcess(ctx)
            restarted = await server.start()

            if not restarted:
                raise RuntimeError("Server failed to start after rollback/failure handling")

            await plugins.run_hook("after_server_start")
            logger.info("watchdog startup complete after rollback")

            ctx.server_output_task = asyncio.create_task(ctx.server_process.read_output_forever())

            try:
                await self.console_loop(ctx, plugins)

            except KeyboardInterrupt:
                logger.info("Shutdown requested by CTRL+C")
                ctx.shutdown_requested = True
                await ctx.server_process.stop()

            finally:
                output_task = getattr(ctx, "server_output_task", None)
                if output_task:
                    output_task.cancel()
                try:
                    if output_task:
                        await output_task
                except asyncio.CancelledError:
                    pass

            return

        except KeyboardInterrupt:
            logger.info("watchdog interrupted")
            if ctx.server_process:
                ctx.shutdown_requested = True
                await ctx.server_process.stop()

        except Exception:
            logger.exception("watchdog failed")
            if ctx.server_process:
                ctx.shutdown_requested = True
                await ctx.server_process.stop()
            raise

        finally:
            if getattr(ctx, "web_panel", None):
                await ctx.web_panel.stop()
        
            if getattr(ctx, "minecraft_event_receiver", None):
                await ctx.minecraft_event_receiver.stop()
        
            await plugins.run_hook("on_wrapper_stop")
