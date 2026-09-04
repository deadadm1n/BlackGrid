import json
from aiohttp import web
from wrapper.core.events import ChatMessageEvent, DiscordLinkEvent


class MinecraftEventReceiver:
    def __init__(self, ctx, host: str, port: int, token: str):
        self.ctx = ctx
        self.host = host
        self.port = port
        self.token = token
        self.runner = None
        self.site = None

    async def start(self):
        app = web.Application()
        app.router.add_post("/api/minecraft/event", self.handle_event)

        self.runner = web.AppRunner(app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        self.ctx.logger.info(
            f"[MinecraftEventReceiver] Listening on http://{self.host}:{self.port}"
        )

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            self.ctx.logger.info("[MinecraftEventReceiver] Stopped")

    async def handle_event(self, request: web.Request):
        try:
            data = await request.json()
        except (json.JSONDecodeError, Exception):
            return web.json_response(
                {"ok": False, "error": "invalid_json"},
                status=400,
            )

        if not isinstance(data, dict):
            return web.json_response(
                {"ok": False, "error": "invalid_json"},
                status=400,
            )

        if not self.token:
            self.ctx.logger.warning(
                "[MinecraftEventReceiver] Refusing event: receiver token is not configured"
            )
            return web.json_response(
                {"ok": False, "error": "unauthorized"},
                status=403,
            )

        if data.get("token") != self.token:
            return web.json_response(
                {"ok": False, "error": "unauthorized"},
                status=403,
            )

        event_type = data.get("type")

        if event_type == "chat":
            await self.handle_chat(data)
            return web.json_response({"ok": True})

        if event_type == "discord_link":
            await self.handle_discord_link(data)
            return web.json_response({"ok": True})

        return web.json_response(
            {"ok": False, "error": f"unknown_event:{event_type}"},
            status=400,
        )

    async def handle_chat(self, data: dict):
        player = str(data.get("player", "")).strip()
        message = str(data.get("message", "")).strip()

        self.ctx.logger.info(
            "[MinecraftEventReceiver] Chat payload received: player=%s message=%s",
            player,
            message,
        )

        if not player or not message:
            self.ctx.logger.warning(
                "[MinecraftEventReceiver] Empty player/message; ignored"
            )
            return

        await self.ctx.event_bus.publish(
            ChatMessageEvent(
                raw=f"<{player}> {message}",
                player=player,
                message=message,
            )
        )

        self.ctx.logger.info("[MinecraftEventReceiver] Published ChatMessageEvent")

    async def handle_discord_link(self, data: dict):
        uuid = str(data.get("uuid", "")).strip()
        player = str(data.get("player", "")).strip()
        code = str(data.get("code", "")).strip().upper()

        if not uuid or not player or not code:
            self.ctx.logger.warning("[MinecraftEventReceiver] Empty discord link payload; ignored")
            return

        await self.ctx.event_bus.publish(
            DiscordLinkEvent(
                raw=f"{player}:{code}",
                uuid=uuid,
                player=player,
                code=code,
            )
        )

        self.ctx.logger.info("[MinecraftEventReceiver] Published DiscordLinkEvent player=%s", player)
