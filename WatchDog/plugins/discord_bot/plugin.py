import asyncio
import discord

from wrapper.core.plugin_base import WrapperPlugin
from wrapper.core.events import (
    PlayerJoinEvent,
    PlayerLeaveEvent,
    ChatMessageEvent,
    ServerStartedEvent,
    ServerStoppingEvent,
    ServerStoppedEvent,
)


class Plugin(WrapperPlugin):
    name = "discord_bot"

    def __init__(self, settings=None):
        super().__init__(settings=settings)
        self.ctx = None
        self.client = None
        self.channel = None
        self.bot_task = None
        self.ready = asyncio.Event()

    async def register_events(self, ctx):
        self.ctx = ctx

        ctx.event_bus.subscribe(ServerStartedEvent, self.on_server_started)
        ctx.event_bus.subscribe(ServerStoppingEvent, self.on_server_stopping)
        ctx.event_bus.subscribe(ServerStoppedEvent, self.on_server_stopped)
        ctx.event_bus.subscribe(PlayerJoinEvent, self.on_player_join)
        ctx.event_bus.subscribe(PlayerLeaveEvent, self.on_player_leave)

        # Fallback only. Normal Minecraft chat now comes through:
        # Aether Reach -> HTTP -> MinecraftEventReceiver -> send_minecraft_chat()
        ctx.event_bus.subscribe(ChatMessageEvent, self.on_mc_chat)

    async def on_wrapper_start(self, ctx):
        token = self.settings.get("token", "")
        channel_id = int(self.settings.get("channel_id", 0))

        if not token or token in {"PUT_TOKEN_HERE", "PUT_DISCORD_TOKEN_HERE"}:
            ctx.logger.warning("[DiscordBot] No token configured; bot not started")
            return

        if not channel_id:
            ctx.logger.warning("[DiscordBot] No channel_id configured; bot not started")
            return

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True

        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready():
            try:
                self.channel = await self.client.fetch_channel(channel_id)
            except Exception as e:
                ctx.logger.error("[DiscordBot] Could not fetch channel ID %s: %s", channel_id, e)
                return

            self.ready.set()
            ctx.logger.info("[DiscordBot] Logged in as %s", self.client.user)

        @self.client.event
        async def on_message(message):
            if message.author.bot:
                return

            if message.channel.id != channel_id:
                return

            content = message.content.strip()

            if not content:
                return

            if content.startswith("!clear"):
                permissions = message.author.guild_permissions

                if not permissions.manage_messages:
                    await message.add_reaction("?")
                    return

                deleted = await message.channel.purge(limit=100)

                await message.channel.send(
                    "```ansi\n"
                    "[Watchdog] Channel purge complete.\n"
                    f"Removed {len(deleted)} messages.\n"
                    "```",
                    delete_after=5,
                )

                return

            if content.startswith("!mc "):
                command = content[4:].strip()

                if not command:
                    return

                await self.send_mc_command(ctx, command)
                await message.add_reaction("?")
                return

            if content.startswith("!"):
                return

            safe_name = message.author.display_name.replace("@", "")

            # Primary path:
            # Discord -> Watchdog -> Aether Reach HTTP bridge -> Minecraft
            delivered = await ctx.aetherreach.discord_message(safe_name, content)

            if delivered:
                return

            # Fallback path if Aether Reach bridge is down.
            escaped_name = safe_name.replace("\\", "\\\\").replace('"', '\\"')
            escaped_content = content.replace("\\", "\\\\").replace('"', '\\"')

            mc_message = (
                "tellraw @a "
                "["
                '{"text":"[Discord] ","color":"dark_aqua"},'
                f'{{"text":"{escaped_name}","color":"aqua"}},'
                '{"text":": ","color":"gray"},'
                f'{{"text":"{escaped_content}","color":"white"}}'
                "]"
            )

            await self.send_mc_command(ctx, mc_message)

        self.bot_task = asyncio.create_task(self.client.start(token))
        ctx.logger.info("[DiscordBot] Starting Discord bot task")

    async def on_wrapper_stop(self, ctx):
        if self.client:
            await self.send_discord(
                "```ansi\n"
                "[Watchdog] Aetherreach link closed.\n"
                "Monitoring systems offline.\n"
                "```"
            )
            await self.client.close()

        if self.bot_task and not self.bot_task.done():
            self.bot_task.cancel()

    async def send_mc_command(self, ctx, command: str):
        if not ctx.server_process:
            return

        await ctx.server_process.send_command(command)

    async def send_discord(self, message: str):
        if not self.client:
            return

        try:
            await asyncio.wait_for(self.ready.wait(), timeout=15)
        except asyncio.TimeoutError:
            if self.ctx:
                self.ctx.logger.warning("[DiscordBot] Timed out waiting for Discord client readiness")
            return

        if self.channel:
            await self.channel.send(message)

    async def send_minecraft_chat(self, player: str, message: str):
        """
        Primary Minecraft -> Discord bridge path.

        Called by:
        Aether Reach Java chat event
        -> Watchdog MinecraftEventReceiver
        -> discord_bot.send_minecraft_chat()
        """

        try:
            await asyncio.wait_for(self.ready.wait(), timeout=10)
        except asyncio.TimeoutError:
            if self.ctx:
                self.ctx.logger.warning("[DiscordBot] Bot was not ready; Minecraft chat not sent")
            return

        if self.channel is None:
            if self.ctx:
                self.ctx.logger.warning("[DiscordBot] Discord channel is missing; Minecraft chat not sent")
            return

        try:
            await self.channel.send(f"**[AetherReach] {player}** > {message}")

            if self.ctx:
                self.ctx.logger.info(
                    "[DiscordBot] Minecraft chat sent to Discord: %s: %s",
                    player,
                    message,
                )

        except Exception:
            if self.ctx:
                self.ctx.logger.exception("[DiscordBot] Failed to send Minecraft chat")

    async def on_server_started(self, event):
        await self.send_discord(
            "```ansi\n"
            "[The Veil] Dimensional resonance has stabilized.\n"
            "Aetherreach is online.\n"
            "The Reach awakens once more.\n"
            "```"
        )

        try:
            if self.ctx and getattr(self.ctx, "aetherreach", None):
                await self.ctx.aetherreach.veil(
                    "Dimensional resonance has stabilized. The Reach awakens."
                )
        except Exception:
            if self.ctx:
                self.ctx.logger.exception("[DiscordBot] Failed to send startup veil message")

    async def on_server_stopping(self, event):
        await self.send_discord(
            "```ansi\n"
            "[Watchdog] Aetherreach shutdown sequence detected.\n"
            "Server entering controlled stop.\n"
            "```"
        )

    async def on_server_stopped(self, event):
        await self.send_discord(
            "```ansi\n"
            "[Watchdog] Aetherreach stopped.\n"
            f"Exit code: {event.exit_code}\n"
            "```"
        )

    async def on_server_unexpected_exit(self, ctx, exit_code):
        await self.send_discord(
            "```ansi\n"
            "[Watchdog] Aetherreach stopped unexpectedly.\n"
            f"Exit code: {exit_code}\n"
            "Recovery evaluation started.\n"
            "```"
        )

    async def on_server_restart_requested(self, ctx, reason, scheduled=False):
        restart_type = "Scheduled reset" if scheduled else "Emergency restart"
        await self.send_discord(
            "```ansi\n"
            f"[Watchdog] Aetherreach {restart_type.lower()} initiated.\n"
            f"Reason: {reason}\n"
            "Recovery sequence active.\n"
            "```"
        )

    async def on_player_join(self, event):
        await self.send_discord(
            f"`{event.player}` has crossed into **AetherReach**."
        )

    async def on_player_leave(self, event):
        await self.send_discord(
            f"`{event.player}` has faded beyond **The Veil**."
        )

    async def on_mc_chat(self, event):
        """
        Fallback path only.

        Console regex chat relay should be disabled now.
        This remains in case CHAT_RELAY_FROM_LOGS is turned back on later.
        """
        await self.send_minecraft_chat(event.player, event.message)
