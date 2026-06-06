import asyncio
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from plugins.atm11_auto_update.plugin import WrapperPlugin as ATM11UpdatePlugin
from plugins.auto_restart.plugin import Plugin as AutoRestartPlugin
from plugins.discord_bot.plugin import Plugin as DiscordBotPlugin
from plugins.auto_update.safe_extract import safe_extract_zip
from plugins.log_rotation.plugin import Plugin as LogRotationPlugin
from wrapper.core.commands import CommandRegistry
from wrapper.core.app import WrapperApp
from wrapper.core.console_parser import parse_console_line
from wrapper.core.config import Config
from wrapper.core.context import WrapperContext
from wrapper.core.events import ChatMessageEvent, ConsoleLineEvent, EventBus, ServerCrashEvent
from wrapper.core.minecraft_event_receiver import MinecraftEventReceiver
from wrapper.core.plugin_loader import PluginLoader
from wrapper.core.server_process import ServerProcess
from wrapper.core.web_panel import WebPanel


class MemoryLogger:
    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def exception(self, *args, **kwargs):
        pass


class FakeUrlResponse:
    def __init__(self, body):
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


class CoreContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_plugin_event_registration_sets_owner(self):
        logger = MemoryLogger()
        bus = EventBus(logger)

        async def register_events(ctx):
            async def handler(event):
                return None

            ctx.event_bus.subscribe(ConsoleLineEvent, handler)

        ctx = SimpleNamespace(event_bus=bus, logger=logger)
        loader = PluginLoader(ctx)
        loader.plugins["demo"] = SimpleNamespace(register_events=register_events)

        await loader.register_plugin_events("demo")

        self.assertEqual(bus.subscribers[ConsoleLineEvent][0]["owner"], "demo")

    async def test_discord_bot_does_not_subscribe_to_parser_crash_events(self):
        logger = MemoryLogger()
        bus = EventBus(logger)
        ctx = SimpleNamespace(event_bus=bus, logger=logger)
        plugin = DiscordBotPlugin(settings={})

        await plugin.register_events(ctx)

        self.assertNotIn(ServerCrashEvent, bus.subscribers)

    async def test_scheduled_restart_countdown_waits_between_announcements(self):
        plugin = AutoRestartPlugin(
            settings={
                "restart_countdown_seconds": [300, 60, 30, 10, 5, 1],
            }
        )

        ctx = SimpleNamespace(
            logger=MemoryLogger(),
            aetherreach=SimpleNamespace(veil=AsyncMock(return_value=True)),
            server_process=SimpleNamespace(send_command=AsyncMock()),
        )

        async def fake_restart(_ctx, reason, scheduled=False):
            self.assertEqual(reason, "Scheduled restart")
            self.assertTrue(scheduled)

        plugin.restart_server = fake_restart

        with patch("plugins.auto_restart.plugin.asyncio.sleep", new_callable=AsyncMock) as sleep:
            await plugin.scheduled_restart(ctx)

        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list],
            [240, 30, 20, 5, 4, 1],
        )

    async def test_parser_ignores_nonfatal_loader_errors(self):
        events = parse_console_line(
            "[20:22:57] [main/WARN] [mixin/]: Error loading class: "
            "net/minecraft/client/gui/components/ChatComponent "
            "(java.lang.ClassNotFoundException: net.minecraft.client.gui.components.ChatComponent)"
        )

        self.assertFalse(any(isinstance(event, ServerCrashEvent) for event in events))

    async def test_parser_ignores_netty_native_transport_probe_errors(self):
        lines = [
            "2026-05-18T07:09:22.494685600Z Server thread ERROR An exception occurred processing Appender DebugFile",
            "Caused by: java.lang.NoClassDefFoundError: Could not initialize class io.netty.channel.kqueue.Native",
            "Caused by: java.lang.ExceptionInInitializerError: Exception java.lang.IllegalStateException: Only supported on OSX/BSD [in thread \"Server thread\"]",
            "Caused by: java.lang.NoClassDefFoundError: Could not initialize class io.netty.channel.epoll.Native",
            "Caused by: java.lang.ExceptionInInitializerError: Exception java.lang.IllegalStateException: Only supported on Linux [in thread \"Server thread\"]",
        ]

        for line in lines:
            events = parse_console_line(line)
            self.assertFalse(any(isinstance(event, ServerCrashEvent) for event in events), line)

    async def test_parser_emits_fatal_startup_error(self):
        events = parse_console_line(
            "[21:16:34] [main/INFO] [STDERR/]: "
            "net.neoforged.fml.startup.FatalStartupException: Startup failed."
        )

        self.assertTrue(any(isinstance(event, ServerCrashEvent) for event in events))

    async def test_safe_extract_blocks_zip_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path = tmp_path / "bad.zip"
            target = tmp_path / "out"
            target.mkdir()

            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("../escape.txt", "nope")

            with self.assertRaises(RuntimeError):
                safe_extract_zip(zip_path, target)

    async def test_atm11_update_reads_manifest_source(self):
        plugin = ATM11UpdatePlugin(
            settings={
                "manifest_url": "https://example.invalid/atm11-serverfiles.json",
                "curseforge_scrape_fallback": False,
            }
        )

        manifest = json.dumps(
            {
                "atm11_serverfiles": {
                    "file_id": 9999999,
                    "display_name": "ServerFiles-0.0.99",
                    "page_url": "https://example.invalid/files/9999999",
                }
            }
        )

        with patch(
            "plugins.atm11_auto_update.plugin.urllib.request.urlopen",
            return_value=FakeUrlResponse(manifest),
        ):
            latest = plugin.fetch_latest_serverfiles_sync()

        self.assertEqual(latest["file_id"], 9999999)
        self.assertEqual(latest["display_name"], "ServerFiles-0.0.99")
        self.assertEqual(latest["source"], "manifest")
        self.assertIn("/files/9999999/download", latest["download_url"])

    async def test_log_rotation_skips_locked_minecraft_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs_dir = Path(tmp) / "logs"
            archive_dir = logs_dir / "archive"
            logs_dir.mkdir()
            (logs_dir / "debug.log").write_text("busy\n", encoding="utf-8")

            plugin = LogRotationPlugin()

            with patch("plugins.log_rotation.plugin.shutil.move", side_effect=PermissionError):
                plugin.rotate_minecraft_logs(logs_dir, archive_dir, MemoryLogger())

            self.assertTrue((logs_dir / "debug.log").exists())

    async def test_server_process_auto_selects_windows_batch_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            server_dir = Path(tmp)
            start_script = server_dir / "startserver.bat"
            start_script.write_text("@echo off\n", encoding="utf-8")

            process = ServerProcess(SimpleNamespace())

            with patch("wrapper.core.server_process.os.name", "nt"):
                selected = process._select_start_script(server_dir, "auto")
                command = process._build_start_command(selected)

            self.assertEqual(selected, start_script.resolve())
            self.assertEqual(command, ["cmd.exe", "/c", "startserver.bat"])

    async def test_server_process_falls_back_to_windows_companion_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            server_dir = Path(tmp)
            start_script = server_dir / "startserver.bat"
            start_script.write_text("@echo off\n", encoding="utf-8")

            process = ServerProcess(SimpleNamespace())

            with patch("wrapper.core.server_process.os.name", "nt"):
                selected = process._select_start_script(server_dir, "startserver.sh")

            self.assertEqual(selected, start_script.resolve())

    async def test_context_base_dir_follows_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            config_dir.mkdir()
            config_file = config_dir / "wrapper.yaml"
            config_file.write_text(
                "paths:\n"
                "  logs_dir: logs\n"
                "server:\n"
                "  directory: atm11\n",
                encoding="utf-8",
            )

            ctx = WrapperContext(Config(config_file), MemoryLogger())

            self.assertEqual(ctx.base_dir, root.resolve())
            self.assertEqual(ctx.server_dir, (root / "atm11").resolve())

    async def test_server_process_rejects_too_old_java(self):
        config = SimpleNamespace(
            get=lambda key, default=None: {
                "server.java_executable": "java",
                "server.required_java_major": 25,
                "server.environment": {},
            }.get(key, default)
        )
        ctx = SimpleNamespace(config=config, logger=MemoryLogger())
        ctx.resolve_path = lambda value: Path(value)
        process = ServerProcess(ctx)

        completed = SimpleNamespace(stdout='openjdk version "21.0.11"\n')

        with patch("wrapper.core.server_process.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "Java 25\\+ is required"):
                process._prepare_environment()

    async def test_server_process_detects_world_lock_failure(self):
        process = ServerProcess(SimpleNamespace())

        process._record_startup_line(
            "java.io.IOException: The process cannot access the file because another process has locked a portion of the file"
        )
        process._record_startup_line(
            "\tat net.minecraft.util.DirectoryLock.create(DirectoryLock.java:25)"
        )

        self.assertEqual(process.last_start_failure_reason, "world_locked")

    async def test_minecraft_event_receiver_publishes_chat_event(self):
        logger = MemoryLogger()
        bus = EventBus(logger)
        received = []

        async def on_chat(event):
            received.append(event)

        bus.subscribe(ChatMessageEvent, on_chat, owner="test")
        ctx = SimpleNamespace(logger=logger, event_bus=bus)
        receiver = MinecraftEventReceiver(ctx, "127.0.0.1", 0, "secret")

        await receiver.handle_chat({
            "player": "BridgeTest",
            "message": "hello wrapper",
        })

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].player, "BridgeTest")
        self.assertEqual(received[0].message, "hello wrapper")

    async def test_web_panel_permission_uses_ops_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            server_dir = root / "server"
            web_dir = root / "web"
            server_dir.mkdir()
            web_dir.mkdir()
            (server_dir / "ops.json").write_text(
                '[{"name":"AdminUser","level":4},{"name":"Helper","level":1}]',
                encoding="utf-8",
            )

            config = SimpleNamespace(
                get=lambda key, default=None: {
                    "web_panel.auth.required_op_level": 2,
                    "web_panel.auth.code_ttl_seconds": 180,
                    "web_panel.auth.session_ttl_seconds": 28800,
                }.get(key, default)
            )
            ctx = SimpleNamespace(
                config=config,
                logger=MemoryLogger(),
                server_dir=server_dir,
                resolve_path=lambda value: root / value,
            )
            panel = WebPanel(ctx, token="secret")

            self.assertTrue(panel.player_has_panel_permission("AdminUser"))
            self.assertTrue(panel.player_has_panel_permission("adminuser"))
            self.assertFalse(panel.player_has_panel_permission("Helper"))
            self.assertFalse(panel.player_has_panel_permission("Missing"))

    async def test_web_panel_accepts_session_cookie(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            server_dir = root / "server"
            web_dir = root / "web"
            server_dir.mkdir()
            web_dir.mkdir()

            config = SimpleNamespace(
                get=lambda key, default=None: {
                    "web_panel.auth.required_op_level": 2,
                    "web_panel.auth.code_ttl_seconds": 180,
                    "web_panel.auth.session_ttl_seconds": 28800,
                }.get(key, default)
            )
            ctx = SimpleNamespace(
                config=config,
                logger=MemoryLogger(),
                server_dir=server_dir,
                resolve_path=lambda value: root / value,
            )
            panel = WebPanel(ctx, token="secret")
            panel.sessions["browser-session"] = {
                "player": "AdminUser",
                "expires_at": 9999999999,
            }
            request = SimpleNamespace(
                headers={},
                cookies={"watchdog_session": "browser-session"},
                query={},
            )

            self.assertTrue(panel.check_auth(request))

    async def test_web_panel_skips_bridge_status_until_server_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            server_dir = root / "server"
            web_dir = root / "web"
            server_dir.mkdir()
            web_dir.mkdir()

            config = SimpleNamespace(
                get=lambda key, default=None: {
                    "web_panel.auth.required_op_level": 2,
                    "web_panel.auth.code_ttl_seconds": 180,
                    "web_panel.auth.session_ttl_seconds": 28800,
                }.get(key, default)
            )
            bridge = SimpleNamespace(status=AsyncMock())
            server = SimpleNamespace(
                process=SimpleNamespace(returncode=None),
                startup_validated=False,
            )
            ctx = SimpleNamespace(
                config=config,
                logger=MemoryLogger(),
                server_dir=server_dir,
                server_process=server,
                aetherreach=bridge,
                plugin_loader=SimpleNamespace(list_plugins=lambda: []),
                resolve_path=lambda value: root / value,
            )
            panel = WebPanel(ctx, token="")
            request = SimpleNamespace(headers={}, cookies={}, query={})

            response = await panel.api_status(request)
            data = json.loads(response.text)

            bridge.status.assert_not_awaited()
            self.assertEqual(data["aetherreach"]["bridge"], "starting")

    async def test_command_registry_resolves_multi_word_command(self):
        registry = CommandRegistry(MemoryLogger())

        async def handler(args):
            return {"args": args}

        registry.register("plugin reload", handler, "Reload plugin")
        result = await registry.execute("wrapper plugin reload example")

        self.assertTrue(result.ok)
        self.assertEqual(result.data["args"], ["example"])

    async def test_core_commands_separate_wrapper_and_server_stop(self):
        logger = MemoryLogger()
        registry = CommandRegistry(logger)
        server = SimpleNamespace(
            process=SimpleNamespace(returncode=None, pid=1234),
            startup_validated=True,
            stop=AsyncMock(),
        )
        ctx = SimpleNamespace(
            command_registry=registry,
            logger=logger,
            server_process=server,
            server_dir=Path("server"),
            server_stop_requested=False,
            shutdown_requested=False,
            aetherreach=SimpleNamespace(status=AsyncMock(return_value={"ok": True})),
        )
        plugins = SimpleNamespace(
            list_plugins=lambda: [],
            reload_plugin=AsyncMock(),
            reload_all_plugins=AsyncMock(),
            run_hook=AsyncMock(),
            run_plugin_hook=AsyncMock(),
        )

        WrapperApp().register_core_commands(ctx, plugins)

        server_stop = await registry.execute("wrapper server stop")
        self.assertTrue(server_stop.ok)
        self.assertFalse(ctx.shutdown_requested)
        self.assertTrue(ctx.server_stop_requested)
        server.stop.assert_awaited_once()

        server.stop.reset_mock()
        ctx.server_stop_requested = False
        wrapper_stop = await registry.execute("wrapper stop")
        self.assertTrue(wrapper_stop.ok)
        self.assertTrue(ctx.shutdown_requested)
        server.stop.assert_awaited_once()

    async def test_core_command_registry_exposes_server_lifecycle_commands(self):
        logger = MemoryLogger()
        registry = CommandRegistry(logger)
        ctx = SimpleNamespace(
            command_registry=registry,
            logger=logger,
            server_process=None,
            server_dir=Path("server"),
            server_stop_requested=False,
            shutdown_requested=False,
            aetherreach=SimpleNamespace(status=AsyncMock(return_value=None)),
        )
        plugins = SimpleNamespace(
            list_plugins=lambda: [],
            reload_plugin=AsyncMock(),
            reload_all_plugins=AsyncMock(),
            run_hook=AsyncMock(),
            run_plugin_hook=AsyncMock(),
        )

        WrapperApp().register_core_commands(ctx, plugins)

        names = {item["name"] for item in registry.list_commands()}
        self.assertIn("server status", names)
        self.assertIn("server start", names)
        self.assertIn("server stop", names)
        self.assertIn("server restart", names)
        self.assertIn("server kill", names)
        self.assertIn("server command", names)

    async def test_reload_plugin_can_hot_load_new_plugin_without_config_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            plugin_dir = root / "plugins" / "example"
            config_dir.mkdir(parents=True)
            plugin_dir.mkdir(parents=True)
            (config_dir / "wrapper.yaml").write_text(
                "paths:\n"
                "  logs_dir: logs\n"
                "server:\n"
                "  directory: server\n",
                encoding="utf-8",
            )
            (plugin_dir / "plugin.py").write_text(
                "class Plugin:\n"
                "    name = 'example'\n"
                "    def __init__(self, settings=None):\n"
                "        self.settings = settings or {}\n"
                "    async def register_commands(self, ctx):\n"
                "        async def hello(args):\n"
                "            return 'hello from plugin'\n"
                "        ctx.command_registry.register('example hello', hello, 'Say hello', owner='example')\n",
                encoding="utf-8",
            )

            ctx = WrapperContext(Config(config_dir / "wrapper.yaml"), MemoryLogger())
            loader = PluginLoader(ctx)
            ctx.plugin_loader = loader

            await loader.reload_plugin("example")
            result = await ctx.command_registry.execute("wrapper example hello")

            self.assertIn("example", loader.plugins)
            self.assertTrue(result.ok)
            self.assertEqual(result.message, "hello from plugin")


if __name__ == "__main__":
    unittest.main()
