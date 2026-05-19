param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+([-.][A-Za-z0-9]+)?$')]
    [string] $Version
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$status = git status --porcelain
if ($status) {
    Write-Error "Git working tree is not clean. Commit or stash changes before creating a release tag."
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
