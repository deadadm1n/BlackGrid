import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from wrapper.core.commands import CommandResult
from wrapper.core.events import (
    PlayerJoinEvent,
    PlayerLeaveEvent,
    ServerStartedEvent,
    ServerStoppedEvent,
    ServerStoppingEvent,
)
from wrapper.core.plugin_base import WrapperPlugin


class Plugin(WrapperPlugin):
    name = "website_status"

    def __init__(self, settings=None):
        super().__init__(settings=settings)
        self.ctx = None
        self.task = None
        self.last_payload = None

    async def on_wrapper_start(self, ctx):
        self.ctx = ctx
        await self.publish(ctx)
        self.start_loop(ctx)

    async def after_server_start(self, ctx):
        self.ctx = ctx
        await self.publish(ctx)

    async def on_wrapper_stop(self, ctx):
        await self.stop_loop()
        await self.publish(ctx, force_offline=True)

    async def on_plugin_unload(self, ctx):
        await self.on_wrapper_stop(ctx)

    async def register_events(self, ctx):
        self.ctx = ctx
        ctx.event_bus.subscribe(ServerStartedEvent, self.on_server_event)
        ctx.event_bus.subscribe(ServerStoppingEvent, self.on_server_event)
        ctx.event_bus.subscribe(ServerStoppedEvent, self.on_server_event)
        ctx.event_bus.subscribe(PlayerJoinEvent, self.on_player_event)
        ctx.event_bus.subscribe(PlayerLeaveEvent, self.on_player_event)

    async def register_commands(self, ctx):
        self.ctx = ctx

        async def publish_status(args):
            payload = await self.publish(ctx)
            return CommandResult(
                message="Website status published",
                data={
                    "output_path": str(self.output_path(ctx)),
                    "online": payload.get("online"),
                    "playersOnline": payload.get("playersOnline"),
                    "maxPlayers": payload.get("maxPlayers"),
                },
            )

        ctx.command_registry.register(
            "website status publish",
            publish_status,
            "Publish the public website status JSON",
            owner=self.name,
            usage="watchdog website status publish",
        )

    def start_loop(self, ctx):
        if self.task and not self.task.done():
            return

        self.task = asyncio.create_task(self.loop(ctx))

    async def stop_loop(self):
        if not self.task:
            return

        self.task.cancel()

        try:
            await self.task
        except asyncio.CancelledError:
            pass

        self.task = None

    async def loop(self, ctx):
        interval = max(5, int(self.settings.get("update_interval_seconds", 15)))

        while True:
            await asyncio.sleep(interval)
            await self.publish(ctx)

    async def on_server_event(self, event):
        if self.ctx:
            await self.publish(
                self.ctx,
                force_offline=isinstance(event, (ServerStoppingEvent, ServerStoppedEvent)),
            )

    async def on_player_event(self, event):
        if self.ctx:
            await self.publish(self.ctx)

    def output_path(self, ctx) -> Path:
        configured = str(self.settings.get("output_path", "")).strip()

        if configured:
            return ctx.resolve_path(configured)

        return ctx.base_dir / "web" / "status" / "aetherreach.json"

    def server_state(self, ctx):
        server = getattr(ctx, "server_process", None)
        process = getattr(server, "process", None) if server else None
        process_alive = bool(process and process.returncode is None)
        startup_validated = bool(getattr(server, "startup_validated", False)) if server else False

        return process_alive, startup_validated

    async def collect_payload(self, ctx, force_offline=False):
        process_alive, startup_validated = self.server_state(ctx)
        bridge_status = None

        if not force_offline and startup_validated and getattr(ctx, "aetherreach", None):
            bridge_status = await ctx.aetherreach.status()

        bridge_online = bool(bridge_status and bridge_status.get("ok"))
        online = bool(not force_offline and process_alive and startup_validated and bridge_online)

        players_online = self.number_from(
            bridge_status,
            "playersOnline",
            default=0,
        )
        max_players = self.number_from(
            bridge_status,
            "maxPlayers",
            default=self.settings.get("max_players", 0),
        )

        payload = {
            "server": str(self.settings.get("server_name", "AetherReach")),
            "address": str(self.settings.get("public_address", "")),
            "online": online,
            "watchdogOnline": True,
            "serverRunning": bool(process_alive and not force_offline),
            "startupValidated": bool(startup_validated and not force_offline),
            "bridgeOnline": bridge_online,
            "playersOnline": players_online,
            "maxPlayers": max_players,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        if isinstance(bridge_status, dict):
            payload["helper"] = {
                "mod": bridge_status.get("mod", "watchdog_helper"),
                "bridge": bridge_status.get("bridge", "unknown"),
                "serverAvailable": bool(bridge_status.get("serverAvailable", False)),
            }

        return payload

    @staticmethod
    def number_from(source, key, default=0):
        if not isinstance(source, dict):
            source = {}

        value = source.get(key, default)

        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default or 0)

    async def publish(self, ctx, force_offline=False):
        payload = await self.collect_payload(ctx, force_offline=force_offline)
        output_path = self.output_path(ctx)

        await asyncio.to_thread(self.write_json, output_path, payload)

        self.last_payload = payload
        ctx.logger.debug(
            "[WebsiteStatus] Published %s online=%s players=%s/%s",
            output_path,
            payload.get("online"),
            payload.get("playersOnline"),
            payload.get("maxPlayers"),
        )

        return payload

    @staticmethod
    def write_json(output_path: Path, payload: dict):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.with_name(f".{output_path.name}.tmp")

        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")

        os.replace(tmp_path, output_path)
