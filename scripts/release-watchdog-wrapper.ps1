param(
    [Parameter(Mandatory = $true)]
    [string] $Version
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "release-lib.ps1")

$Version = Normalize-ReleaseVersion $Version
$repoRoot = Resolve-RepoRoot $PSScriptRoot
Set-Location $repoRoot

Assert-TrackedTreeClean
Assert-UniqueTag "watchdog-v$Version"

git tag -a "watchdog-v$Version" -m "WatchDog Wrapper v$Version"
git push origin "watchdog-v$Version"

Write-Host "Pushed watchdog-v$Version. GitHub Actions will package and attach the wrapper zip."
