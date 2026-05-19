param(
    [ValidateSet("status", "cleanup", "bootstrap", "start", "stop", "restart", "pull")]
    [string] $Action = "status",

    [string] $HostAlias = "deadadmin",
    [string] $RemoteRoot = "/home/deadadm1n",
    [string] $RepoUrl = "https://github.com/deadadm1n/BlackGrid.git",
    [string] $Branch = "main",
    [switch] $MigrateExisting
)

$ErrorActionPreference = "Stop"

function Invoke-Remote {
    param([Parameter(Mandatory = $true)][string] $Script)
    $Script | ssh -o BatchMode=yes $HostAlias "bash -s"
}

function New-RemoteScript {
    param([Parameter(Mandatory = $true)][string] $Body)

    @"
set -euo pipefail
REMOTE_ROOT='$RemoteRoot'
REPO_URL='$RepoUrl'
BRANCH='$Branch'
BLACKGRID_DIR="`$REMOTE_ROOT/BlackGrid"
WATCHDOG_LINK="`$REMOTE_ROOT/WatchDog"
REPO_WATCHDOG="`$BLACKGRID_DIR/WatchDog"

$Body
"@
}

switch ($Action) {
    "status" {
        Invoke-Remote (New-RemoteScript @'
echo "== Identity =="
hostname || true
whoami || true
id || true

echo
echo "== Tools =="
python3 --version 2>/dev/null || true
git --version 2>/dev/null || true
tmux -V 2>/dev/null || true

echo
echo "== Layout =="
for path in "$REMOTE_ROOT" "$BLACKGRID_DIR" "$WATCHDOG_LINK" "$REPO_WATCHDOG"; do
  if [ -e "$path" ] || [ -L "$path" ]; then
    ls -ld "$path"
  else
    echo "missing $path"
  fi
done

echo
echo "== Git =="
if [ -d "$BLACKGRID_DIR/.git" ]; then
  git -C "$BLACKGRID_DIR" status --short --branch
  git -C "$BLACKGRID_DIR" log --oneline -1
else
  echo "BlackGrid is not cloned yet."
fi

echo
echo "== WatchDog =="
if [ -d "$WATCHDOG_LINK" ] || [ -L "$WATCHDOG_LINK" ]; then
  find -L "$WATCHDOG_LINK" -maxdepth 2 \( -name ".env" -o -name "wrapper.yaml" -o -name "start.sh" -o -name "watchdog_helper*.jar" -o -name "aetherreachcore*.jar" \) -printf "%M %u:%g %s %p\n" 2>/dev/null | sort
fi

echo
echo "== tmux =="
tmux ls 2>/dev/null || echo "no tmux sessions"
'@)
    }

    "cleanup" {
        Invoke-Remote (New-RemoteScript @'
for p in "$REMOTE_ROOT/server.zip" "$WATCHDOG_LINK/server.zip"; do
  if [ -f "$p" ]; then
    rm -f "$p"
    echo "deleted $p"
  fi
done

if [ -d "$WATCHDOG_LINK" ] || [ -L "$WATCHDOG_LINK" ]; then
  find -L "$WATCHDOG_LINK" -path "*/.venv" -prune -o -type d -name __pycache__ -print -exec rm -rf {} + 2>/dev/null || true
  find -L "$WATCHDOG_LINK" -path "*/.venv" -prune -o -type f -name "*.pyc" -delete 2>/dev/null || true
fi

echo "cleanup complete"
'@)
    }

    "bootstrap" {
        $migrate = if ($MigrateExisting) { "1" } else { "0" }
        Invoke-Remote (New-RemoteScript @"
MIGRATE_EXISTING='$migrate'

if [ ! -d "`$BLACKGRID_DIR/.git" ]; then
  git clone --branch "`$BRANCH" "`$REPO_URL" "`$BLACKGRID_DIR"
else
  git -C "`$BLACKGRID_DIR" fetch origin "`$BRANCH"
  git -C "`$BLACKGRID_DIR" checkout "`$BRANCH"
  git -C "`$BLACKGRID_DIR" pull --ff-only origin "`$BRANCH"
fi

mkdir -p "`$REPO_WATCHDOG"

if [ "`$MIGRATE_EXISTING" = "1" ] && [ -d "`$WATCHDOG_LINK" ] && [ ! -L "`$WATCHDOG_LINK" ]; then
  stamp=`$(date -u +%Y%m%d-%H%M%S)
  backup="`$REMOTE_ROOT/WatchDog.pre-git.`$stamp"

  for name in atm11 .env logs state backups downloads tmp updates; do
    if [ -e "`$WATCHDOG_LINK/`$name" ] && [ ! -e "`$REPO_WATCHDOG/`$name" ]; then
      mv "`$WATCHDOG_LINK/`$name" "`$REPO_WATCHDOG/`$name"
      echo "moved runtime path: `$name"
    fi
  done

  mv "`$WATCHDOG_LINK" "`$backup"
  ln -s "`$REPO_WATCHDOG" "`$WATCHDOG_LINK"
  echo "migrated existing WatchDog to git layout"
  echo "old source backup: `$backup"
elif [ ! -e "`$WATCHDOG_LINK" ]; then
  ln -s "`$REPO_WATCHDOG" "`$WATCHDOG_LINK"
  echo "created WatchDog symlink"
else
  echo "WatchDog path already exists; use -MigrateExisting to convert it to the git layout"
fi

chmod +x "`$REPO_WATCHDOG/start.sh" 2>/dev/null || true
"@)
    }

    "pull" {
        Invoke-Remote (New-RemoteScript @'
if [ ! -d "$BLACKGRID_DIR/.git" ]; then
  echo "BlackGrid is not cloned yet. Run bootstrap first." >&2
  exit 1
fi
git -C "$BLACKGRID_DIR" pull --ff-only origin "$BRANCH"
chmod +x "$REPO_WATCHDOG/start.sh" 2>/dev/null || true
'@)
    }

    "start" {
        Invoke-Remote (New-RemoteScript @'
cd "$WATCHDOG_LINK"
chmod +x ./start.sh
./start.sh
'@)
    }

    "stop" {
        Invoke-Remote (New-RemoteScript @'
if tmux has-session -t watchdog 2>/dev/null; then
  tmux send-keys -t watchdog "wrapper stop" C-m
  echo "sent wrapper stop to tmux session watchdog"
else
  echo "watchdog tmux session is not running"
fi
'@)
    }

    "restart" {
        & $PSCommandPath -Action stop -HostAlias $HostAlias -RemoteRoot $RemoteRoot -RepoUrl $RepoUrl -Branch $Branch
        Start-Sleep -Seconds 5
        & $PSCommandPath -Action start -HostAlias $HostAlias -RemoteRoot $RemoteRoot -RepoUrl $RepoUrl -Branch $Branch
    }
}
