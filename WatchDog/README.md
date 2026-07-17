# WatchDog

WatchDog is BlackGrid's server wrapper and control plane.

It started with AetherReach, the BlackGrid Minecraft/ATM11 server, but the long-term goal is bigger than one Minecraft instance. WatchDog should become the thing BlackGrid uses to start, stop, monitor, update, back up, and expose control/status for different kinds of game servers.

Minecraft is the first target. It is not supposed to be the only target forever.

## What works now

- Loads `config/wrapper.yaml`, or another config passed with `--config`
- Loads enabled plugins from `plugins/*`
- Starts a configured server directory/start script on Windows or Linux
- Watches console output for startup success/failure patterns
- Logs to `logs/wrapper.log`
- Supports plugin-owned commands and hot reloads
- Exposes a small web panel for status, terminal output, commands, plugin reloads, and restarts
- Has a Minecraft/AetherReach bridge path through WatchDog Helper
- Has ATM11 ServerFiles update automation with backup, staged install, startup validation, and rollback
- Discord and auto-restart plugins are included as working lifecycle pieces
- Fake test server support exists so the wrapper can run without the live server folder

## Current server target

The default config still points at AetherReach's local ATM11 folder:

```yaml
server:
  directory: "atm11"
  start_script: "auto"
  java_executable: "auto"
  required_java_major: 25
```

That is the current production use case, not the final boundary of WatchDog.

## The direction

WatchDog core should stay generic wherever it reasonably can:

- process start/stop/restart
- process tree cleanup
- stdout/stderr capture
- startup validation
- command registry
- plugin loading/reloading
- event bus
- web control panel
- config and runtime paths
- update hooks
- status publishing

Game-specific behavior should live in plugins, profiles, helpers, or config:

- Minecraft console parsing
- ATM11 ServerFiles updates
- WatchDog Helper bridge calls
- Discord rank linking for Minecraft players
- ops/whitelist behavior
- future CS/Source/RCON logic
- future SteamCMD or game-specific update steps

## Test run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Default config points to the local `atm11` folder and uses `start_script: "auto"`.
On Windows it prefers `startserver.bat`/`run.bat`; on Linux it prefers `startserver.sh`/`run.sh`.

To run a generated or alternate config:

```bash
python main.py --config config/wrapper.yaml
```

```powershell
python main.py --config config\wrapper.yaml
```

## Real AetherReach / ATM11 setup

Edit `config/wrapper.yaml`:

```yaml
server:
  directory: "atm11"
  start_script: "auto"
  java_executable: "auto"
  required_java_major: 25
```

Then configure the ATM11 auto-update plugin and any Discord/bridge tokens needed for the live server.

## Secrets

Runtime secrets live in `.env`, not `config/wrapper.yaml`.

For a new install:

```bash
cp .env.example .env
nano .env
```

Set the Discord bot token and bridge tokens there. Keep `.env` private.

For a different install location, set `server.directory` to either an absolute path or a path relative to the wrapper folder. The same applies to log, backup, download, temporary, and plugin paths in `config/wrapper.yaml`.

## Java selection

AetherReach/ATM11 currently needs Java 25. WatchDog itself does not hardcode a Java path. It checks, in order:

1. `server.java_executable` when set to a path instead of `auto`
2. `ATM11_JAVA`
3. `JAVA_HOME/bin/java`
4. `java` from `PATH`

On Windows PowerShell, for a one-session override:

```powershell
$env:ATM11_JAVA = "C:\Program Files\Eclipse Adoptium\jdk-25...\bin\java.exe"
python main.py
```

On Linux:

```bash
export ATM11_JAVA=/path/to/jdk-25/bin/java
python main.py
```

## Design rule

The server folder belongs to the game/modpack.

WatchDog owns control, monitoring, patches, updates, and recovery.

Do not let ATM11-specific behavior leak into WatchDog core unless there is no cleaner place for it yet.

## Plugin hotloader commands

These commands run inside the WatchDog wrapper console after startup:

```text
wrapper plugins
wrapper reload-plugin discord_bot
wrapper reload-plugin auto_restart
wrapper reload-plugins
wrapper reload
wrapper stop
```

Notes:

- `wrapper reload-plugin <name>` reloads one plugin without restarting the running game server.
- `wrapper reload-plugins` reloads every currently loaded plugin without restarting the running game server.
- Event subscriptions are owner-tracked and removed during reload so events do not duplicate.
- `on_plugin_unload(ctx)` is called before a plugin is unloaded. By default it calls `on_wrapper_stop(ctx)`.
