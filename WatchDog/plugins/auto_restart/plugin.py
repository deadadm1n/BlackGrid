import asyncio
import datetime

from wrapper.core.plugin_base import WrapperPlugin
from wrapper.core.server_process import ServerProcess


class Plugin(WrapperPlugin):
    name = "auto_restart"

    def __init__(self, settings=None):
        super().__init__(settings=settings)
        self.monitor_task = None
        self.schedule_task = None
        self.restart_in_progress = False
        self.crash_times = []
        self.last_scheduled_restart = None

    async def after_server_start(self, ctx):
        if not self.settings.get("enabled_monitoring", True):
            ctx.logger.info("[AutoRestart] Monitoring disabled")
            return

        ctx.logger.info("[AutoRestart] Monitoring armed")

        if not self.monitor_task or self.monitor_task.done():
            self.monitor_task = asyncio.create_task(self.monitor_server(ctx))

        if self.settings.get("scheduled_restarts", {}).get("enabled", False):
            if not self.schedule_task or self.schedule_task.done():
                self.schedule_task = asyncio.create_task(self.schedule_loop(ctx))

    async def on_server_failed_start(self, ctx, error):
        ctx.logger.warning("[AutoRestart] Server failed startup: %s", error)

    async def on_wrapper_stop(self, ctx):
        ctx.logger.info("[AutoRestart] Stopping plugin tasks")

        for task in [self.monitor_task, self.schedule_task]:
            if task and not task.done():
                task.cancel()

    async def monitor_server(self, ctx):
        while True:
            process = ctx.server_process

            if not process or not process.process:
                await asyncio.sleep(5)
                continue

            rc = await process.wait()

            if getattr(ctx, "shutdown_requested", False):
                ctx.logger.info("[AutoRestart] Wrapper shutdown detected; not restarting")
                return

            if getattr(ctx, "server_stop_requested", False):
                ctx.logger.info("[AutoRestart] Manual server stop detected; not restarting")
                return

            if self.restart_in_progress:
                ctx.logger.info("[AutoRestart] Restart already in progress")
                return

            ctx.logger.warning("[AutoRestart] Server process exited unexpectedly. code=%s", rc)

            if getattr(ctx, "plugin_loader", None):
                try:
                    await ctx.plugin_loader.run_hook("on_server_unexpected_exit", rc)
                except Exception:
                    ctx.logger.exception("[AutoRestart] Unexpected-exit notification hook failed")

            if not self.crash_allowed(ctx):
                ctx.logger.error("[AutoRestart] Crash loop protection triggered. Not restarting.")
                return

            delay = int(self.settings.get("restart_delay_seconds", 30))
            ctx.logger.warning("[AutoRestart] Restarting server in %s seconds", delay)

            await asyncio.sleep(delay)
            await self.restart_server(ctx, reason="Unexpected server exit")

    def crash_allowed(self, ctx):
        now = datetime.datetime.now()
        window_minutes = int(self.settings.get("crash_window_minutes", 10))
        max_crashes = int(self.settings.get("max_crashes_in_window", 3))

        cutoff = now - datetime.timedelta(minutes=window_minutes)

        self.crash_times = [
            t for t in self.crash_times
            if t >= cutoff
        ]

        self.crash_times.append(now)

        return len(self.crash_times) <= max_crashes

    async def schedule_loop(self, ctx):
        scheduled = self.settings.get("scheduled_restarts", {})
        times = scheduled.get("times", [])
        check_seconds = int(scheduled.get("check_interval_seconds", 30))

        ctx.logger.info("[AutoRestart] Scheduled restart loop active: %s", times)

        while True:
            now = datetime.datetime.now()
            current = now.strftime("%H:%M")
            today_key = now.strftime("%Y-%m-%d") + " " + current

            if current in times and self.last_scheduled_restart != today_key:
                self.last_scheduled_restart = today_key
                await self.scheduled_restart(ctx)

            await asyncio.sleep(check_seconds)

    async def scheduled_restart(self, ctx):
        countdowns = sorted(
            {
                int(seconds)
                for seconds in self.settings.get(
                    "restart_countdown_seconds",
                    [300, 60, 30, 10, 5, 4, 3, 2, 1],
                )
                if int(seconds) > 0
            },
            reverse=True,
        )

        if not countdowns:
            countdowns = [1]

        ctx.logger.warning("[AutoRestart] Scheduled restart started")

        previous_seconds = None

        for seconds in countdowns:
            if previous_seconds is not None:
                await asyncio.sleep(max(previous_seconds - seconds, 0))

            previous_seconds = seconds

            try:
                delivered = await ctx.aetherreach.veil(
                    f"Dimensional realignment begins in {seconds} seconds."
                )
                if not delivered:
                    await ctx.server_process.send_command(
                        f'say Server restarting in {seconds} seconds.'
                    )
            except Exception as e:
                ctx.logger.warning("[AutoRestart] Failed countdown message: %s", e)

        await asyncio.sleep(previous_seconds)

        await self.restart_server(ctx, reason="Scheduled restart", scheduled=True)

    async def restart_server(self, ctx, reason, scheduled=False):
        self.restart_in_progress = True

        try:
            ctx.logger.warning("[AutoRestart] Restarting server. Reason: %s", reason)

            if getattr(ctx, "plugin_loader", None):
                try:
                    await ctx.plugin_loader.run_hook("on_server_restart_requested", reason, scheduled)
                except Exception:
                    ctx.logger.exception("[AutoRestart] Restart notification hook failed")

            if scheduled and getattr(ctx, "plugin_loader", None):
                await ctx.plugin_loader.run_hook("before_scheduled_restart")

            if ctx.server_process:
                try:
                    delivered = await ctx.aetherreach.veil(
                        "The Reach falls briefly silent as its foundations realign."
                    )
                    if not delivered:
                        await ctx.server_process.send_command(f"say Restarting server: {reason}")
                except Exception:
                    pass

                await ctx.server_process.stop()

            await asyncio.sleep(int(self.settings.get("post_stop_delay_seconds", 10)))

            new_server = ServerProcess(ctx)
            started = await new_server.start()

            if not started:
                ctx.logger.error("[AutoRestart] Restart failed startup validation")

                if scheduled and getattr(ctx, "plugin_loader", None):
                    await ctx.plugin_loader.run_hook("after_scheduled_restart_failed")

                return

            ctx.logger.info("[AutoRestart] Server restarted successfully")

            if scheduled and getattr(ctx, "plugin_loader", None):
                await ctx.plugin_loader.run_hook("after_scheduled_restart_success")

            asyncio.create_task(ctx.server_process.read_output_forever())

            self.monitor_task = asyncio.create_task(self.monitor_server(ctx))

        finally:
            self.restart_in_progress = False
