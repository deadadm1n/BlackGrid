param(
    [Parameter(Mandatory = $true)]
    [string] $Version
)

$ErrorActionPreference = "Stop"

$Version = $Version.Trim()
if ($Version -match '^(\d+\.\d+)(-[A-Za-z0-9][A-Za-z0-9.-]*)?$') {
    $Version = "$($Matches[1]).0$($Matches[2])"
}

if ($Version -notmatch '^\d+\.\d+\.\d+(-[A-Za-z0-9][A-Za-z0-9.-]*)?$') {
    Write-Error "Version must look like 1.0.0, 1.0, or 1.0.0-beta."
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$status = git status --porcelain --untracked-files=no
if ($status) {
    Write-Error "Tracked Git files are not clean. Commit or stash tracked changes before creating a release tag."
}

$tag = "aetherreach-v$Version"
$existingTag = git tag --list $tag
if ($existingTag) {
    Write-Error "Tag already exists locally: $tag"
}

git fetch origin --tags
$remoteTag = git ls-remote --tags origin "refs/tags/$tag"
if ($remoteTag) {
    Write-Error "Tag already exists on origin: $tag"
}

Write-Host "Building AetherReach before tagging $tag..."
Push-Location (Join-Path $repoRoot "AetherReach")
try {
    .\gradlew.bat build
}
finally {
    Pop-Location
}

git tag -a $tag -m "AetherReach Core v$Version"
git push origin $tag

Write-Host "Pushed $tag. GitHub Actions will build the jar and attach it to the release."
