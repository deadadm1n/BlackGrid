# BlackGrid provider system

BlackGrid should not know how every game downloads.

BlackGrid should know how to load a recipe, pick the provider named by that recipe, and ask that provider to resolve and install files.

```text
Recipe = what the operator wants
Provider = how files are resolved/downloaded/installed
WatchDog = how one installed server is run
```

## First provider: CurseForge web API ServerFiles

ATM11 already proves the first provider shape without needing a CurseForge Core API key.

The current working path uses CurseForge web API-style endpoints:

```text
GET https://www.curseforge.com/api/v1/mods/{project_id}/files
GET https://www.curseforge.com/api/v1/mods/{project_id}/files/{file_id}/additional-files
GET https://www.curseforge.com/api/v1/mods/{project_id}/files/{file_id}/download
```

That provider is for modpacks where the normal pack file has an attached ServerFiles/additional file.

The provider should:

1. list recent files for the CurseForge project
2. prefer stable/non-alpha files when configured
3. inspect additional files attached to the pack file
4. find a ServerFiles entry
5. return file id, display name, file name, page URL, changelog URL, and download URL
6. download through CurseForge's official download endpoint
7. fall back to a static manifest when the endpoint breaks

## Static manifest fallback

Every network provider should have a boring fallback when possible.

For ATM11, the fallback is:

```text
configs/atm11-serverfiles.json
```

That file pins the known-good ServerFiles download so BlackGrid can still install the current supported version even if the provider lookup fails.

Provider failure should not mean the whole project is dead. It should mean BlackGrid drops to the next configured source and tells the operator what happened.

## Provider result shape

Providers should eventually return a common object:

```yaml
file_id: 1234567
display_name: "ServerFiles-1.21.1-1.0.0"
file_name: "ServerFiles-1.21.1-1.0.0.zip"
page_url: "https://www.curseforge.com/..."
download_url: "https://www.curseforge.com/api/v1/.../download"
changelog_url: "https://www.curseforge.com/.../changelog"
source: curseforge_web_api_serverfiles
```

BlackGrid does not care whether that result came from CurseForge, SteamCMD, a manual ZIP, or a local folder. The provider owns the cursed details.

## Provider types to support

### `static_manifest`

Reads a local JSON/YAML manifest with a known file id and download URL.

Good for the first stable version of a recipe.

### `curseforge_web_api_serverfiles`

Uses CurseForge web API-style endpoints to find a modpack's attached ServerFiles package.

Good for ATM-style packs.

### `curseforge_web_api_file`

Uses CurseForge web API-style endpoints to find a normal project file by Minecraft version and loader priority.

Good for individual mods or helper dependencies.

Example matching behavior:

```text
try NeoForge for Minecraft version
if none, try Forge for Minecraft version
newest matching file wins
```

### `steamcmd`

Uses SteamCMD to install or update a dedicated server by app id.

Good for Valheim, Palworld, Source servers, and other Steam dedicated servers.

### `manual_url`

Downloads a configured ZIP/TAR URL.

Good for weird games, private builds, and quick testing.

### `local_folder`

Wraps an existing folder without downloading anything.

Good for live migrations and anything BlackGrid should not touch.

## Rule

Provider code can be game/source-specific.

WatchDog core should stay boring:

```text
start script
stop command
ports
logs
state
backups
health checks
```

That keeps a broken CurseForge resolver from infecting Valheim, and keeps a SteamCMD goblin from touching Minecraft.
