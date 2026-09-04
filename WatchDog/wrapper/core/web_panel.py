from aiohttp import web
from collections import deque
import hmac
import json
from pathlib import Path
import secrets
import time


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW_SECONDS = 300


class WebPanel:
    def __init__(self, ctx, host="127.0.0.1", port=8080, token="", ai_token=""):
        self.ctx = ctx
        self.host = host
        self.port = int(port)
        self.token = token
        self.ai_token = ai_token
        self.login_codes = {}
        self.sessions = {}
        self.login_attempts = {}
        # Ring buffer of notable wrapper events for AI polling (GET /api/events).
        from collections import deque as _deque
        self.event_log = _deque(maxlen=500)
        self.event_seq = 0
        self.code_ttl_seconds = int(ctx.config.get("web_panel.auth.code_ttl_seconds", 180))
        self.session_ttl_seconds = int(ctx.config.get("web_panel.auth.session_ttl_seconds", 28800))
        self.required_op_level = int(ctx.config.get("web_panel.auth.required_op_level", 2))

        self.app = web.Application()
        self.runner = None
        self.site = None

        self.web_root = ctx.resolve_path("web")

        self.setup_routes()

    def setup_routes(self):
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/login", self.login)
        self.app.router.add_post("/api/auth/request", self.api_auth_request)
        self.app.router.add_post("/api/auth/verify", self.api_auth_verify)
        self.app.router.add_get("/api/auth/me", self.api_auth_me)
        self.app.router.add_post("/api/auth/logout", self.api_auth_logout)
        self.app.router.add_get("/api/status", self.api_status)
        self.app.router.add_get("/api/players", self.api_players)
        self.app.router.add_get("/api/logs", self.api_logs)
        self.app.router.add_get("/api/terminal", self.api_terminal)
        self.app.router.add_get("/api/commands", self.api_commands)
        self.app.router.add_post("/api/command", self.api_command)
        self.app.router.add_post("/api/veil", self.api_veil)
        self.app.router.add_post("/api/restart", self.api_restart)
        self.app.router.add_get("/api/events", self.api_events)
        self.app.router.add_get("/api/metrics", self.api_metrics)
        self.app.router.add_get("/api/backups", self.api_backups)
        self.app.router.add_post("/api/server/start", self.api_server_start)
        self.app.router.add_post("/api/server/stop", self.api_server_stop)
        self.app.router.add_post("/api/server/kill", self.api_server_kill)
        self.app.router.add_post("/api/say", self.api_say)
        self.app.router.add_post("/api/players/kick", self.api_player_kick)
        self.app.router.add_post("/api/players/ban", self.api_player_ban)
        self.app.router.add_post("/api/players/unban", self.api_player_unban)
        self.app.router.add_post("/api/players/op", self.api_player_op)
        self.app.router.add_post("/api/players/deop", self.api_player_deop)
        self.app.router.add_post("/api/players/whitelist", self.api_player_whitelist)
        self.app.router.add_get("/api/plugins", self.api_plugins)
        self.app.router.add_post("/api/plugins/reload", self.api_plugins_reload)
        self.app.router.add_get("/api/updates/status", self.api_updates_status)
        self.app.router.add_post("/api/updates/check", self.api_updates_check)
        self.app.router.add_post("/api/updates/download", self.api_updates_download)
        self.app.router.add_post("/api/updates/apply", self.api_updates_apply)
        self.app.router.add_post("/api/updates/clear", self.api_updates_clear)
        self.app.router.add_get("/discord/oauth/start", self.discord_oauth_start)
        self.app.router.add_get("/discord/oauth/callback", self.discord_oauth_callback)

        if self.web_root.exists():
            self.app.router.add_static("/static", self.web_root)

    def token_required(self) -> bool:
        # Loopback-only panels may run without a token for local use.
        # Anything bound off-loopback requires a token to be configured.
        if self.token:
            return True
        return self.host not in LOOPBACK_HOSTS

    def check_auth(self, request):
        self.cleanup_auth()

        if not self.token_required():
            return True

        if not self.token:
            self.ctx.logger.warning(
                "[WebPanel] Refusing request: panel is exposed off-loopback with no token configured"
            )
            return False

        # Dedicated AI key: separate from the human panel token so it can
        # be rotated/revoked independently. Full scope, always audited.
        ai_key = request.headers.get("X-AI-Token", "").strip()
        if ai_key and self.ai_token and hmac.compare_digest(ai_key, self.ai_token):
            return True

        auth = request.headers.get("Authorization", "")

        if auth.startswith("Bearer "):
            presented = auth.removeprefix("Bearer ").strip()
            if self.token and presented and hmac.compare_digest(presented, self.token):
                return True
            if self.ai_token and presented and hmac.compare_digest(presented, self.ai_token):
                return True
            session = self.sessions.get(presented)
            if session and session["expires_at"] > time.time():
                return True
            return False

        session_token = request.cookies.get("watchdog_session", "")
        session = self.sessions.get(session_token)
        if session and session["expires_at"] > time.time():
            return True

        return False

    async def require_auth(self, request):
        if not self.check_auth(request):
            raise web.HTTPUnauthorized(text="Unauthorized")

    async def index(self, request):
        if not self.check_auth(request):
            return await self.login(request)

        index_file = self.web_root / "index.html"

        if not index_file.exists():
            return web.Response(
                text="Watchdog Web Panel missing web/index.html",
                status=500,
            )

        return web.FileResponse(index_file)

    async def login(self, request):
        if not self.token:
            raise web.HTTPFound("/")

        login_file = self.web_root / "login.html"

        if not login_file.exists():
            return web.Response(
                text="Watchdog Web Panel missing web/login.html",
                status=500,
            )

        return web.FileResponse(login_file)

    async def api_auth_request(self, request):
        if not self.token:
            return web.json_response({
                "ok": False,
                "error": "Web panel authentication is disabled.",
            }, status=404)

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

        player = str(data.get("player", "")).strip()
        if not player or len(player) > 16 or not player.replace("_", "").isalnum():
            return web.json_response({"ok": False, "error": "Enter a valid Minecraft player name"}, status=400)

        if self._login_throttled(player.lower()):
            return web.json_response({"ok": False, "error": "Too many attempts, try again later"}, status=429)

        if not self.player_has_panel_permission(player):
            return web.json_response({
                "ok": False,
                "error": f"{player} does not have the required Minecraft permissions",
            }, status=403)

        server = getattr(self.ctx, "server_process", None)
        process = getattr(server, "process", None) if server else None
        if not server or not process or process.returncode is not None:
            return web.json_response({"ok": False, "error": "Minecraft server is not running"}, status=503)

        code = f"{secrets.randbelow(1000000):06d}"
        self.login_codes[player.lower()] = {
            "player": player,
            "code": code,
            "expires_at": time.time() + self.code_ttl_seconds,
        }

        message = f"Watchdog web login code: {code}"
        await server.send_command(
            f"tellraw {player} {json.dumps({'text': message, 'color': 'gold'})}"
        )

        return web.json_response({
            "ok": True,
            "player": player,
            "expires_in": self.code_ttl_seconds,
        })

    async def api_auth_verify(self, request):
        if not self.token:
            return web.json_response({
                "ok": False,
                "error": "Web panel authentication is disabled.",
            }, status=404)

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

        player = str(data.get("player", "")).strip()
        code = str(data.get("code", "")).strip()
        pending = self.login_codes.get(player.lower())

        if self._login_throttled(player.lower()):
            return web.json_response({"ok": False, "error": "Too many attempts, try again later"}, status=429)

        if (
            not pending
            or pending["expires_at"] <= time.time()
            or not hmac.compare_digest(str(pending["code"]), code)
        ):
            self._record_login_failure(player.lower())
            return web.json_response({"ok": False, "error": "Invalid or expired login code"}, status=401)

        if not self.player_has_panel_permission(player):
            return web.json_response({
                "ok": False,
                "error": f"{player} does not have the required Minecraft permissions",
            }, status=403)

        session_token = secrets.token_urlsafe(32)
        self.sessions[session_token] = {
            "player": pending["player"],
            "expires_at": time.time() + self.session_ttl_seconds,
        }
        self.login_codes.pop(player.lower(), None)

        response = web.json_response({
            "ok": True,
            "token": session_token,
            "player": pending["player"],
            "expires_in": self.session_ttl_seconds,
        })
        response.set_cookie(
            "watchdog_session",
            session_token,
            max_age=self.session_ttl_seconds,
            httponly=True,
            samesite="Strict",
        )
        return response

    async def api_auth_me(self, request):
        await self.require_auth(request)

        if not self.token_required():
            return web.json_response({
                "ok": True,
                "player": "local",
                "expires_at": None,
            })

        session = self.session_from_request(request)
        return web.json_response({
            "ok": True,
            "player": session.get("player") if session else "token",
            "expires_at": session.get("expires_at") if session else None,
        })

    async def api_auth_logout(self, request):
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            self.sessions.pop(auth.removeprefix("Bearer ").strip(), None)

        cookie_token = request.cookies.get("watchdog_session", "")
        if cookie_token:
            self.sessions.pop(cookie_token, None)

        response = web.json_response({"ok": True})
        response.del_cookie("watchdog_session")
        return response

    def discord_bot_plugin(self):
        loader = getattr(self.ctx, "plugin_loader", None)
        plugins = getattr(loader, "plugins", {}) if loader else {}
        return plugins.get("discord_bot")

    async def discord_oauth_start(self, request):
        plugin = self.discord_bot_plugin()
        handler = getattr(plugin, "oauth_start", None)

        if not callable(handler):
            return web.Response(text="Discord linking is not available.", status=404)

        return await handler(request)

    async def discord_oauth_callback(self, request):
        plugin = self.discord_bot_plugin()
        handler = getattr(plugin, "oauth_callback", None)

        if not callable(handler):
            return web.Response(text="Discord linking is not available.", status=404)

        return await handler(request)

    async def api_status(self, request):
        await self.require_auth(request)

        server = getattr(self.ctx, "server_process", None)
        server_running = False
        process_alive = False
        startup_validated = False

        if server:
            process = getattr(server, "process", None)

            if process:
                process_alive = process.returncode is None
                server_running = process_alive
                startup_validated = bool(getattr(server, "startup_validated", False))

        bridge_status = {
            "ok": False,
            "bridge": "starting" if process_alive and not startup_validated else "offline",
        }
        bridge = getattr(self.ctx, "aetherreach", None)

        if bridge and startup_validated:
            bridge_status = await bridge.status()
            if bridge_status is None:
                bridge_status = {"ok": False, "bridge": "offline"}

        return web.json_response({
            "ok": True,
            "watchdog": "online",
            "server_running": server_running,
            "process_alive": process_alive,
            "startup_validated": startup_validated,
            "aetherreach": bridge_status,
            "plugins": self.ctx.plugin_loader.list_plugins() if getattr(self.ctx, "plugin_loader", None) else [],
        })

    def _tail_lines(self, log_file, limit: int):
        from collections import deque

        if not log_file.exists():
            return []
        with log_file.open(encoding="utf-8", errors="replace") as handle:
            return list(deque(handle, maxlen=limit))

    async def api_players(self, request):
        await self.require_auth(request)

        bridge = getattr(self.ctx, "aetherreach", None)
        status = await bridge.status() if bridge else None

        if not status:
            return web.json_response({
                "ok": False,
                "error": "Helper bridge is offline or not configured",
            }, status=502)

        players = status.get("players", status.get("playersOnline", []))
        return web.json_response({
            "ok": True,
            "players_online": status.get("playersOnline", len(players) if isinstance(players, list) else 0),
            "max_players": status.get("maxPlayers", 0),
            "players": players,
            "bridge": status.get("bridge", "online"),
        })

    async def api_logs(self, request):
        await self.require_auth(request)

        log_file = self.ctx.log_file("wrapper.log")

        return web.json_response({
            "ok": True,
            "lines": self._tail_lines(log_file, 200),
        })

    async def api_terminal(self, request):
        await self.require_auth(request)

        source = request.query.get("source", "wrapper")
        try:
            limit = int(request.query.get("limit", 300))
        except (TypeError, ValueError):
            return web.json_response({
                "ok": False,
                "error": "Invalid limit",
            }, status=400)
        limit = max(20, min(limit, 1000))

        if source == "minecraft":
            log_file = self.ctx.log_file("minecraft_console.log")
        else:
            log_file = self.ctx.log_file("wrapper.log")

        lines = self._tail_lines(log_file, limit) if log_file.exists() else []

        return web.json_response({
            "ok": True,
            "source": source,
            "lines": lines,
        })

    async def api_commands(self, request):
        await self.require_auth(request)

        return web.json_response({
            "ok": True,
            "commands": self.ctx.command_registry.list_commands(),
        })

    async def api_command(self, request):
        await self.require_auth(request)

        try:
            data = await request.json()
        except Exception:
            return web.json_response({
                "ok": False,
                "error": "Invalid JSON",
            }, status=400)

        command = str(data.get("command", "")).strip()

        if not command:
            return web.json_response({
                "ok": False,
                "error": "Missing command",
            }, status=400)

        result = None

        lowered = command.lower()

        if lowered.startswith("watchdog") or lowered.startswith("wrapper"):
            result = await self.ctx.command_registry.execute(command)
            return web.json_response(result.to_dict(), status=200 if result.ok else 400)

        if command.startswith("/"):
            command = command[1:]

        server = getattr(self.ctx, "server_process", None)

        if not server:
            return web.json_response({
                "ok": False,
                "error": "Server controller not available",
            }, status=500)

        try:
            if hasattr(server, "send_command"):
                await server.send_command(command)
            elif hasattr(server, "send"):
                await server.send(command)
            elif getattr(server, "process", None) and server.process.stdin and not server.process.stdin.is_closing():
                server.process.stdin.write((command + "\n").encode())
                await server.process.stdin.drain()
            else:
                return web.json_response({
                    "ok": False,
                    "error": "No command interface found",
                }, status=500)
        except (BrokenPipeError, ConnectionResetError) as exc:
            return web.json_response({
                "ok": False,
                "error": f"Server pipe is closed: {exc}",
            }, status=500)

        self.audit(request, "command", command[:200])

        return web.json_response({
            "ok": True,
            "command": command,
        })

    async def api_veil(self, request):
        await self.require_auth(request)

        try:
            data = await request.json()
        except Exception:
            return web.json_response({
                "ok": False,
                "error": "Invalid JSON",
            }, status=400)

        message = str(data.get("message", "")).strip()

        if not message:
            return web.json_response({
                "ok": False,
                "error": "Missing message",
            }, status=400)

        bridge = getattr(self.ctx, "aetherreach", None)

        if not bridge:
            return web.json_response({
                "ok": False,
                "error": "Helper bridge not available",
            }, status=500)

        delivered = await bridge.veil(message)

        self.audit(request, "veil", message[:200])

        if not delivered:
            return web.json_response({
                "ok": False,
                "error": "Helper bridge is offline or rejected the message",
            }, status=502)

        return web.json_response({
            "ok": True,
            "message": message,
        })

    async def api_restart(self, request):
        await self.require_auth(request)

        dry_run = request.query.get("dry_run", "").lower() in {"1", "true", "yes"}

        server = getattr(self.ctx, "server_process", None)
        process = getattr(server, "process", None) if server else None
        running = bool(process and process.returncode is None)

        if dry_run:
            return web.json_response({
                "ok": True,
                "dry_run": True,
                "server_running": running,
                "would": "stop then start the server" if running else "start the server",
            })

        self.audit(request, "restart", "")

        result = await self.ctx.command_registry.execute("watchdog server restart")
        return web.json_response(result.to_dict(), status=200 if result.ok else 500)

    # ---- AI control surface: server lifecycle ----

    def _server_running(self) -> bool:
        server = getattr(self.ctx, "server_process", None)
        process = getattr(server, "process", None) if server else None
        return bool(process and process.returncode is None)

    async def _lifecycle(self, request, watchdog_command: str, dry_would: str):
        await self.require_auth(request)
        dry_run = request.query.get("dry_run", "").lower() in {"1", "true", "yes"}
        running = self._server_running()
        if dry_run:
            return web.json_response({
                "ok": True, "dry_run": True,
                "server_running": running, "would": dry_would,
            })
        self.audit(request, watchdog_command, "")
        result = await self.ctx.command_registry.execute("watchdog " + watchdog_command)
        return web.json_response(result.to_dict(), status=200 if result.ok else 500)

    async def api_server_start(self, request):
        return await self._lifecycle(request, "server start", "start the server")

    async def api_server_stop(self, request):
        return await self._lifecycle(request, "server stop", "gracefully stop the server")

    async def api_server_kill(self, request):
        return await self._lifecycle(request, "server kill", "force-kill the server process")

    # ---- AI control surface: in-game admin ----

    @staticmethod
    def _clean_player(value) -> str:
        name = str(value or "").strip()
        if not name or len(name) > 16 or not name.replace("_", "").isalnum():
            raise ValueError(f"Invalid Minecraft player name: {value!r}")
        return name

    async def _mc(self, request, action: str, mc_command: str):
        await self.require_auth(request)
        server = getattr(self.ctx, "server_process", None)
        if not server:
            return web.json_response({"ok": False, "error": "Server controller not available"}, status=500)
        self.audit(request, action, mc_command[:200])
        delivered = await server.send_command(mc_command)
        if not delivered:
            return web.json_response({"ok": False, "error": "Server is not accepting commands"}, status=502)
        return web.json_response({"ok": True, "command": mc_command})

    async def _mc_body(self, request):
        try:
            return await request.json()
        except Exception:
            return None

    async def api_say(self, request):
        data = await self._mc_body(request)
        if not isinstance(data, dict) or not str(data.get("message", "")).strip():
            return web.json_response({"ok": False, "error": "Missing message"}, status=400)
        return await self._mc(request, "say", "say " + str(data["message"]).strip()[:500])

    async def _player_action(self, request, action: str, build):
        data = await self._mc_body(request)
        if not isinstance(data, dict):
            return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)
        try:
            player = self._clean_player(data.get("player") or data.get("user"))
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        reason = str(data.get("reason", "")).strip()[:200]
        return await self._mc(request, action, build(player, reason))

    async def api_player_kick(self, request):
        return await self._player_action(
            request, "kick",
            lambda player, reason: f"kick {player} {reason or 'Kicked via WatchDog API'}".strip(),
        )

    async def api_player_ban(self, request):
        return await self._player_action(
            request, "ban",
            lambda player, reason: f"ban {player} {reason or 'Banned via WatchDog API'}".strip(),
        )

    async def api_player_unban(self, request):
        return await self._player_action(
            request, "unban", lambda player, reason: f"pardon {player}",
        )

    async def api_player_op(self, request):
        return await self._player_action(
            request, "op", lambda player, reason: f"op {player}",
        )

    async def api_player_deop(self, request):
        return await self._player_action(
            request, "deop", lambda player, reason: f"deop {player}",
        )

    async def api_player_whitelist(self, request):
        data = await self._mc_body(request)
        if not isinstance(data, dict):
            return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)
        try:
            player = self._clean_player(data.get("player") or data.get("user"))
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        sub = str(data.get("action", "add")).strip().lower()
        if sub not in {"add", "remove", "on", "off"}:
            return web.json_response({"ok": False, "error": "action must be add, remove, on, or off"}, status=400)
        if sub in {"on", "off"}:
            return await self._mc(request, "whitelist", f"whitelist {sub}")
        return await self._mc(request, "whitelist", f"whitelist {sub} {player}")

    # ---- AI control surface: plugins / updates / backups ----

    async def api_plugins(self, request):
        await self.require_auth(request)
        loader = getattr(self.ctx, "plugin_loader", None)
        return web.json_response({
            "ok": True,
            "plugins": loader.list_plugins() if loader else [],
        })

    async def api_plugins_reload(self, request):
        await self.require_auth(request)
        data = await self._mc_body(request)
        name = str((data or {}).get("name", "")).strip() if isinstance(data, dict) else ""
        command = f"watchdog plugin reload {name}" if name else "watchdog plugins reload"
        self.audit(request, "plugins-reload", name or "all")
        result = await self.ctx.command_registry.execute(command)
        return web.json_response(result.to_dict(), status=200 if result.ok else 500)

    async def _update_command(self, request, action: str, watchdog_command: str):
        await self.require_auth(request)
        self.audit(request, "updates-" + action, "")
        result = await self.ctx.command_registry.execute("watchdog " + watchdog_command)
        return web.json_response(result.to_dict(), status=200 if result.ok else 500)

    async def api_updates_status(self, request):
        await self.require_auth(request)
        result = await self.ctx.command_registry.execute("watchdog atm11 update status")
        return web.json_response(result.to_dict(), status=200 if result.ok else 500)

    async def api_updates_check(self, request):
        return await self._update_command(request, "check", "atm11 update check")

    async def api_updates_download(self, request):
        return await self._update_command(request, "download", "atm11 update download")

    async def api_updates_apply(self, request):
        return await self._update_command(request, "apply", "atm11 update apply")

    async def api_updates_clear(self, request):
        return await self._update_command(request, "clear", "atm11 update clear")

    async def api_backups(self, request):
        await self.require_auth(request)
        backups_dir = getattr(self.ctx, "backups_dir", None)
        items = []
        if backups_dir and backups_dir.exists():
            for entry in sorted(backups_dir.iterdir(), reverse=True)[:50]:
                try:
                    stat = entry.stat()
                except OSError:
                    continue
                items.append({"name": entry.name, "size": stat.st_size, "modified": stat.st_mtime})
        return web.json_response({"ok": True, "backups": items})

    async def api_metrics(self, request):
        await self.require_auth(request)
        metrics = {"wrapper": "online", "server_running": self._server_running()}
        try:
            import psutil
            proc = getattr(getattr(self.ctx, "server_process", None), "process", None)
            if proc is not None:
                p = psutil.Process(proc.pid)
                with p.oneshot():
                    metrics["server"] = {
                        "pid": proc.pid,
                        "cpu_percent": p.cpu_percent(interval=None),
                        "memory_mb": round(p.memory_info().rss / 1048576, 1),
                    }
        except Exception:
            pass
        return web.json_response({"ok": True, "metrics": metrics})

    # ---- AI control surface: event feed ----

    def record_event(self, kind: str, detail: str = "") -> None:
        self.event_seq += 1
        self.event_log.append({"seq": self.event_seq, "event": kind, "detail": detail[:500]})

    async def api_events(self, request):
        await self.require_auth(request)
        try:
            since = int(request.query.get("since", 0))
        except (TypeError, ValueError):
            return web.json_response({"ok": False, "error": "Invalid since"}, status=400)
        events = [e for e in self.event_log if e["seq"] > since]
        return web.json_response({"ok": True, "latest": self.event_seq, "events": events[-100:]})

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        self._subscribe_event_feed()

        self.ctx.logger.info(
            "[WebPanel] Listening on http://%s:%s",
            self.host,
            self.port,
        )

    def _subscribe_event_feed(self) -> None:
        try:
            from wrapper.core.events import (
                ChatMessageEvent,
                PlayerJoinEvent,
                PlayerLeaveEvent,
                ServerCrashEvent,
                ServerStartedEvent,
                ServerStoppedEvent,
                ServerStoppingEvent,
            )
        except Exception:
            return

        bus = getattr(self.ctx, "event_bus", None)
        if not bus:
            return

        async def recorder(event):
            player = getattr(event, "player", "")
            reason = getattr(event, "reason", "") or getattr(event, "message", "")
            self.record_event(
                type(event).__name__,
                f"{player} {reason}".strip()[:500],
            )

        for event_type in (
            PlayerJoinEvent,
            PlayerLeaveEvent,
            ChatMessageEvent,
            ServerCrashEvent,
            ServerStartedEvent,
            ServerStoppingEvent,
            ServerStoppedEvent,
        ):
            try:
                bus.subscribe(event_type, recorder, owner="web_panel")
            except Exception:
                continue

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            self.ctx.logger.info("[WebPanel] Stopped")

    def session_from_request(self, request):
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return self.sessions.get(auth.removeprefix("Bearer ").strip())

        cookie_token = request.cookies.get("watchdog_session", "")
        if cookie_token:
            return self.sessions.get(cookie_token)

        return None

    def _login_throttled(self, player_key: str) -> bool:
        attempts = [
            ts for ts in self.login_attempts.get(player_key, [])
            if ts > time.time() - LOGIN_ATTEMPT_WINDOW_SECONDS
        ]
        self.login_attempts[player_key] = attempts
        return len(attempts) >= MAX_LOGIN_ATTEMPTS

    def _record_login_failure(self, player_key: str) -> None:
        attempts = [
            ts for ts in self.login_attempts.get(player_key, [])
            if ts > time.time() - LOGIN_ATTEMPT_WINDOW_SECONDS
        ]
        attempts.append(time.time())
        self.login_attempts[player_key] = attempts

    def request_actor(self, request) -> str:
        ai_key = request.headers.get("X-AI-Token", "").strip()
        if ai_key and self.ai_token and hmac.compare_digest(ai_key, self.ai_token):
            return "ai"
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            presented = auth.removeprefix("Bearer ").strip()
            if self.ai_token and presented and hmac.compare_digest(presented, self.ai_token):
                return "ai"
            if self.token and presented and hmac.compare_digest(presented, self.token):
                return "panel-token"
        session = self.session_from_request(request)
        if session:
            return str(session.get("player") or "session")
        return "local" if not self.token_required() else "unknown"

    def audit(self, request, action: str, detail: str = "") -> None:
        self.ctx.logger.info(
            "[WebPanel] AUDIT actor=%s action=%s %s",
            self.request_actor(request),
            action,
            detail,
        )

    def cleanup_auth(self):
        now = time.time()
        self.login_codes = {
            key: value for key, value in self.login_codes.items()
            if value["expires_at"] > now
        }
        self.sessions = {
            key: value for key, value in self.sessions.items()
            if value["expires_at"] > now
        }

    def player_has_panel_permission(self, player: str) -> bool:
        ops_file = self.ctx.server_dir / "ops.json"
        if not ops_file.exists():
            return False

        try:
            ops = json.loads(ops_file.read_text(encoding="utf-8"))
        except Exception as exc:
            self.ctx.logger.warning("[WebPanel] Could not read ops.json: %s", exc)
            return False

        if not isinstance(ops, list):
            self.ctx.logger.warning("[WebPanel] ops.json is not a list; denying panel access")
            return False

        player_key = player.lower()
        for entry in ops:
            if str(entry.get("name", "")).lower() == player_key:
                return int(entry.get("level", 0)) >= self.required_op_level

        return False
