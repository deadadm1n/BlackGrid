param(
    [Parameter(Mandatory = $true)]
    [string] $Version
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "release-lib.ps1")

$Version = Normalize-ReleaseVersion $Version
$repoRoot = Resolve-RepoRoot $PSScriptRoot
Set-Location $repoRoot

$tag = "aetherreach-v$Version"

Assert-TrackedTreeClean
Assert-UniqueTag $tag

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
