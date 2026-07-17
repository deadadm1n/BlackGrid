# Minecraft loader and addon model

BlackGrid needs to stop treating Minecraft as one giant bucket.

The menu shape should become:

```text
Minecraft
  Vanilla
  Fabric
  Quilt
  Forge
  NeoForge
  Paper
  Purpur
```

Then each loader can offer compatible server recipes, modpacks, helper mods, and optional BlackGrid addons.

```text
Game -> Loader -> Recipe -> Optional Addons -> WatchDog install
```

## Loader detection

When wrapping an existing Minecraft server, BlackGrid should detect the loader before offering addons.

Detection should be boring and evidence-based:

| Signal | Loader guess |
| --- | --- |
| `fabric-server-launch.jar`, `fabric-loader-*`, `fabric-installer*.jar` | Fabric |
| `quilt-server-launch.jar`, `quilt-loader-*`, `quilt-installer*.jar` | Quilt |
| `neoforge-*`, `libraries/net/neoforged/`, `mods.toml` with NeoForge metadata | NeoForge |
| `forge-*`, `libraries/net/minecraftforge/`, `mods.toml` with Forge metadata | Forge |
| `paper-*.jar`, `paperclip.jar`, `cache/patched_*.jar` | Paper |
| `purpur-*.jar` | Purpur |
| `server.jar` with no mod/plugin folders | Vanilla |

The detector should return:

```yaml
game: minecraft
loader: neoforge
minecraft_version: "1.21.1"
confidence: medium
evidence:
  - libraries/net/neoforged exists
  - mods folder exists
```

Low confidence should not block setup. It should ask the operator to confirm the loader instead of guessing like a cursed magic eight ball.

## Base recipe vs addons

A base server recipe should only install what is needed for that server to exist and start.

BlackGrid features are addons.

That means these are stripped from the base recipe by default:

```text
blackgrid.discord_bot
blackgrid.minecraft_helper
```

The operator can opt into them later during setup or after wrapping.

## Addon detection

BlackGrid should detect installed addons before offering to install them again.

Examples:

| Addon | Detection |
| --- | --- |
| Discord bot bridge | WatchDog config has `plugins.discord_bot.enabled=true` or token/channel configured |
| BlackGrid Minecraft helper | `mods/watchdog_helper-*.jar`, `mods/blackgrid_helper-*.jar`, or matching helper config exists |
| Web panel | WatchDog config has `web_panel.enabled=true` |
| Minecraft event bridge | WatchDog config has `bridges.minecraft_events.enabled=true` |

Addon status should be one of:

```text
missing
installed
enabled
disabled
incompatible
unknown
```

## Loader compatibility

Every addon should declare what it supports.

Example:

```yaml
id: blackgrid.minecraft_helper
name: BlackGrid Minecraft helper mod
supports:
  game: minecraft
  loaders:
    - neoforge
    - forge
    - fabric
install:
  type: curseforge_web_api_file
  project_id: 000000
  match:
    minecraft_version: "1.21.1"
    loader_priority:
      - NeoForge
      - Forge
      - Fabric
```

If the server is Vanilla, Paper, or Purpur, the helper mod should not be offered unless a compatible plugin/addon exists for that loader family.

## Setup flow

For a new Minecraft server:

```text
Pick Minecraft
Pick loader: Vanilla / Fabric / Forge / NeoForge / Paper / etc.
Pick recipe: ATM11 / Vanilla / Paper / custom CurseForge project / local folder
Resolve provider
Detect supported addons
Ask which optional BlackGrid addons to include
Generate WatchDog config
```

For wrapping an existing server:

```text
Point BlackGrid at the folder
Detect Minecraft loader/version
Show detected stack and confidence
Detect installed addons
Offer only compatible missing addons
Generate WatchDog config without mutating the server folder unless the operator selects an addon install
```

## Rule

Recipes describe the server.

Addons describe optional BlackGrid features.

Providers describe how files are fetched.

WatchDog describes how one server is run.

Do not mix those together or the project turns into soup with ports.
