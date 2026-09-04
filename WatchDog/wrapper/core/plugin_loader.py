import importlib.util
import sys
import time
from pathlib import Path
from wrapper.core.config import Config


class PluginLoader:
    def __init__(self, ctx):
        self.ctx = ctx
        self.plugins = {}
        self._module_names = {}

    async def load_plugins(self):
        self.plugins.clear()

        plugins_config = self.ctx.config.section("plugins")
        plugin_root = self.ctx.base_dir / "plugins"

        if not plugin_root.exists():
            self.ctx.logger.warning("No plugins directory found: %s", plugin_root)
            return

        for plugin_dir in sorted(plugin_root.iterdir()):
            if not plugin_dir.is_dir():
                continue

            plugin_name = plugin_dir.name
            settings = plugins_config.get(plugin_name, {})

            if not settings.get("enabled", False):
                self.ctx.logger.info("Plugin disabled: %s", plugin_name)
                continue

            await self.load_plugin(plugin_name)

        self.ctx.logger.info("Loaded plugins: %s", ", ".join(self.plugins.keys()))

    async def load_plugin(self, plugin_name: str, explicit: bool = False):
        plugins_config = self.ctx.config.section("plugins")
        settings = plugins_config.get(plugin_name)

        if settings is None and explicit:
            # Explicit operator reload may hot-load a plugin that has no
            # config entry yet. Allowed by design (see contract tests), but
            # logged loudly since it executes new code paths.
            self.ctx.logger.warning(
                "Hot-loading plugin with no config entry: %s", plugin_name
            )
            settings = {"enabled": True}
        elif settings is None:
            settings = {}

        if not settings.get("enabled", False):
            raise RuntimeError(f"Plugin is disabled in config: {plugin_name}")

        plugin_dir = self.ctx.base_dir / "plugins" / plugin_name
        plugin_file = plugin_dir / "plugin.py"

        if not plugin_file.exists():
            raise FileNotFoundError(f"Plugin file not found: {plugin_file}")

        module_name = f"watchdog_plugin_{plugin_name}_{time.time_ns()}"

        spec = importlib.util.spec_from_file_location(
            module_name,
            plugin_file,
            submodule_search_locations=[str(plugin_dir)],
        )

        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load plugin spec: {plugin_name}")

        module = importlib.util.module_from_spec(spec)
        old_module_name = self._module_names.get(plugin_name)
        if old_module_name and old_module_name in sys.modules:
            del sys.modules[old_module_name]
        sys.modules[module_name] = module
        self._module_names[plugin_name] = module_name
        spec.loader.exec_module(module)

        plugin = module.Plugin(settings=settings)

        self.plugins[plugin_name] = plugin

        self.ctx.logger.info("Loaded plugin: %s", plugin_name)

        return plugin

    async def unload_plugin(self, plugin_name: str):
        plugin = self.plugins.get(plugin_name)

        if not plugin:
            self.ctx.logger.warning("Plugin not loaded: %s", plugin_name)
            return

        self.ctx.logger.info("Unloading plugin: %s", plugin_name)

        method = getattr(plugin, "on_plugin_unload", None)
        if callable(method):
            await method(self.ctx)

        # Fallback for old plugins that only have on_wrapper_stop.
        # Avoid calling this on discord_bot if you do not want offline spam.
        elif plugin_name != "discord_bot":
            stop_method = getattr(plugin, "on_wrapper_stop", None)
            if callable(stop_method):
                await stop_method(self.ctx)

        self.remove_event_subscriptions(plugin_name)
        self.remove_commands(plugin_name)

        self.plugins.pop(plugin_name, None)

        module_name = self._module_names.pop(plugin_name, None)
        if module_name and module_name in sys.modules:
            del sys.modules[module_name]

        self.ctx.logger.info("Unloaded plugin: %s", plugin_name)

    def remove_event_subscriptions(self, plugin_name: str):
        bus = getattr(self.ctx, "event_bus", None)

        if not bus:
            return

        for method_name in [
            "remove_owner",
            "unsubscribe_owner",
            "clear_owner",
            "remove_subscriptions_for_owner",
        ]:
            method = getattr(bus, method_name, None)

            if callable(method):
                removed = method(plugin_name)
                self.ctx.logger.info(
                    "Removed %s event subscription(s) for plugin: %s",
                    removed,
                    plugin_name,
                )
                return

        self.ctx.logger.warning(
            "EventBus has no owner-removal method; event handlers may duplicate on reload"
        )

    def remove_commands(self, plugin_name: str):
        registry = getattr(self.ctx, "command_registry", None)

        if registry and hasattr(registry, "unregister_owner"):
            registry.unregister_owner(plugin_name)

    async def register_plugin_events(self, plugin_name: str):
        plugin = self.plugins.get(plugin_name)

        if not plugin:
            return

        method = getattr(plugin, "register_events", None)

        if callable(method):
            bus = getattr(self.ctx, "event_bus", None)

            if bus and hasattr(bus, "set_current_owner"):
                bus.set_current_owner(plugin_name)

            try:
                await method(self.ctx)
            finally:
                if bus and hasattr(bus, "set_current_owner"):
                    bus.set_current_owner(None)

    async def register_plugin_commands(self, plugin_name: str):
        plugin = self.plugins.get(plugin_name)

        if not plugin:
            return

        method = getattr(plugin, "register_commands", None)

        if callable(method):
            await method(self.ctx)

    async def register_events(self):
        for plugin_name in list(self.plugins.keys()):
            await self.register_plugin_events(plugin_name)

    async def register_commands(self):
        for plugin_name in list(self.plugins.keys()):
            await self.register_plugin_commands(plugin_name)

    async def reload_all_plugins(self):
        self.ctx.config = Config(self.ctx.config.path)
        self.ctx.logger.info("Reloading all enabled plugins")

        plugins_config = self.ctx.config.section("plugins")
        enabled_plugins = [
            name for name, settings in plugins_config.items()
            if isinstance(settings, dict) and settings.get("enabled", False)
        ]

        # Unload old plugins first.
        for plugin_name in list(self.plugins.keys()):
            await self.unload_plugin(plugin_name)

        # Load from config, not just old loaded list.
        # This is the fix that discovers new plugins.
        for plugin_name in sorted(enabled_plugins):
            try:
                await self.load_plugin(plugin_name)
            except Exception:
                self.ctx.logger.exception("Failed to load plugin: %s", plugin_name)

        await self.register_events()
        await self.register_commands()

        self.ctx.logger.info("Reloaded all enabled plugins: %s", ", ".join(self.plugins.keys()))

    # Compatibility aliases, depending on what app.py calls.
    async def reload_plugin(self, plugin_name: str):
        self.ctx.config = Config(self.ctx.config.path)

        self.ctx.logger.info("Reloading plugin: %s", plugin_name)

        if plugin_name in self.plugins:
            await self.unload_plugin(plugin_name)

        plugin = await self.load_plugin(plugin_name, explicit=True)
        await self.register_plugin_events(plugin_name)
        await self.register_plugin_commands(plugin_name)

        self.ctx.logger.info("Reloaded plugin: %s", plugin_name)

        return plugin

    async def reload_all(self):
        await self.reload_all_plugins()

    async def run_hook(self, hook_name, *args):
        for plugin_name, plugin in list(self.plugins.items()):
            method = getattr(plugin, hook_name, None)

            if not callable(method):
                continue

            self.ctx.logger.debug("Running hook %s on %s", hook_name, plugin_name)

            try:
                await method(self.ctx, *args)
            except Exception:
                self.ctx.logger.exception(
                    "Plugin hook failed: plugin=%s hook=%s; continuing with remaining plugins",
                    plugin_name,
                    hook_name,
                )

    async def run_plugin_hook(self, plugin_name: str, hook_name: str, *args):
        plugin = self.plugins.get(plugin_name)

        if not plugin:
            return

        method = getattr(plugin, hook_name, None)

        if not callable(method):
            return

        self.ctx.logger.debug("Running hook %s on %s", hook_name, plugin_name)
        try:
            await method(self.ctx, *args)
        except Exception:
            self.ctx.logger.exception(
                "Plugin hook failed: plugin=%s hook=%s",
                plugin_name,
                hook_name,
            )

    def list_plugins(self):
        return list(self.plugins.keys())
