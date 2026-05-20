from aiohttp import web
import json
from pathlib import Path
import secrets
import time


class WebPanel:
    def __init__(self, ctx, host="127.0.0.1", port=8080, token=""):
        self.ctx = ctx
        self.host = host
        self.port = int(port)
        self.token = token
        self.login_codes = {}
        self.sessions = {}
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
        self.app.router.add_get("/api/logs", self.api_logs)
        self.app.router.add_get("/api/terminal", self.api_terminal)
        self.app.router.add_get("/api/commands", self.api_commands)
        self.app.router.add_post("/api/command", self.api_command)
        self.app.router.add_post("/api/veil", self.api_veil)
        self.app.router.add_post("/api/restart", self.api_restart)

        if self.web_root.exists():
            self.app.router.add_static("/static", self.web_root)

    def check_auth(self, request):
        self.cleanup_auth()

        if not self.token:
            return True

        auth = request.headers.get("Authorization", "")

        if auth == f"Bearer {self.token}":
            return True

        if auth.startswith("Bearer "):
            session = self.sessions.get(auth.removeprefix("Bearer ").strip())
            if session and session["expires_at"] > time.time():
                return True

        session_token = request.cookies.get("watchdog_session", "")
        session = self.sessions.get(session_token)
        if session and session["expires_at"] > time.time():
            return True

        query_token = request.query.get("token", "")

        return query_token == self.token or query_token in self.sessions

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

        if not pending or pending["expires_at"] <= time.time() or pending["code"] != code:
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

        if not self.token:
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
            "wrapper": "online",
            "server_running": server_running,
            "process_alive": process_alive,
            "startup_validated": startup_validated,
            "aetherreach": bridge_status,
            "plugins": self.ctx.plugin_loader.list_plugins() if getattr(self.ctx, "plugin_loader", None) else [],
        })

    async def api_logs(self, request):
        await self.require_auth(request)

        log_file = self.ctx.log_file("wrapper.log")

        if not log_file.exists():
            return web.json_response({
                "ok": True,
                "lines": [],
            })

        lines = log_file.read_text(errors="replace").splitlines()
        lines = lines[-200:]

        return web.json_response({
            "ok": True,
            "lines": lines,
        })

    async def api_terminal(self, request):
        await self.require_auth(request)

        source = request.query.get("source", "wrapper")
        limit = int(request.query.get("limit", 300))
        limit = max(20, min(limit, 1000))

        if source == "minecraft":
            log_file = self.ctx.log_file("minecraft_console.log")
        else:
            log_file = self.ctx.log_file("wrapper.log")

        lines = []
        if log_file.exists():
            lines = log_file.read_text(errors="replace").splitlines()[-limit:]

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

        if command.lower().startswith("wrapper"):
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

        if hasattr(server, "send_command"):
            await server.send_command(command)
        elif hasattr(server, "send"):
            await server.send(command)
        elif getattr(server, "process", None) and server.process.stdin:
            server.process.stdin.write((command + "\n").encode())
            await server.process.stdin.drain()
        else:
            return web.json_response({
                "ok": False,
                "error": "No command interface found",
            }, status=500)

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

        await bridge.veil(message)

        return web.json_response({
            "ok": True,
            "message": message,
        })

    async def api_restart(self, request):
        await self.require_auth(request)

        result = await self.ctx.command_registry.execute("wrapper restart")
        return web.json_response(result.to_dict(), status=200 if result.ok else 500)

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        self.ctx.logger.info(
            "[WebPanel] Listening on http://%s:%s",
            self.host,
            self.port,
        )

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

        return self.sessions.get(request.query.get("token", ""))

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

        player_key = player.lower()
        for entry in ops:
            if str(entry.get("name", "")).lower() == player_key:
                return int(entry.get("level", 0)) >= self.required_op_level

        return False
