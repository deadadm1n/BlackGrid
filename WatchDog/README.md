# ATM11 Wrapper v3 - Watchdog

Plugin-driven Python wrapper for an All the Mods 11 server.

## What works

- Loads `config/wrapper.yaml`
- Loads enabled plugins from `plugins/*`
- Starts Minecraft with configured server directory/start script on Windows or Linux
- Watches console output for startup success/failure patterns
- Logs to `logs/wrapper.log`
- Auto-update is a plugin
- Auto-update can backup, download, extract, patch, mark pending, commit, or roll back
- Patch types: `properties`, `replace_file`, `replace_text_file`, `text_replace`
- Discord and auto-restart plugins are included as working lifecycle stubs
- Fake test server included so the wrapper runs immediately

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

## Real ATM11 setup

Edit `config/wrapper.yaml`:

```yaml
server:
  directory: "atm11"
  start_script: "auto"
  java_executable: "auto"
  required_java_major: 25
```

Then configure the auto-update plugin.

## Secrets

Runtime secrets live in `.env`, not `config/wrapper.yaml`.

For a new install:

```bash
cp .env.example .env
nano .env
```

Set the Discord bot token and bridge tokens there. Keep `.env` private.

For a different install location, set `server.directory` to either an absolute path or
a path relative to the wrapper folder. The same applies to log, backup, download,
temporary, and plugin paths in `config/wrapper.yaml`.

## Java selection

ATM11 currently needs Java 25. The wrapper does not hardcode a Java path. It checks,
in order:

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

The modpack owns the server folder. The wrapper owns your patches.

## Plugin hotloader commands

These commands run inside the Watchdog wrapper console after startup:

```text
wrapper plugins
wrapper reload-plugin discord_bot
wrapper reload-plugin auto_restart
wrapper reload-plugins
wrapper reload
wrapper stop
```

Notes:
- `wrapper reload-plugin <name>` reloads one plugin without restarting ATM11.
- `wrapper reload-plugins` reloads every currently loaded plugin without restarting ATM11.
- Event subscriptions are owner-tracked and removed during reload so events do not duplicate.
- `on_plugin_unload(ctx)` is called before a plugin is unloaded. By default it calls `on_wrapper_stop(ctx)`.
