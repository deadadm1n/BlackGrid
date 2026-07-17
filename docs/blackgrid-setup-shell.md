# BlackGrid setup shell

BlackGrid is now allowed to be a standalone setup tool instead of a forever-running control daemon.

The shape is:

```text
BlackGrid Shell = creates or wraps a server
WatchDog = runs one created/wrapped server
Server folder = the actual game server files
```

After BlackGrid creates a server, that server should be able to run with its own detached WatchDog install. BlackGrid can be closed, deleted, ignored, or used later to build another server.

## First supported flow

The first supported flow is intentionally boring:

```text
Run blackgrid.bat or ./blackgrid.sh
Pick: Create new Minecraft / ATM11 server
Choose target folder
Download ATM11 ServerFiles from the checked-in manifest
Extract server files
Generate a detached WatchDog install
Start later with start-watchdog.bat or start-watchdog.sh
```

There is also a safer migration flow for live servers:

```text
Run blackgrid.bat or ./blackgrid.sh
Pick: Wrap existing Minecraft / ATM11 server
Point at the existing server folder
Choose a separate WatchDog install folder
Generate WatchDog around the existing server without moving it
```

That wrap mode is what should be used first for AetherReach or any live server. Do not make the first test be the only live folder unless downtime demons sound fun that day.

## Detached output

A generated server should look roughly like this:

```text
AetherReach/
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
