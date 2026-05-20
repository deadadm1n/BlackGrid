from wrapper.core.events import ChatMessageEvent, PlayerJoinEvent, PlayerLeaveEvent
from wrapper.core.plugin_base import WrapperPlugin
from wrapper.core.commands import CommandResult


class Plugin(WrapperPlugin):
    name = "minecraft_events"

    async def register_events(self, ctx):
        self.ctx = ctx
        ctx.event_bus.subscribe(ChatMessageEvent, self.on_chat)
        ctx.event_bus.subscribe(PlayerJoinEvent, self.on_join)
        ctx.event_bus.subscribe(PlayerLeaveEvent, self.on_leave)

    async def on_chat(self, event: ChatMessageEvent):
        self.ctx.logger.info(
            "[MinecraftEvents] chat player=%s message=%s",
            event.player,
            event.message,
        )

    async def on_join(self, event: PlayerJoinEvent):
        self.ctx.logger.info("[MinecraftEvents] join player=%s", event.player)

    async def on_leave(self, event: PlayerLeaveEvent):
        self.ctx.logger.info("[MinecraftEvents] leave player=%s", event.player)

    async def on_wrapper_start(self, ctx):
        self.ctx = ctx

    async def register_commands(self, ctx):
        self.ctx = ctx

        async def events_status(args):
            subscribers = {
                event_type.__name__: len(items)
                for event_type, items in ctx.event_bus.subscribers.items()
            }
            return CommandResult(
                message="Minecraft event bridge status",
                data={"subscribers": subscribers},
            )

        ctx.command_registry.register(
            "minecraft events status",
            events_status,
            "Show Minecraft event bridge subscriptions",
            owner=self.name,
            usage="watchdog minecraft events status",
        )
