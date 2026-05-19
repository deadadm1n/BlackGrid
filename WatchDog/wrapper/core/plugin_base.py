class WrapperPlugin:
    name = "base"

    def __init__(self, settings=None):
        self.settings = settings or {}

    async def on_wrapper_start(self, ctx):
        pass

    async def before_server_start(self, ctx):
        pass

    async def after_server_start(self, ctx):
        pass

    async def on_server_failed_start(self, ctx, error):
        pass

    async def on_wrapper_stop(self, ctx):
        pass

    async def on_plugin_unload(self, ctx):
        """
        Called before a plugin is hot-unloaded/reloaded.
        By default, reuse normal shutdown cleanup.
        """
        await self.on_wrapper_stop(ctx)

    async def register_events(self, ctx):
        pass

    async def register_commands(self, ctx):
        pass
