# AI Control Surface

This document is written for AI agents (and the operators who deploy them). It describes every HTTP endpoint an AI can use to administer Discord and WatchDog-managed game servers. All mutating calls are admin-scoped: treat tokens as root credentials.

## 1. Discord admin bridge (`discord-bot/`)

Node.js + discord.js v14. The bot logs in with a token and exposes a local HTTP API. No auto-posts, no auto-roles: it only acts on `POST /discord-command`.

- Base: `http://HOST:3000`
- Health: `GET /` → `{ok, bot}`
- OAuth landing: `GET /auth/callback?code=...&guild_id=...` → HTML confirmation (used as the invite `redirect_uri`)
- Command: `POST /discord-command` with JSON `{"type": ..., ...}`

The bot must be invited with Administrator (`permissions=8`) and have Server Members Intent + Message Content Intent enabled.

### Reads

| `type` | Fields | Returns |
|---|---|---|
| `guild-info` | — | `{guild: {id, name, memberCount, channels, roles}}` |
| `list-channels` | — | `{channels: [{id, name, type}]}` |
| `list-members` | `limit?` | `{members: [{id, tag, roles}]}` |
| `list-roles` | — | `{roles: [{id, name}]}` |
| `get-messages` | `channel?` (id or name), `limit?` (max 100) | `{channel, messages: [{id, author, content, at}]}` |

### Writes

| `type` | Fields |
|---|---|
| `send-message` | `channel?`, `message` (required) |
| `create-role` | `roleName`, `permissions?` (array of `PermissionFlagsBits` names, default `[Administrator]`), `color?` (int), `hoist?` (default true), `mentionable?` |
| `update-role` | `role` (id or name), `name?`, `color?` (int), `hoist?`, `mentionable?` |
| `delete-role` | `role` (id or name) |
| `assign-role` / `remove-role` | `user` (id or tag), `role` (id or name) |
| `create-channel` | `name`, `voice?` (bool) |
| `delete-channel` | `channel` (id or name) |
| `delete-message` | `channel`, `messageId` |
| `kick` / `ban` | `user`, `reason?` |
| `unban` | `user` (id), `reason?` |
| `timeout` | `user`, `minutes?` (default 10), `reason?` |

Notes:

- The bot cannot edit its own top integration role (Discord hierarchy). To show the bot in its own sidebar group, create a hoisted `Bot` role below it and assign it to the bot user.
- Errors are `{error}` with HTTP 400 (bad input), 404 (guild/channel/member/role not found), 500 (Discord rejected).

Example:

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"type":"create-role","roleName":"Moderator","permissions":["KickMembers","ModerateMembers","ManageMessages"],"color":255,"hoist":true}' \
  http://HOST:3000/discord-command
```

## 2. WatchDog panel API

Base: `http://HOST:PORT` (default `127.0.0.1:8080`, see `web_panel` in `WatchDog/config/wrapper.yaml`).

Auth (any one):

- `X-AI-Token: <WEB_PANEL_AI_TOKEN>` — dedicated AI key, full scope, every call audit-logged as `actor=ai`. **Use this.**
- `Authorization: Bearer <WEB_PANEL_TOKEN>` — human panel token.
- `watchdog_session` cookie — human login session.

Query-string tokens are not accepted. Empty tokens only work on loopback binds.

### Lifecycle

| Endpoint | Effect |
|---|---|
| `POST /api/server/start` | Start the game server (keeps wrapper alive) |
| `POST /api/server/stop` | Graceful stop (keeps wrapper alive) |
| `POST /api/server/kill` | Force-kill the process |
| `POST /api/restart` | Graceful restart |
| All above accept `?dry_run=1` | Returns what *would* happen, changes nothing |

### Players and chat

| Endpoint | Body |
|---|---|
| `POST /api/say` | `{"message"}` — broadcast to all players |
| `POST /api/players/kick` | `{"player", "reason?"}` |
| `POST /api/players/ban` | `{"player", "reason?"}` |
| `POST /api/players/unban` | `{"player"}` (id) |
| `POST /api/players/op` / `deop` | `{"player"}` |
| `POST /api/players/whitelist` | `{"action": "add\|remove\|on\|off", "player?"}` |
| `GET /api/players` | Online list from the helper bridge |

Player names are validated (`[A-Za-z0-9_]{3,16}`). All calls report delivered vs server-offline honestly.

### Ops, updates, backups, metrics, events

| Endpoint | Effect |
|---|---|
| `GET /api/status` | Wrapper/server/bridge/plugins snapshot |
| `GET /api/plugins` | Loaded plugin list |
| `POST /api/plugins/reload` | `{"name?"}` — one plugin or all |
| `GET /api/updates/status` | ATM11 update state |
| `POST /api/updates/check\|download\|apply\|clear` | Update pipeline (apply stops, installs, validates, rolls back) |
| `GET /api/backups` | Newest 50 backups with sizes |
| `GET /api/metrics` | Server CPU/RAM, running state |
| `GET /api/events?since=N` | Ring-buffer feed: joins, leaves, chat, crashes, start/stop |
| `GET /api/terminal?source=wrapper\|minecraft&limit=` | Log tail (bounded reads) |
| `POST /api/command` | Universal escape hatch: `{"command": "watchdog ..."}` or raw console input |

## 3. Suggested AI loop

1. `GET /api/status` + `GET /api/players` — is the server up, who is on.
2. `GET /api/events?since=<last>` — poll for joins, chat, crashes.
3. Act: `POST /api/say`, player admin, `POST /api/updates/apply`, `POST /api/server/restart?dry_run=1` first for anything destructive.
4. Mirror notable events to Discord via the bridge (`send-message`), and Discord commands back via `POST /api/command`.

## 4. Safety rules for agents

- Never expose `WEB_PANEL_TOKEN`, `WEB_PANEL_AI_TOKEN`, `DISCORD_BOT_TOKEN`, or bridge tokens in chat, logs, or commits. `.env` is gitignored for a reason.
- Prefer `dry_run` before start/stop/restart/kill and before `updates/apply`.
- `POST /api/command` is raw console: `op`, `ban`, and `watchdog stop` all work. Treat it like SSH root.
- Keep `MINECRAFT_EVENT_RECEIVER_TOKEN` and helper bridge tokens non-empty; empty tokens refuse events.
