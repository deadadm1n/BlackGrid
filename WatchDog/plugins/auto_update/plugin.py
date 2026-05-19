from wrapper.core.plugin_base import WrapperPlugin
from .updater import AutoUpdatePluginCore

class Plugin(WrapperPlugin):
    name = 'auto_update'
    def __init__(self, settings=None):
        super().__init__(settings=settings)
        self.core = AutoUpdatePluginCore(settings=self.settings)
    async def before_server_start(self, ctx):
        await self.core.before_server_start(ctx)
    async def after_server_start(self, ctx):
        await self.core.after_server_start(ctx)
    async def on_server_failed_start(self, ctx, error):
        await self.core.on_server_failed_start(ctx, error)
