[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$IncludePath = "",
    [switch]$OutputJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    param([string]$Hint)

    if ($Hint -and (Test-Path -LiteralPath $Hint)) {
        return (Resolve-Path -LiteralPath $Hint).Path
    }

    $root = (& git rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -eq 0 -and $root) {
        return $root.Trim()
    }

    throw "Unable to determine git repository root. Run from a git repo or pass -RepoRoot."
}

function Get-LocalGitInfo {
    param(
        [string]$Repo,
        [string]$Path
    )

    Push-Location -LiteralPath $Repo
    try {
        $out = (& git log -n 1 --format="%H|%cI" -- $Path 2>$null)
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($out)) {
            return [pscustomobject]@{
                commitSha  = ""
                commitDate = ""
            }
        }

        $parts = $out.Trim().Split('|', 2)
        return [pscustomobject]@{
            commitSha  = if ($parts.Count -ge 1) { $parts[0] } else { "" }
            commitDate = if ($parts.Count -ge 2) { $parts[1] } else { "" }
        }
    }
    finally {
        Pop-Location
    }
}

function Get-FrontmatterBlock {
    param([string]$Content)

    if (-not $Content) {
        return ""
    }

    if ($Content -match '(?s)^---\s*\r?\n(?<fm>.*?)\r?\n---\s*(?:\r?\n|$)') {
        return $Matches.fm
    }

    return ""
}

function Get-TrackEntriesFromFile {
    param(
        [string]$Repo,
        [string]$AbsolutePath
    )

    $content = Get-Content -LiteralPath $AbsolutePath -Raw
    $frontmatter = Get-FrontmatterBlock -Content $content
    if (-not $frontmatter) {
        return @()
    }

    $relativePath = [IO.Path]::GetRelativePath($Repo, $AbsolutePath).Replace('\', '/')

    # Collect metadata.source (single URL => mirror)
    $sourceUrl = ""
    if ($frontmatter -match '(?m)^\s*source\s*:\s*["'']?(?<url>https?://[^"''\r\n]+)') {
        $sourceUrl = $Matches.url.Trim()
    }

    # Collect metadata.adaptedFrom (single URL or YAML array => adapted)
    $adaptedUrls = New-Object System.Collections.Generic.List[string]

    # Match YAML array form:  adaptedFrom:\n    - "url1"\n    - "url2"
    if ($frontmatter -match '(?ms)^\s*adaptedFrom\s*:\s*\r?\n(?<block>([ \t]+-\s*["'']?https?://[^"''\r\n]+["'']?\s*\r?\n?)+)') {
        $block = $Matches.block
        $arrayMatches = [regex]::Matches($block, '(?m)-\s*["'']?(?<url>https?://[^"''\r\n]+?)["'']?\s*$')
        foreach ($m in $arrayMatches) {
            $adaptedUrls.Add($m.Groups['url'].Value.Trim())
        }
    }
    # Match single-value form:  adaptedFrom: "url"
    elseif ($frontmatter -match '(?m)^\s*adaptedFrom\s*:\s*["'']?(?<url>https?://[^"''\r\n]+)') {
        $adaptedUrls.Add($Matches.url.Trim())
    }

    $entries = New-Object System.Collections.Generic.List[object]

    # Adapted entries (one per upstream URL)
    foreach ($url in $adaptedUrls) {
        $entries.Add([pscustomobject]@{
            id        = $relativePath
            mode      = 'adapted'
            localPath = $relativePath
            sourceUrl = $url
        })
    }

    # Mirror entry (only when no adaptedFrom URLs exist)
    if ($entries.Count -eq 0 -and $sourceUrl) {
        $entries.Add([pscustomobject]@{
            id        = $relativePath
            mode      = 'mirror'
            localPath = $relativePath
            sourceUrl = $sourceUrl
        })
    }

    return $entries
}

function Convert-GitHubUrlToQuery {
    param([string]$Url)

    $uri = [System.Uri]$Url
    if ($uri.Host -ne 'github.com') {
        throw "Unsupported source host '$($uri.Host)'. Only github.com URLs are supported."
    }

    $segments = $uri.AbsolutePath.Trim('/') -split '/'
    if ($segments.Length -lt 2) {
        throw "Invalid GitHub URL path: '$Url'"
    }

    $owner = $segments[0]
    $repo = $segments[1]

    if ($segments.Length -eq 2) {
        return [pscustomobject]@{
            owner = $owner
            repo  = $repo
            ref   = 'main'
            path  = ''
        }
    }

    if ($segments.Length -ge 4 -and ($segments[2] -eq 'blob' -or $segments[2] -eq 'tree')) {
        $ref = $segments[3]
        $path = if ($segments.Length -gt 4) { ($segments[4..($segments.Length - 1)] -join '/') } else { '' }

        return [pscustomobject]@{
            owner = $owner
            repo  = $repo
            ref   = $ref
            path  = $path
        }
    }

    throw "Unsupported GitHub URL structure: '$Url'. Use repository, tree, or blob URLs."
}

function Get-GitHubLatestCommitInfo {
    param($Query)

    $headers = @{
        "User-Agent" = "llmctl-upstream-sync"
        "Accept"     = "application/vnd.github+json"
    }

    $apiUrl = if ($Query.path) {
        "https://api.github.com/repos/{0}/{1}/commits?path={2}&sha={3}&per_page=1" -f $Query.owner, $Query.repo, $Query.path, $Query.ref
    }
    else {
        "https://api.github.com/repos/{0}/{1}/commits?sha={2}&per_page=1" -f $Query.owner, $Query.repo, $Query.ref
    }

    $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -Method Get -TimeoutSec 30

    $first = $null
    if ($response -is [System.Array]) {
        if ($response.Length -gt 0) {
            $first = $response[0]
        }
    }
    else {
        $first = $response
    }

    if (-not $first -or -not $first.sha) {
        throw "No upstream commits found for '$($Query.owner)/$($Query.repo)' at ref '$($Query.ref)' and path '$($Query.path)'."
    }

    return [pscustomobject]@{
        commitSha  = [string]$first.sha
        commitDate = ([DateTimeOffset]$first.commit.committer.date).ToString('o')
    }
}

function Parse-DateSafe {
    param([string]$Value)

    if (-not $Value) {
        throw "Cannot parse empty date value."
    }

    $parsed = [DateTimeOffset]::MinValue
    if ([DateTimeOffset]::TryParse($Value, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::AssumeUniversal, [ref]$parsed)) {
        return $parsed
    }

    if ([DateTimeOffset]::TryParse($Value, [Globalization.CultureInfo]::CurrentCulture, [Globalization.DateTimeStyles]::AssumeUniversal, [ref]$parsed)) {
        return $parsed
    }

    throw "Unrecognized date format: '$Value'"
}

function Discover-TrackedEntries {
    param([string]$Repo)

    $patterns = @('*.agent.md', 'SKILL.md', '*.instructions.md', '*.prompt.md')
    $entries = New-Object System.Collections.Generic.List[object]

    foreach ($pattern in $patterns) {
        $files = Get-ChildItem -LiteralPath $Repo -Recurse -File -Filter $pattern
        foreach ($file in $files) {
            $fileEntries = Get-TrackEntriesFromFile -Repo $Repo -AbsolutePath $file.FullName
            foreach ($entry in $fileEntries) {
                $entries.Add($entry)
            }
        }
    }

    return $entries
}

$repoRootResolved = Get-RepoRoot -Hint $RepoRoot
$trackedEntries = Discover-TrackedEntries -Repo $repoRootResolved

if ($IncludePath) {
    $trackedEntries = @($trackedEntries | Where-Object { $_.localPath -like $IncludePath })
}

if ($trackedEntries.Count -eq 0) {
    if ($IncludePath) {
        throw "No tracked files found for IncludePath '$IncludePath'."
    }
    throw "No tracked files found. Add metadata.source or metadata.adaptedFrom URLs in frontmatter."
}

$results = New-Object System.Collections.Generic.List[object]

foreach ($item in $trackedEntries) {
    $localGit = Get-LocalGitInfo -Repo $repoRootResolved -Path $item.localPath
    if (-not $localGit.commitDate) {
        $results.Add([pscustomobject]@{
            id              = $item.id
            localPath       = $item.localPath
            mode            = $item.mode
            sourceUrl       = $item.sourceUrl
            status          = 'missing_local_commit'
            recommendation  = 'commit_local_file_first'
            recommendUpdate = $false
            reason          = 'local_file_not_in_git_history'
            localGit        = $localGit
            upstream        = [pscustomobject]@{ commitSha = ''; commitDate = '' }
            comparison      = [pscustomobject]@{ localIsOlder = $null; deltaDays = $null }
        })
        continue
    }

    try {
        $query = Convert-GitHubUrlToQuery -Url $item.sourceUrl
        $upstreamInfo = Get-GitHubLatestCommitInfo -Query $query
    }
    catch {
        $results.Add([pscustomobject]@{
            id              = $item.id
            localPath       = $item.localPath
            mode            = $item.mode
            sourceUrl       = $item.sourceUrl
            status          = 'fetch_failed'
            recommendation  = 'check_source_url'
            recommendUpdate = $false
            reason          = $_.Exception.Message
            localGit        = $localGit
            upstream        = [pscustomobject]@{ commitSha = ''; commitDate = '' }
            comparison      = [pscustomobject]@{ localIsOlder = $null; deltaDays = $null }
        })
        continue
    }

    $localDate = Parse-DateSafe -Value $localGit.commitDate
    $upstreamDate = Parse-DateSafe -Value $upstreamInfo.commitDate
    $localIsOlder = $localDate -lt $upstreamDate
    $deltaDays = [math]::Round(($upstreamDate - $localDate).TotalDays, 3)

    $status = if ($localIsOlder) { 'update_available' } else { 'up_to_date' }
    $recommendation = 'none'
    $recommendUpdate = $false
    $reason = ''

    if ($localIsOlder) {
        $recommendUpdate = $true
        $reason = 'upstream_commit_newer_than_local_commit'
        if ($item.mode -eq 'mirror') {
            $recommendation = 'replace_from_upstream'
        }
        else {
            $recommendation = 'review_and_merge_from_upstream'
        }
    }
    else {
        $reason = 'local_commit_date_is_not_older_than_upstream'
    }

    $results.Add([pscustomobject]@{
        id              = $item.id
        localPath       = $item.localPath
        mode            = $item.mode
        sourceUrl       = $item.sourceUrl
        status          = $status
        recommendation  = $recommendation
        recommendUpdate = $recommendUpdate
        reason          = $reason
        localGit        = $localGit
        upstream        = [pscustomobject]@{
            commitSha  = $upstreamInfo.commitSha
            commitDate = $upstreamInfo.commitDate
        }
        comparison      = [pscustomobject]@{
            localIsOlder = $localIsOlder
            deltaDays    = $deltaDays
        }
    })
}

$uniqueFiles = ($results | Select-Object -Property localPath -Unique | Measure-Object).Count

$summary = [pscustomobject]@{
    filesChecked         = $uniqueFiles
    upstreamChecks       = $results.Count
    upToDateCount        = ($results | Where-Object { $_.status -eq 'up_to_date' } | Measure-Object).Count
    updateAvailableCount = ($results | Where-Object { $_.status -eq 'update_available' } | Measure-Object).Count
    failedCount          = ($results | Where-Object { $_.status -in @('fetch_failed', 'missing_local_commit') } | Measure-Object).Count
    recommendCount       = ($results | Where-Object { $_.recommendUpdate } | Measure-Object).Count
}

$output = [pscustomobject]@{
    generatedAt = (Get-Date).ToString('o')
    repoRoot    = $repoRootResolved
    includePath = $IncludePath
    summary     = $summary
    results     = $results
}

if ($OutputJson) {
    $output | ConvertTo-Json -Depth 10
}
else {
    Write-Host "Upstream sync check complete"
    Write-Host ("Files: {0} | Upstreams: {1} | Up-to-date: {2} | Update-available: {3} | Failed: {4} | Recommend: {5}" -f $summary.filesChecked, $summary.upstreamChecks, $summary.upToDateCount, $summary.updateAvailableCount, $summary.failedCount, $summary.recommendCount)

    foreach ($result in $results) {
        Write-Host ("[{0}] {1} ({2}) <- {3} | {4} | recommendation: {5}" -f $result.status, $result.localPath, $result.mode, $result.sourceUrl, $result.reason, $result.recommendation)
    }
}
