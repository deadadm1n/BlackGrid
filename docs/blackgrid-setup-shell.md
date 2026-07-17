# BlackGrid setup shell

BlackGrid is now allowed to be a standalone setup tool instead of a forever-running control daemon.

The shape is:

```text
BlackGrid Shell = creates or wraps a server
WatchDog = runs one created/wrapped server
Server folder = the actual game server files
```

After BlackGrid creates a server, that server should be able to run with its own detached WatchDog install. BlackGrid can be closed, deleted, ignored, or used later to build another server.

## Server identity

Every generated server needs a user-selected identity.

BlackGrid should not hardcode `AetherReach` into generated installs. AetherReach is one server/community that can run on BlackGrid, not the name of every server BlackGrid creates.

During create or wrap setup, BlackGrid asks for a server name/folder name. That value becomes the generated server identity and should be reused anywhere the old developed server code would have said AetherReach.

```text
Server name entered by operator: Sky Goblin SMP
Folder/id form: sky-goblin-smp
Display form: Sky Goblin SMP
```

Generated output should use that identity for:

- detached install folder names
- tmux/session naming
- WatchDog Discord bot `server_name`
- website/status `server_name`
- helper/mod display names where the base helper needs a public server name
- server-specific data folders that used to be named `aetherreach`
- preserve/update paths for server-specific addon data

The rule is simple:

```text
AetherReach = example/live server name
server_identity = whatever the operator picked during install
```

AetherReach-specific economy/shop/protection behavior should stay in an AetherReach addon/profile, not the base WatchDog Helper.

## System checks

There are two different checks on purpose:

```text
blackgrid_system_check.py = checks whether BlackGrid itself can start
WatchDog/server_system_check.py = checks whether one selected server can start
```

The BlackGrid startup check runs before the setup shell opens from `blackgrid.bat` or `blackgrid.sh`. It checks the stuff BlackGrid needs before WatchDog gets to do its selected-server check:

- Git
- Python 3.10+
- tmux
- Half a brain cell.

`Half a brain cell.` is a deliberate troll check. It only appears when the real startup requirements passed. If Git, Python, or tmux are actually missing, BlackGrid shows the real failure instead and stops.

When only the troll check fails, BlackGrid asks whether to continue. `yes` keeps going into the setup shell. `no` closes out so everyone can sit there and laugh in silence.

Do not put Minecraft, Java, ATM11, Discord, port, manifest, or game-specific checks in the BlackGrid startup check. Those belong later, after the user picks what they are creating or wrapping.

The WatchDog server check runs right before WatchDog starts a server. It checks the selected generated config and that one server only:

- config file exists and parses as YAML
- server directory exists
- logs/state/backups/downloads/tmp paths are writable
- start script exists or can be auto-detected
- Java exists and meets the configured major version
- enabled ports are valid and do not collide
- enabled ports are not already bound/listening
- exposed web panel is not enabled without a token
- enabled Discord bot has minimum token/channel config

This keeps BlackGrid startup from turning into a giant audit of games the user is not even trying to run.

## First supported flow

The first supported flow is intentionally boring:

```text
Run blackgrid.bat or ./blackgrid.sh
Run BlackGrid system check
Pick: Create new Minecraft / ATM11 server
Choose server name / identity
Choose target folder
Run preflight checks
Download ATM11 ServerFiles from the checked-in manifest
Extract server files
Generate a detached WatchDog install
Start later with start-watchdog.bat or start-watchdog.sh
```

There is also a safer migration flow for live servers:

```text
Run blackgrid.bat or ./blackgrid.sh
Run BlackGrid system check
Pick: Wrap existing Minecraft / ATM11 server
Point at the existing server folder
Choose server name / identity
Choose a separate WatchDog install folder
Run preflight checks
Generate WatchDog around the existing server without moving it
```

That wrap mode is what should be used first for a live server. Do not make the first test be the only live folder unless downtime demons sound fun that day.

## Preflight checks

BlackGrid runs preflight before generating anything.

Checks use four levels:

```text
OK = good
INFO = useful note
WARN = continue allowed, but pay attention
FAIL = do not continue
```

A wrap can be safe to generate while still being unsafe to start. That is expected when the live server is already running.

The first preflight pass checks:

- install target is not the repo root, filesystem root, or source `WatchDog/` folder
- WatchDog install folder is separate from the live server folder
- checked-in ATM11 manifest has `file_id`, `display_name`, and `download_url`
- `server.properties` can be read when wrapping an existing server
- Minecraft `server-port`, query port, and RCON port do not collide with each other
- enabled ports are already bound/listening on the host
- a Java/server process appears to be using the existing server folder
- `session.lock` exists at the server root or world root
- `eula.txt` is present and accepted
- a usable start script exists
- the folder looks like Minecraft/ATM11 enough to be worth wrapping

For wrap mode, ATM11 auto-update is generated disabled by default. The point is to let WatchDog run or observe the server first, then turn mutation-heavy behavior on later once the wrapper is trusted.

## Detached output

A generated server should look roughly like this:

```text
<server-identity>/
  server/              # game server files for new installs
  watchdog/            # copied WatchDog wrapper for this one server
  logs/
  state/
  backups/
  downloads/
  manifests/
  updates/
  start-watchdog.bat
  start-watchdog.sh
```

For wrap mode, the `server/` folder may live somewhere else. The generated WatchDog config points directly at the existing folder.

## Reattaching to WatchDog

BlackGrid can detach after setup, but the operator still needs a way back into the WatchDog terminal.

On Linux, WatchDog uses `tmux`:

```bash
./start-watchdog.sh
```

That enters a tmux session named from the install folder, such as `blackgrid-sky-goblin-smp`. Detach safely with:

```text
Ctrl-b then d
```

Reconnect from the detached install with:

```bash
cd watchdog
./attach.sh
```

Stop the wrapper politely with:

```bash
cd watchdog
./stop.sh
```

The root generated `start-watchdog.sh` still works as the easy start path. The helper scripts inside `watchdog/` are the terminal re-entry path.

On Windows, batch files cannot reattach to a console that was closed. The copied WatchDog install includes:

```text
watchdog\attach.bat
watchdog\logs.bat
```

`attach.bat` explains the limitation. `logs.bat` tails `logs\wrapper.log` through PowerShell so the operator can still see what WatchDog is doing. For real detach/reattach behavior, use Linux/WSL with tmux.

## Boundary rule

BlackGrid creates servers.

WatchDog runs one server.

The generated server should not depend on BlackGrid being open in another terminal. That keeps server ownership simple and keeps one broken server from poisoning the whole host.

## Next expansion

Do not build the full multi-game monster until the first path works.

Good next additions:

1. Minecraft vanilla recipe.
2. Paper recipe.
3. Existing generic server folder wrapper.
4. Source/CS-style recipe with RCON/SteamCMD plugin support.
5. A real recipe loader once more than ATM11 exists.

Until then, hardcoded ATM11 in `blackgrid.py` is acceptable because it proves the provisioning shape without pretending the entire hosting platform is finished.
