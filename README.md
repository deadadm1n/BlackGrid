# BlackGrid

BlackGrid is a gaming community and server-hosting lab for people who want to play, learn, experiment, and eventually try running servers without already being a sysadmin goblin.

Right now the public face is simple: BlackGrid is a gaming community that can grow into more than one server. Behind the scenes, the direction is bigger:

- **BlackGrid** is the umbrella community, hosting/lab idea, and long-term brand.
- **WatchDog** is the server wrapper and control layer that should eventually manage more than one kind of game server.
- **AetherReach** is the first Minecraft server/community running under BlackGrid.
- **WatchDog Helper** is the Minecraft-side helper mod used by AetherReach and future Minecraft servers that need in-game bridge features.

Minecraft is where this started. It should not be where the idea gets stuck.

## Repo layout

This repository currently contains the infrastructure for the first BlackGrid stack:

- `WatchDog/` - Python server wrapper, web panel, automation plugins, update tools, and start scripts.
- `WatchDogHelper/` - NeoForge Java helper mod for Minecraft servers. It provides the Minecraft-side bridge, economy/commands, MOTD/rules, and placement protections.
- `configs/` - clean public config templates and manifests.
- `scripts/` - release helpers and remote WatchDog automation.

Runtime files are intentionally not tracked. The live AetherReach/ATM11 server folder, logs, backups, virtual environments, generated jars, and `.env` secrets stay local.

For a fresh WatchDog install, copy `WatchDog/.env.example` to `WatchDog/.env` and fill in the local tokens.

## Current direction

BlackGrid is being repositioned from “one Minecraft server project” into a broader gaming community and learning-focused server host.

The near-term path is:

1. Keep AetherReach stable as the first Minecraft server.
2. Keep WatchDog working as the wrapper/control plane.
3. Start separating generic server-wrapper behavior from Minecraft/ATM11-specific behavior.
4. Add cleaner docs and profiles so other server types can exist later.
5. Grow BlackGrid’s appearance into the community/server-lab brand instead of making everything look like it only belongs to ATM11.

Long term, WatchDog should be able to run profiles for different game servers, such as Minecraft, CS/Source-style servers, and other dedicated servers that need start/stop/restart/log/update/status handling.

## Design rule

BlackGrid is the platform.

WatchDog is the wrapper.

AetherReach is a server.

Minecraft-specific code belongs in Minecraft-specific plugins, configs, docs, or helper mods. WatchDog core should stay as reusable as possible.

## Releasing WatchDog Helper

WatchDog Helper jars are built by GitHub Actions and attached to GitHub Releases. To publish a new jar release from a clean working tree:

```powershell
.\scripts\release-watchdog-helper.ps1 -Version 1.0.0
```

If PowerShell blocks local scripts on your PC, use the batch launcher instead:

```powershell
.\scripts\release-watchdog-helper.bat -Version 1.0.0
```

The batch launcher also accepts the version as the first argument:

```powershell
.\scripts\release-watchdog-helper.bat 1.0
```

The release helper builds the mod locally, creates a tag like `watchdog-helper-v1.0.0`, and pushes the tag. GitHub then builds the jar on Ubuntu and uploads it as a release asset.

## Releasing WatchDog

WatchDog wrapper and WatchDog Helper releases are published from tags:

```powershell
.\scripts\release-watchdog-wrapper.bat 0.1.0
.\scripts\release-watchdog-helper.bat 0.1.0
```

Inside the wrapper console, one command checks, downloads, and applies WatchDog plus the WatchDog Helper jar:

```text
wrapper update
```

You can also inspect or split the steps:

```text
wrapper update status
wrapper update check
wrapper update download
wrapper update apply
```

Wrapper updates preserve local config, `.env`, logs, state, backups, downloads, `atm11`, and update staging folders. WatchDog Helper jar updates replace the helper jar in `atm11/mods` and back up the previous jar first.

## AetherReach / ATM11 ServerFiles updates

AetherReach currently runs on ATM11, so WatchDog can update the server pack from the checked-in manifest at:

```text
configs/atm11-serverfiles.json
```

When that manifest points at a newer ServerFiles `file_id`, the live wrapper downloads it automatically and queues it for the next scheduled restart. The update backs up the server first, preserves the configured local folders and custom jars, validates startup, and rolls back if validation fails.

The manifest is refreshed by the scheduled GitHub Actions workflow in `.github/workflows/atm11-serverfiles-manifest.yml`. You can also run the scraper manually:

```text
python scripts/update-atm11-serverfiles-manifest.py
```

## Discord linking

WatchDog Helper exposes `/discord` in Minecraft. The player runs it in-game, then clicks the generated Discord OAuth link.

The old `/discordlink` and `/linkdiscord` commands are kept as compatibility aliases. Discord admins can run:

```text
!ranks setup
!ranks list
!ranks sync
```

The bot needs Discord `Manage Roles`, and its bot role must be above the roles it manages. Server Members Intent must be enabled for the bot.

## Remote WatchDog

SSH automation for the Ubuntu host lives in `scripts/remote-watchdog.bat`:

```powershell
.\scripts\remote-watchdog.bat -Action status
.\scripts\remote-watchdog.bat -Action cleanup
.\scripts\remote-watchdog.bat -Action bootstrap -MigrateExisting
.\scripts\remote-watchdog.bat -Action pull
.\scripts\remote-watchdog.bat -Action start
.\scripts\remote-watchdog.bat -Action stop
```

`bootstrap -MigrateExisting` preserves live runtime paths such as `atm11`, `.env`, logs, state, backups, downloads, tmp, and updates, then points the remote `WatchDog` path at the Git checkout.
