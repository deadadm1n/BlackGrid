# BlackGrid

BlackGrid Gaming Community

This repository contains two related projects:

- `WatchDog/` - the Python wrapper, web panel, automation plugins, and Ubuntu start script.
- `WatchDogHelper/` - the NeoForge Java helper mod installed into the Minecraft server. It provides the Minecraft-side bridge, economy, commands, MOTD/rules, and placement protections.

Runtime files are intentionally not tracked. The live ATM11 server folder, logs, backups, virtual environments, generated jars, and `.env` secrets stay local.

For a fresh WatchDog install, copy `WatchDog/.env.example` to `WatchDog/.env` and fill in the local tokens.

Clean public config templates also live in `configs/`.

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

## ATM11 ServerFiles Updates

WatchDog can update the ATM11 server pack from the checked-in manifest at:

```text
configs/atm11-serverfiles.json
```

When that manifest points at a newer ServerFiles `file_id`, the live wrapper downloads it automatically and queues it for the next scheduled restart. The update backs up the server first, preserves the configured local folders and custom jars, validates startup, and rolls back if validation fails.

## Discord Linking

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
