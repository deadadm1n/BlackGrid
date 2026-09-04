import asyncio
import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
import discord
from aiohttp import web

from wrapper.core.plugin_base import WrapperPlugin
from wrapper.core.events import (
    PlayerJoinEvent,
    PlayerLeaveEvent,
    ChatMessageEvent,
    DiscordLinkEvent,
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
        self.guild = None
        self.rank_roles = {}
        self.bot_task = None
        self.ready = asyncio.Event()

    async def register_events(self, ctx):
        self.ctx = ctx

        ctx.event_bus.subscribe(ServerStartedEvent, self.on_server_started)
        ctx.event_bus.subscribe(ServerStoppingEvent, self.on_server_stopping)
        ctx.event_bus.subscribe(ServerStoppedEvent, self.on_server_stopped)
        ctx.event_bus.subscribe(PlayerJoinEvent, self.on_player_join)
        ctx.event_bus.subscribe(PlayerLeaveEvent, self.on_player_leave)
        ctx.event_bus.subscribe(DiscordLinkEvent, self.on_discord_link_request)

        # Fallback only. Normal Minecraft chat now comes through:
        # WatchDog Helper -> HTTP -> MinecraftEventReceiver -> send_minecraft_chat()
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
        intents.members = True

        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready():
            try:
                self.channel = await self.client.fetch_channel(channel_id)
            except Exception as e:
                ctx.logger.error("[DiscordBot] Could not fetch channel ID %s: %s", channel_id, e)
                return

            self.guild = await self.resolve_guild(ctx)
            if self.ranks_enabled():
                await self.ensure_rank_roles()

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
                if not bool(self.settings.get("mc_console_enabled", True)):
                    await message.add_reaction("?")
                    return

                permissions = message.author.guild_permissions

                if not permissions.manage_messages:
                    await message.add_reaction("?")
                    return

                command = content[4:].strip()

                if not command:
                    return

                await self.send_mc_command(ctx, command)
                await message.add_reaction("?")
                return

            if await self.handle_rank_command(message, content):
                return

            if content.startswith("!"):
                return

            safe_name = message.author.display_name.replace("@", "")
            safe_content = content.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

            # Primary path:
            # Discord -> WatchDog -> helper HTTP bridge -> Minecraft
            # channel_id is included so the helper's gameChatChannelId gate can verify it.
            delivered = await ctx.aetherreach.discord_message(
                safe_name,
                safe_content,
                channel_id=str(self.settings.get("channel_id", "")),
            )

            if delivered:
                return

            # Fallback path if the helper bridge is down.
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

        @self.client.event
        async def on_member_join(member):
            await self.assign_default_member_role(member)

        self.bot_task = asyncio.create_task(self.client.start(token))
        ctx.logger.info("[DiscordBot] Starting Discord bot task")

    async def on_plugin_unload(self, ctx):
        # Reload path: close the client quietly (no offline spam),
        # so a fresh on_wrapper_start doesn't leak a second client.
        self.ready.clear()
        if self.client:
            try:
                await self.client.close()
            except Exception:
                pass
        if self.bot_task and not self.bot_task.done():
            self.bot_task.cancel()
        self.client = None
        self.channel = None
        self.guild = None
        self.bot_task = None

    async def on_wrapper_stop(self, ctx):
        if self.client:
            await self.send_discord(
                "```ansi\n"
                f"[{self.helper_display_name()}] Server link closed.\n"
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

    async def send_discord(self, message: str, channel_id=None) -> bool:
        if not self.client:
            return False

        try:
            await asyncio.wait_for(self.ready.wait(), timeout=15)
        except asyncio.TimeoutError:
            if self.ctx:
                self.ctx.logger.warning("[DiscordBot] Timed out waiting for Discord client readiness")
            return False

        channel = self.channel

        if channel_id:
            try:
                channel = await self.client.fetch_channel(int(channel_id))
            except Exception as e:
                if self.ctx:
                    self.ctx.logger.warning("[DiscordBot] Could not fetch channel ID %s: %s", channel_id, e)
                return False

        if not channel:
            return False

        try:
            await channel.send(message)
            return True
        except Exception:
            if self.ctx:
                self.ctx.logger.exception("[DiscordBot] Failed to send Discord message")
            return False

    def server_display_name(self):
        return str(self.settings.get("server_name", "") or "Minecraft").strip()

    def helper_display_name(self):
        return str(self.settings.get("helper_name", "") or "WatchDog").strip()

    async def send_minecraft_chat(self, player: str, message: str):
        """
        Primary Minecraft -> Discord bridge path.

        Called by:
        WatchDog Helper Java chat event
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

        safe_player = str(player).replace("@", "")
        safe_message = str(message).replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        if len(safe_message) > 1900:
            safe_message = safe_message[:1900] + "..."

        try:
            await self.channel.send(f"**[{self.server_display_name()}] {safe_player}** > {safe_message}")

            if self.ctx:
                self.ctx.logger.info(
                    "[DiscordBot] Minecraft chat sent to Discord: %s: %s",
                    player,
                    message,
                )

        except Exception:
            if self.ctx:
                self.ctx.logger.exception("[DiscordBot] Failed to send Minecraft chat")

    def ranks_enabled(self):
        return bool(self.settings.get("ranks", {}).get("enabled", False))

    async def resolve_guild(self, ctx):
        guild_id = int(self.settings.get("guild_id", 0) or 0)

        try:
            if guild_id:
                return await self.client.fetch_guild(guild_id)
            if self.channel and getattr(self.channel, "guild", None):
                return self.channel.guild
        except Exception as e:
            ctx.logger.error("[DiscordBot] Could not resolve guild for rank handling: %s", e)

        return None

    def rank_definitions(self):
        ranks_cfg = self.settings.get("ranks", {})
        roles_cfg = ranks_cfg.get("roles")

        if isinstance(roles_cfg, dict) and roles_cfg:
            definitions = {}
            for key, body in roles_cfg.items():
                if not isinstance(body, dict):
                    body = {"name": str(body)}

                role_name = str(body.get("name", key)).strip()
                if not role_name:
                    continue

                definitions[str(key).lower()] = {
                    "key": str(key).lower(),
                    "name": role_name,
                    "role_name": role_name,
                    "color": body.get("color", ranks_cfg.get("default_role_color", "#99aab5")),
                    "auto_assign": bool(body.get("auto_assign", False)),
                }

            return definitions

        default_role = str(ranks_cfg.get("default_role_name", "")).strip()
        if not default_role:
            return {}

        return {
            "member": {
                "key": "member",
                "name": default_role,
                "role_name": default_role,
                "color": ranks_cfg.get("default_role_color", "#99aab5"),
                "auto_assign": True,
            }
        }

    async def ensure_rank_roles(self):
        if not self.guild:
            if self.ctx:
                self.ctx.logger.warning("[DiscordBot] Rank handling enabled but guild is unavailable")
            return

        ranks_cfg = self.settings.get("ranks", {})
        create_missing = bool(ranks_cfg.get("create_missing_roles", True))
        configured = self.rank_definitions()

        existing_roles = {role.name: role for role in getattr(self.guild, "roles", [])}
        if not existing_roles and hasattr(self.guild, "fetch_roles"):
            existing_roles = {role.name: role for role in await self.guild.fetch_roles()}
        self.rank_roles = {}

        for key, spec in configured.items():
            name = str(spec.get("role_name", key)).strip()
            if not name:
                continue

            role = existing_roles.get(name)
            if role is None and create_missing:
                try:
                    role = await self.guild.create_role(
                        name=name,
                        color=self.parse_color(spec.get("color", ranks_cfg.get("default_role_color", "#99aab5"))),
                        hoist=False,
                        mentionable=False,
                        reason="WatchDog Discord role setup",
                    )
                    if self.ctx:
                        self.ctx.logger.info("[DiscordBot] Created rank role: %s", name)
                except Exception:
                    if self.ctx:
                        self.ctx.logger.exception("[DiscordBot] Failed to create rank role: %s", name)
                    continue

            if role is not None:
                self.rank_roles[key.lower()] = role

    async def handle_rank_command(self, message, content):
        if not self.ranks_enabled():
            return False

        prefix = str(self.settings.get("ranks", {}).get("link_command", "!link")).strip() or "!link"
        if content == prefix or content.startswith(prefix + " "):
            await self.handle_link_command(message, content[len(prefix):].strip())
            return True

        if content == "!ranks" or content.startswith("!ranks "):
            await self.handle_ranks_command(message, content)
            return True

        return False

    async def handle_ranks_command(self, message, content):
        if not self.member_can_manage_ranks(message.author):
            await message.add_reaction("?")
            return

        parts = content.split()
        action = parts[1].lower() if len(parts) > 1 else "list"

        if action == "setup":
            await self.ensure_rank_roles()
            await message.channel.send(self.rank_list_message("Rank roles checked."))
            return

        if action == "sync":
            synced = await self.sync_all_linked_members()
            await message.channel.send(f"Checked Discord member role for {synced} linked account(s).")
            return

        if action == "list":
            await message.channel.send(self.rank_list_message("Configured rank roles:"))
            return

        await message.channel.send("Usage: `!ranks list`, `!ranks setup`, or `!ranks sync`")

    async def handle_link_command(self, message, code):
        code = code.strip().upper()
        if not code:
            await message.channel.send("Run `/discord` in-game and click the link it gives you.")
            return

        pending = self.load_rank_state("pending_links")
        link = pending.get(code)
        if not link:
            await message.channel.send("That link token was not found. Run `/discord` in-game for a fresh link.")
            return

        expires_at = float(link.get("expires_at", 0))
        if expires_at and time.time() > expires_at:
            pending.pop(code, None)
            self.save_rank_state("pending_links", pending)
            await message.channel.send("That link expired. Run `/discord` in-game again.")
            return

        links = self.load_rank_state("linked_accounts")
        links[str(message.author.id)] = {
            "discord_id": str(message.author.id),
            "discord_name": str(message.author),
            "uuid": link["uuid"],
            "player": link["player"],
            "linked_at": time.time(),
        }
        self.save_rank_state("linked_accounts", links)

        pending.pop(code, None)
        self.save_rank_state("pending_links", pending)

        if self.settings.get("ranks", {}).get("sync_on_link", True):
            await self.assign_default_member_role(message.author)

        await message.channel.send(f"Linked Discord account to Minecraft player `{link['player']}`.")

    def member_can_manage_ranks(self, member):
        permission = str(self.settings.get("ranks", {}).get("manage_permission", "manage_roles"))
        permissions = getattr(member, "guild_permissions", None)
        return bool(permissions and getattr(permissions, permission, False))

    def rank_list_message(self, title):
        configured = self.rank_definitions()
        lines = [title]
        for key, spec in configured.items():
            name = spec.get("role_name", key)
            role = self.rank_roles.get(key.lower())
            status = "ready" if role else "missing"
            lines.append(f"- `{key}` -> `{name}` ({status})")
        return "\n".join(lines)

    async def on_discord_link_request(self, event):
        if not self.ranks_enabled():
            return

        ttl = int(self.settings.get("ranks", {}).get("link_ttl_seconds", 600))
        pending = self.load_rank_state("pending_links")
        pending[event.code.upper()] = {
            "uuid": event.uuid,
            "player": event.player,
            "code": event.code.upper(),
            "created_at": time.time(),
            "expires_at": time.time() + max(ttl, 60),
        }
        self.save_rank_state("pending_links", pending)

        if self.ctx:
            self.ctx.logger.info("[DiscordBot] Stored Discord link code for %s", event.player)

    def oauth_settings(self):
        ranks_cfg = self.settings.get("ranks", {})
        oauth_cfg = ranks_cfg.get("oauth", {})
        if not isinstance(oauth_cfg, dict):
            oauth_cfg = {}
        return oauth_cfg

    def oauth_enabled(self):
        oauth_cfg = self.oauth_settings()
        return bool(
            oauth_cfg.get("enabled", False)
            and oauth_cfg.get("client_id")
            and oauth_cfg.get("client_secret")
            and oauth_cfg.get("redirect_uri")
        )

    async def oauth_start(self, request):
        state = str(request.query.get("state", "")).strip().upper()
        pending = self.load_rank_state("pending_links")

        if not state or state not in pending:
            return web.Response(text="That Minecraft Discord link is invalid or expired.", status=404)

        link = pending[state]
        expires_at = float(link.get("expires_at", 0))
        if expires_at and time.time() > expires_at:
            pending.pop(state, None)
            self.save_rank_state("pending_links", pending)
            return web.Response(text="That Minecraft Discord link expired. Run /discord again.", status=410)

        if not self.oauth_enabled():
            return web.Response(text="Discord OAuth linking is not configured yet.", status=503)

        oauth_cfg = self.oauth_settings()
        params = {
            "client_id": str(oauth_cfg.get("client_id", "")),
            "redirect_uri": str(oauth_cfg.get("redirect_uri", "")),
            "response_type": "code",
            "scope": "identify guilds.join",
            "state": state,
        }

        raise web.HTTPFound("https://discord.com/oauth2/authorize?" + urlencode(params))

    async def oauth_callback(self, request):
        state = str(request.query.get("state", "")).strip().upper()
        oauth_code = str(request.query.get("code", "")).strip()

        if not state or not oauth_code:
            return web.Response(text="Discord did not return a valid link response.", status=400)

        pending = self.load_rank_state("pending_links")
        link = pending.get(state)

        if not link:
            return web.Response(text="That Minecraft Discord link was not found. Run /discord again.", status=404)

        expires_at = float(link.get("expires_at", 0))
        if expires_at and time.time() > expires_at:
            pending.pop(state, None)
            self.save_rank_state("pending_links", pending)
            return web.Response(text="That Minecraft Discord link expired. Run /discord again.", status=410)

        try:
            token_data = await self.exchange_oauth_code(oauth_code)
            user = await self.fetch_oauth_user(token_data["access_token"])
            member = await self.ensure_discord_member(str(user["id"]), token_data["access_token"])
        except Exception as e:
            if self.ctx:
                self.ctx.logger.exception("[DiscordBot] Discord OAuth link failed")
            return web.Response(text=f"Discord link failed: {e}", status=500)

        links = self.load_rank_state("linked_accounts")
        links[str(user["id"])] = {
            "discord_id": str(user["id"]),
            "discord_name": self.discord_user_name(user),
            "uuid": link["uuid"],
            "player": link["player"],
            "linked_at": time.time(),
        }
        self.save_rank_state("linked_accounts", links)

        pending.pop(state, None)
        self.save_rank_state("pending_links", pending)

        if member and self.settings.get("ranks", {}).get("sync_on_link", True):
            await self.assign_default_member_role(member)

        if self.ctx:
            self.ctx.logger.info("[DiscordBot] Linked %s to Discord user %s", link["player"], user["id"])

        return web.Response(
            text=(
                f"Linked Discord to Minecraft player {link['player']}. "
                "You can close this page and return to the server."
            )
        )

    async def exchange_oauth_code(self, oauth_code):
        oauth_cfg = self.oauth_settings()
        data = {
            "client_id": str(oauth_cfg.get("client_id", "")),
            "client_secret": str(oauth_cfg.get("client_secret", "")),
            "grant_type": "authorization_code",
            "code": oauth_code,
            "redirect_uri": str(oauth_cfg.get("redirect_uri", "")),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://discord.com/api/oauth2/token", data=data) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(payload.get("error_description") or payload.get("error") or "OAuth token exchange failed")
                return payload

    async def fetch_oauth_user(self, access_token):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError("Could not read Discord user profile")
                return payload

    async def ensure_discord_member(self, discord_id, access_token):
        if not self.guild:
            self.guild = await self.resolve_guild(self.ctx)

        if not self.guild:
            raise RuntimeError("Discord guild is unavailable")

        try:
            return await self.guild.fetch_member(int(discord_id))
        except discord.NotFound:
            pass

        bot_token = str(self.settings.get("token", "")).strip()
        if not bot_token:
            raise RuntimeError("Discord bot token is missing")

        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"https://discord.com/api/guilds/{self.guild.id}/members/{discord_id}",
                headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
                json={"access_token": access_token},
            ) as response:
                if response.status not in {200, 201, 204}:
                    payload = await response.text()
                    raise RuntimeError(f"Could not join Discord server: HTTP {response.status} {payload}")

        return await self.guild.fetch_member(int(discord_id))

    def discord_user_name(self, user):
        username = str(user.get("username", "unknown"))
        discriminator = str(user.get("discriminator", "0"))
        if discriminator and discriminator != "0":
            return f"{username}#{discriminator}"
        return username

    async def sync_all_linked_members(self):
        if not self.guild:
            return 0

        await self.ensure_rank_roles()
        links = self.load_rank_state("linked_accounts")
        count = 0

        for discord_id, link in links.items():
            try:
                member = await self.guild.fetch_member(int(discord_id))
            except Exception:
                continue
            await self.assign_default_member_role(member)
            count += 1

        return count

    async def sync_linked_player(self, player_name):
        if not self.guild or not player_name:
            return

        links = self.load_rank_state("linked_accounts")
        for discord_id, link in links.items():
            if str(link.get("player", "")).lower() != player_name.lower():
                continue
            try:
                member = await self.guild.fetch_member(int(discord_id))
            except Exception:
                continue
            await self.assign_default_member_role(member)

    async def sync_member_roles(self, member, link):
        await self.assign_default_member_role(member)

    async def assign_default_member_role(self, member):
        await self.ensure_rank_roles()
        configured = self.rank_definitions()
        desired_roles = [
            self.rank_roles[key]
            for key, spec in configured.items()
            if spec.get("auto_assign") and key in self.rank_roles
        ]
        to_add = [role for role in desired_roles if role not in member.roles]

        if not to_add:
            return

        try:
            await member.add_roles(*to_add, reason="WatchDog Discord member role")
        except discord.Forbidden:
            if self.ctx:
                self.ctx.logger.warning("[DiscordBot] Missing role hierarchy/permissions for Discord member role")
        except Exception:
            if self.ctx:
                self.ctx.logger.exception("[DiscordBot] Failed to assign Discord member role")

    def player_rank_keys(self, link):
        definitions = self.rank_definitions()
        keys = {
            key
            for key, spec in definitions.items()
            if str(spec.get("condition", "")).lower() == "always_active"
        }

        uuid = str(link.get("uuid", "")).lower()
        players = self.read_json5_object(self.ctx.resolve_path(self.settings.get("ranks", {}).get("players_file", "atm11/world/serverconfig/ftbranks/players.json5")))
        player_block = self.extract_block_for_key(players, uuid)
        keys.update(self.extract_rank_keys_from_block(player_block))

        teams_dir = self.ctx.resolve_path(self.settings.get("ranks", {}).get("ftbteams_player_dir", "atm11/world/ftbteams/player"))
        team_file = teams_dir / f"{uuid}.json5"
        keys.update(self.extract_rank_keys_from_block(self.read_json5_object(team_file)))

        return [key for key in keys if key in definitions]

    def rank_state_dir(self):
        path = self.ctx.state_dir / "discord_bot"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_rank_state(self, name):
        path = self.rank_state_dir() / f"{name}.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_rank_state(self, name, data):
        path = self.rank_state_dir() / f"{name}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(path)

    def read_json5_object(self, path):
        path = Path(path)
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"//.*", "", text)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        return text

    def extract_named_blocks(self, text):
        blocks = {}
        for match in re.finditer(r'(?m)^\s*"?([A-Za-z0-9_.:-]+)"?\s*:\s*\{', text or ""):
            key = match.group(1)
            start = match.end()
            depth = 1
            i = start
            while i < len(text) and depth:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            blocks[key] = text[start:i - 1]
        return blocks

    def extract_block_for_key(self, text, key):
        return self.extract_named_blocks(text).get(key, "")

    def extract_rank_keys_from_block(self, block):
        if not block:
            return set()
        ranks_block = self.extract_block_for_key(block, "ranks")
        if not ranks_block:
            return set()

        keys = set()
        for match in re.finditer(r'"?([A-Za-z0-9_.:-]+)"?\s*:', ranks_block):
            keys.add(match.group(1).lower())
        for match in re.finditer(r'"([A-Za-z0-9_.:-]+)"', ranks_block):
            keys.add(match.group(1).lower())
        return keys

    @staticmethod
    def extract_string(text, key):
        match = re.search(rf'"?{re.escape(key)}"?\s*:\s*"([^"]*)"', text or "")
        return match.group(1) if match else None

    def extract_rank_color(self, text):
        fmt = self.extract_string(text, "ftbranks.name_format") or ""
        color_map = {
            "0": "#000000", "1": "#0000aa", "2": "#00aa00", "3": "#00aaaa",
            "4": "#aa0000", "5": "#aa00aa", "6": "#ffaa00", "7": "#aaaaaa",
            "8": "#555555", "9": "#5555ff", "a": "#55ff55", "b": "#55ffff",
            "c": "#ff5555", "d": "#ff55ff", "e": "#ffff55", "f": "#ffffff",
        }
        match = re.search(r"[&" + chr(0xA7) + r"]([0-9a-fA-F])", fmt)
        if match:
            return color_map.get(match.group(1).lower())
        return None

    @staticmethod
    def parse_color(value):
        text = str(value or "#99aab5").strip().lstrip("#")
        try:
            return discord.Color(int(text, 16))
        except ValueError:
            return discord.Color.default()

    async def on_server_started(self, event):
        await self.send_discord(
            "```ansi\n"
            f"[{self.helper_display_name()}] Server is online.\n"
            "Monitoring systems active.\n"
            "```"
        )

        try:
            if self.ctx and getattr(self.ctx, "aetherreach", None):
                await self.ctx.aetherreach.veil(
                    "Server is online."
                )
        except Exception:
            if self.ctx:
                self.ctx.logger.exception("[DiscordBot] Failed to send startup veil message")

    async def on_server_stopping(self, event):
        await self.send_discord(
            "```ansi\n"
            f"[{self.helper_display_name()}] Shutdown sequence detected.\n"
            "Server entering controlled stop.\n"
            "```"
        )

    async def on_server_stopped(self, event):
        await self.send_discord(
            "```ansi\n"
            f"[{self.helper_display_name()}] Server stopped.\n"
            f"Exit code: {event.exit_code}\n"
            "```"
        )

    async def on_server_unexpected_exit(self, ctx, exit_code):
        await self.send_discord(
            "```ansi\n"
            f"[{self.helper_display_name()}] Server stopped unexpectedly.\n"
            f"Exit code: {exit_code}\n"
            "Recovery evaluation started.\n"
            "```"
        )

    async def on_server_restart_requested(self, ctx, reason, scheduled=False):
        restart_type = "Scheduled reset" if scheduled else "Emergency restart"
        await self.send_discord(
            "```ansi\n"
            f"[{self.helper_display_name()}] {restart_type} initiated.\n"
            f"Reason: {reason}\n"
            "Recovery sequence active.\n"
            "```"
        )

    async def on_player_join(self, event):
        await self.send_discord(
            f"`{event.player}` joined **{self.server_display_name()}**."
        )
        if self.ranks_enabled() and self.settings.get("ranks", {}).get("sync_on_join", True):
            await self.sync_linked_player(event.player)

    async def on_player_leave(self, event):
        await self.send_discord(
            f"`{event.player}` left **{self.server_display_name()}**."
        )

    async def on_mc_chat(self, event):
        """
        Fallback path only.

        Console regex chat relay should be disabled now.
        This remains in case CHAT_RELAY_FROM_LOGS is turned back on later.
        """
        await self.send_minecraft_chat(event.player, event.message)
