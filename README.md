# BlackGrid

BlackGrid Gaming Community

This repository contains two related projects:

- `WatchDog/` - the Python wrapper, web panel, automation plugins, and Ubuntu start script.
- `AetherReach/` - the NeoForge Java mod that provides the Minecraft-side bridge, economy, commands, MOTD/rules, and placement protections.

Runtime files are intentionally not tracked. The live ATM11 server folder, logs, backups, virtual environments, generated jars, and `.env` secrets stay local.

For a fresh WatchDog install, copy `WatchDog/.env.example` to `WatchDog/.env` and fill in the local tokens.

## Releasing AetherReach

AetherReach jars are built by GitHub Actions and attached to GitHub Releases. To publish a new jar release from a clean working tree:

```powershell
.\scripts\release-aetherreach.ps1 -Version 1.0.0
```

If PowerShell blocks local scripts on your PC, use the batch launcher instead:

```powershell
.\scripts\release-aetherreach.bat -Version 1.0.0
```

The batch launcher also accepts the version as the first argument:

```powershell
.\scripts\release-aetherreach.bat 1.0
```

The release helper builds the mod locally, creates a tag like `aetherreach-v1.0.0`, and pushes the tag. GitHub then builds the jar on Ubuntu and uploads it as a release asset.
