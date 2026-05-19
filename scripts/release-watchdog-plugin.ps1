param(
    [Parameter(Mandatory = $true)]
    [string] $Plugin,

    [Parameter(Mandatory = $true)]
    [string] $Version
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "release-lib.ps1")

$Plugin = $Plugin.Trim()
if ($Plugin -notmatch '^[A-Za-z0-9_-]+$') {
    Write-Error "Plugin name must contain only letters, numbers, underscores, or dashes."
}

$Version = Normalize-ReleaseVersion $Version
$repoRoot = Resolve-RepoRoot $PSScriptRoot
Set-Location $repoRoot

$pluginDir = Join-Path $repoRoot "WatchDog\plugins\$Plugin"
if (-not (Test-Path -LiteralPath $pluginDir -PathType Container)) {
    Write-Error "Plugin folder does not exist: $pluginDir"
}

Assert-TrackedTreeClean
Assert-UniqueTag "watchdog-plugin-$Plugin-v$Version"

git tag -a "watchdog-plugin-$Plugin-v$Version" -m "WatchDog Plugin $Plugin v$Version"
git push origin "watchdog-plugin-$Plugin-v$Version"

Write-Host "Pushed watchdog-plugin-$Plugin-v$Version. GitHub Actions will package and attach the plugin zip."
