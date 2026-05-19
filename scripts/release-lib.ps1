function Normalize-ReleaseVersion {
    param([Parameter(Mandatory = $true)][string] $Version)

    $normalized = $Version.Trim()
    if ($normalized -match '^(\d+\.\d+)(-[A-Za-z0-9][A-Za-z0-9.-]*)?$') {
        $normalized = "$($Matches[1]).0$($Matches[2])"
    }

    if ($normalized -notmatch '^\d+\.\d+\.\d+(-[A-Za-z0-9][A-Za-z0-9.-]*)?$') {
        Write-Error "Version must look like 1.0.0, 1.0, or 1.0.0-beta."
    }

    return $normalized
}

function Resolve-RepoRoot {
    param([Parameter(Mandatory = $true)][string] $ScriptRoot)
    return (Resolve-Path (Join-Path $ScriptRoot "..")).Path
}

function Assert-TrackedTreeClean {
    $status = git status --porcelain --untracked-files=no
    if ($status) {
        Write-Error "Tracked Git files are not clean. Commit or stash tracked changes before creating a release tag."
    }
}

function Assert-UniqueTag {
    param([Parameter(Mandatory = $true)][string] $Tag)

    $existingTag = git tag --list $Tag
    if ($existingTag) {
        Write-Error "Tag already exists locally: $Tag"
    }

    git fetch origin --tags
    $remoteTag = git ls-remote --tags origin "refs/tags/$Tag"
    if ($remoteTag) {
        Write-Error "Tag already exists on origin: $Tag"
    }
}
