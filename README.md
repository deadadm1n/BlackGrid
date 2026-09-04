# BlackGrid

BlackGrid is a gaming community and server-hosting lab. Play, learn, experiment, and run game servers without already being a sysadmin.

- **BlackGrid** — the community, brand, and hosting-lab idea.
- **WatchDog** — the server wrapper and control plane. Starts, stops, monitors, updates, backs up, and exposes control/status for game servers. Minecraft first, generic core by design.
- **AetherReach** — the first Minecraft (ATM11) server running under BlackGrid.
- **WatchDog Helper** — the Minecraft-side NeoForge mod (bridge, economy, commands, protections).
- **discord-bot** — the Discord admin bridge. Gives an AI (or operator script) full server-admin control over Discord through a local HTTP API.

## Repo layout

- `blackgrid.py` + `blackgrid.bat` / `blackgrid.sh` — standalone setup shell for creating or wrapping server installs.
- `WatchDog/` — Python wrapper, web panel, plugins, update tools, start scripts.
- `WatchDogHelper/` — NeoForge Java helper mod.
- `discord-bot/` — Node.js Discord admin bridge (`index.js`, HTTP control on `:3000`).
- `configs/` — public config templates and manifests.
- `recipes/` — provisioning recipes for BlackGrid-created servers.
- `scripts/` — release helpers and remote WatchDog automation.
- `docs/` — design docs, including `docs/ai-control.md` (machine + human control surfaces).
- `branding/` `website/` — brand assets and site.

Runtime files are never tracked: live server folders, logs, backups, venvs, jars, `node_modules/`, `.env` secrets.

## Quickstart

**WatchDog:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in tokens
python main.py
```

Windows PowerShell: `.venv\Scripts\Activate.ps1` instead of `source`.

**Discord bridge:**

```bash
cd discord-bot
npm install
DISCORD_BOT_TOKEN=... node index.js
```

Invite with Administrator (`permissions=8`), Server Members Intent + Message Content Intent enabled.

## AI control surfaces

Full detail: `docs/ai-control.md`.

**Discord bridge** (`http://HOST:3000/discord-command`, `POST` JSON):

| `type` | Does |
|---|---|
| `send-message` | Post to a channel |
| `get-messages` | Read channel history |
| `list-channels` / `list-members` / `list-roles` / `guild-info` | Inspect server |
| `create-role` / `delete-role` / `update-role` | Manage roles (Admin perms supported) |
| `assign-role` / `remove-role` | Manage membership |
| `create-channel` / `delete-channel` / `delete-message` | Manage channels |
| `kick` / `ban` / `unban` / `timeout` | Moderate |
| Health: `GET /`, OAuth landing: `GET /auth/callback` | Status + invite flow |

**WatchDog panel** (set `WEB_PANEL_AI_TOKEN`, send as `X-AI-Token` header; every call audit-logged):

- Lifecycle: `POST /api/server/start|stop|kill`, `POST /api/restart` (all accept `?dry_run=1`)
- Players: `POST /api/say`, `/api/players/kick|ban|unban|op|deop`, `/api/players/whitelist`, `GET /api/players`
- Ops: `GET /api/plugins`, `POST /api/plugins/reload`, `GET /api/updates/status`, `POST /api/updates/check|download|apply|clear`, `GET /api/backups`, `GET /api/metrics`, `GET /api/events?since=`
- Universal escape hatch: `POST /api/command` runs any `watchdog …` command or raw console input

## Environment

| Variable | Used by | Purpose |
|---|---|---|
| `DISCORD_BOT_TOKEN` | discord-bot, WatchDog discord plugin | Bot login |
| `WEB_PANEL_TOKEN` | WatchDog | Human panel auth |
| `WEB_PANEL_AI_TOKEN` | WatchDog | AI key (`X-AI-Token`), full scope, audited |
| `MINECRAFT_EVENT_RECEIVER_TOKEN` | WatchDog + Helper | Helper→wrapper event auth (must be non-empty) |
| `AETHERREACH_BRIDGE_TOKEN` | WatchDog + Helper | Wrapper→helper auth |
| `ATM11_JAVA` / `JAVA_HOME` | WatchDog | Java 25 selection for ATM11 |
| `ATM11_MANIFEST_URL` | WatchDog | Update manifest override |

Copy `WatchDog/.env.example` to `WatchDog/.env`. Never commit `.env`.

## Design rule

BlackGrid is the platform. WatchDog is the wrapper. AetherReach is a server.

Minecraft-specific code belongs in Minecraft-specific plugins, configs, docs, or helper mods. WatchDog core stays reusable.

## Setup shell

```powershell
.\blackgrid.bat
```

```bash
bash blackgrid.sh
```

Two flows: create a new Minecraft/ATM11 server from the ServerFiles manifest, or wrap an existing one without moving it. Output is a detached server folder WatchDog owns. See `docs/blackgrid-setup-shell.md`.

## Releases

Helper jars build on GitHub Actions from tags:

```powershell
.\scripts\release-watchdog-helper.bat 0.1.0
.\scripts\release-watchdog-wrapper.bat 0.1.0
```

In the wrapper console, `wrapper update status|check|download|apply` manages wrapper + helper updates. ATM11 packs update from `configs/atm11-serverfiles.json` (refreshed by `.github/workflows/atm11-serverfiles-manifest.yml`, or `python scripts/update-atm11-serverfiles-manifest.py`).

## Discord linking

Helper exposes `/discord` in-game; players link via OAuth. Admins: `!ranks setup|list|sync`. The bot needs Manage Roles above managed roles, plus Server Members Intent. Bridge details: `docs/watchdog-discord-chat-bridge.md`.

## Remote WatchDog

```powershell
.\scripts\remote-watchdog.bat -Action status
.\scripts\remote-watchdog.bat -Action pull
.\scripts\remote-watchdog.bat -Action start
.\scripts\remote-watchdog.bat -Action stop
```

`bootstrap -MigrateExisting` preserves live paths (`atm11`, `.env`, logs, state, backups, downloads, tmp, updates) and points the remote path at the Git checkout.
