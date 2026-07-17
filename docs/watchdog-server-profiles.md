# WatchDog server profiles

WatchDog currently starts AetherReach/ATM11 through `config/wrapper.yaml`.

The long-term direction is to make WatchDog profile-driven so BlackGrid can run more than one kind of game server without turning core code into Minecraft soup.

## Profile idea

A future server profile should describe the boring parts WatchDog needs to know:

```yaml
id: aetherreach-atm11
name: AetherReach
kind: minecraft
server:
  directory: atm11
  start_script: auto
  stop_command: stop
  required_java_major: 25
startup:
  success_patterns:
    - 'For help, type "help"'
  failure_patterns:
    - 'Crash report saved'
    - 'session.lock: already locked'
plugins:
  minecraft_events: true
  atm11_auto_update: true
  discord_bot: true
  website_status: true
```

For another server type, the profile should change the adapter/plugins, not force the core wrapper to learn a new game's entire personality disorder.

Example future Source/CS-style shape:

```yaml
id: source-test-server
name: Source Test Server
kind: source
server:
  directory: servers/source-test
  start_script: start.sh
  stop_command: quit
startup:
  success_patterns:
    - 'VAC secure mode is activated'
plugins:
  source_rcon: true
  steamcmd_update: true
  website_status: true
```

## Boundary rule

WatchDog core should handle:

- running a process
- stopping/restarting it
- reading logs
- matching generic startup/failure patterns
- keeping runtime paths organized
- loading plugins
- exposing a web panel
- publishing status

Game-specific plugins should handle:

- Minecraft helper bridge
- Minecraft chat/player events
- ATM11 ServerFiles updates
- Discord rank sync based on Minecraft players
- future RCON behavior
- future SteamCMD behavior
- game-specific backups/update rules

## Why this matters

BlackGrid wants to become more than AetherReach.

AetherReach can stay the first real server, but WatchDog should not be trapped as “the ATM11 wrapper forever.” The profile direction gives the project a path toward multiple servers without pretending that all games work the same way.

## Near-term plan

Do not build the full profile engine yet unless it is needed.

First pass:

1. Keep `config/wrapper.yaml` as the live config.
2. Add docs and example profile files.
3. Rename comments/docs so they say AetherReach/ATM11 only where that is actually the current server.
4. Slowly isolate Minecraft-only logic into Minecraft plugins/helpers.
5. Later, add a real `profiles/` loader once there is a second server type worth supporting.
