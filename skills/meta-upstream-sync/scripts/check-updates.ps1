[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$IncludePath = "",
    [switch]$OutputJson,
    [switch]$IncludeChangeDetails,
    [switch]$AllowNoLocalCommit,
    [string]$GitHubToken = "",
    [ValidateRange(1, 100)]
    [int]$MaxChangeCommits = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:ResolvedGitHubToken = if (-not [string]::IsNullOrWhiteSpace($GitHubToken)) {
    $GitHubToken.Trim()
}
elseif (-not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
    $env:GITHUB_TOKEN.Trim()
}
elseif (-not [string]::IsNullOrWhiteSpace($env:GH_TOKEN)) {
    $env:GH_TOKEN.Trim()
}
else {
    ""
}

function Get-GitHubApiHeaders {
    $headers = @{
        "User-Agent" = "llmctl-meta-upstream-sync"
        "Accept"     = "application/vnd.github+json"
    }

    if (-not [string]::IsNullOrWhiteSpace($script:ResolvedGitHubToken)) {
        $headers["Authorization"] = "Bearer $($script:ResolvedGitHubToken)"
    }

    return $headers
}

function Invoke-GitHubApiGet {
    param([string]$Url)

    $headers = Get-GitHubApiHeaders

    try {
        return Invoke-RestMethod -Uri $Url -Headers $headers -Method Get -TimeoutSec 30
    }
    catch {
        $statusCode = $null
        try {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
        }
        catch {
            $statusCode = $null
        }

        if ($statusCode -eq 403) {
            if ([string]::IsNullOrWhiteSpace($script:ResolvedGitHubToken)) {
                throw "GitHub API returned 403 (likely unauthenticated rate limit). Set GITHUB_TOKEN/GH_TOKEN or pass -GitHubToken."
            }

            throw "GitHub API returned 403 with authentication. Verify token validity/scopes or wait for rate limit reset."
        }

        throw
    }
}

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
    if ($frontmatter -match '(?ms)^\s*adaptedFrom\s*:[ \t]*\r?\n(?<block>(?:[ \t]+-[ \t]*["'']?https?://[^"''\r\n]+["'']?[ \t]*\r?\n?)+)') {
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

    $apiUrl = if ($Query.path) {
        "https://api.github.com/repos/{0}/{1}/commits?path={2}&sha={3}&per_page=1" -f $Query.owner, $Query.repo, $Query.path, $Query.ref
    }
    else {
        "https://api.github.com/repos/{0}/{1}/commits?sha={2}&per_page=1" -f $Query.owner, $Query.repo, $Query.ref
    }

    $response = Invoke-GitHubApiGet -Url $apiUrl

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

function Get-GitHubChangesSince {
    param(
        $Query,
        [DateTimeOffset]$Since,
        [int]$MaxCommits = 20
    )

    $sinceIso = $Since.ToUniversalTime().ToString('o')
    $sinceEscaped = [System.Uri]::EscapeDataString($sinceIso)

    $apiUrl = if ($Query.path) {
        "https://api.github.com/repos/{0}/{1}/commits?path={2}&sha={3}&since={4}&per_page={5}" -f $Query.owner, $Query.repo, $Query.path, $Query.ref, $sinceEscaped, $MaxCommits
    }
    else {
        "https://api.github.com/repos/{0}/{1}/commits?sha={2}&since={3}&per_page={4}" -f $Query.owner, $Query.repo, $Query.ref, $sinceEscaped, $MaxCommits
    }

    $response = Invoke-GitHubApiGet -Url $apiUrl

    $commitObjects = @()
    if ($response -is [System.Array]) {
        $commitObjects = @($response)
    }
    elseif ($response) {
        $commitObjects = @($response)
    }

    $commits = foreach ($commit in $commitObjects) {
        if (-not $commit.sha) {
            continue
        }

        [pscustomobject]@{
            sha      = [string]$commit.sha
            shortSha = ([string]$commit.sha).Substring(0, [Math]::Min(10, ([string]$commit.sha).Length))
            date     = ([DateTimeOffset]$commit.commit.committer.date).ToString('o')
            author   = [string]$commit.commit.author.name
            message  = [string](($commit.commit.message -split "`r?`n", 2)[0])
            url      = [string]$commit.html_url
        }
    }

    return [pscustomobject]@{
        since       = $sinceIso
        commitCount = (@($commits) | Measure-Object).Count
        commits     = @($commits)
    }
}

function Get-GitHubRecentChanges {
    param(
        $Query,
        [int]$MaxCommits = 20
    )

    $apiUrl = if ($Query.path) {
        "https://api.github.com/repos/{0}/{1}/commits?path={2}&sha={3}&per_page={4}" -f $Query.owner, $Query.repo, $Query.path, $Query.ref, $MaxCommits
    }
    else {
        "https://api.github.com/repos/{0}/{1}/commits?sha={2}&per_page={3}" -f $Query.owner, $Query.repo, $Query.ref, $MaxCommits
    }

    $response = Invoke-GitHubApiGet -Url $apiUrl

    $commitObjects = @()
    if ($response -is [System.Array]) {
        $commitObjects = @($response)
    }
    elseif ($response) {
        $commitObjects = @($response)
    }

    $commits = foreach ($commit in $commitObjects) {
        if (-not $commit.sha) {
            continue
        }

        [pscustomobject]@{
            sha      = [string]$commit.sha
            shortSha = ([string]$commit.sha).Substring(0, [Math]::Min(10, ([string]$commit.sha).Length))
            date     = ([DateTimeOffset]$commit.commit.committer.date).ToString('o')
            author   = [string]$commit.commit.author.name
            message  = [string](($commit.commit.message -split "`r?`n", 2)[0])
            url      = [string]$commit.html_url
        }
    }

    return [pscustomobject]@{
        collected   = $true
        commitCount = (@($commits) | Measure-Object).Count
        commits     = @($commits)
    }
}

function New-UpstreamChangesEmpty {
    return [pscustomobject]@{
        collected   = $false
        commitCount = 0
        commits     = @()
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
        if (-not $AllowNoLocalCommit) {
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
                upstreamChanges = New-UpstreamChangesEmpty
                comparison      = [pscustomobject]@{ localIsOlder = $null; deltaDays = $null }
            })
            continue
        }

        $bootstrapChanges = New-UpstreamChangesEmpty
        try {
            $query = Convert-GitHubUrlToQuery -Url $item.sourceUrl
            $upstreamInfo = Get-GitHubLatestCommitInfo -Query $query

            if ($IncludeChangeDetails) {
                $bootstrapChanges = Get-GitHubRecentChanges -Query $query -MaxCommits $MaxChangeCommits
            }
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
                upstreamChanges = $bootstrapChanges
                comparison      = [pscustomobject]@{ localIsOlder = $null; deltaDays = $null }
            })
            continue
        }

        $bootstrapRecommendation = if ($item.mode -eq 'mirror') { 'bootstrap_replace_from_upstream' } else { 'bootstrap_review_and_merge_from_upstream' }
        $results.Add([pscustomobject]@{
            id              = $item.id
            localPath       = $item.localPath
            mode            = $item.mode
            sourceUrl       = $item.sourceUrl
            status          = 'update_available'
            recommendation  = $bootstrapRecommendation
            recommendUpdate = $true
            reason          = 'local_file_not_in_git_history_bootstrap_allowed'
            localGit        = $localGit
            upstream        = [pscustomobject]@{
                commitSha  = $upstreamInfo.commitSha
                commitDate = $upstreamInfo.commitDate
            }
            upstreamChanges = $bootstrapChanges
            comparison      = [pscustomobject]@{ localIsOlder = $null; deltaDays = $null }
        })
        continue
    }

    $localDate = Parse-DateSafe -Value $localGit.commitDate
    $upstreamChanges = New-UpstreamChangesEmpty

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
            upstreamChanges = $upstreamChanges
            comparison      = [pscustomobject]@{ localIsOlder = $null; deltaDays = $null }
        })
        continue
    }

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

        if ($IncludeChangeDetails) {
            try {
                $upstreamChanges = Get-GitHubChangesSince -Query $query -Since $localDate -MaxCommits $MaxChangeCommits
                $upstreamChanges.collected = $true
            }
            catch {
                $upstreamChanges = [pscustomobject]@{
                    collected   = $false
                    commitCount = 0
                    commits     = @()
                    error       = $_.Exception.Message
                }
            }
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
        upstreamChanges = $upstreamChanges
        comparison      = [pscustomobject]@{
            localIsOlder = $localIsOlder
            deltaDays    = $deltaDays
        }
    })
}

$uniqueFiles = ($results | Select-Object -Property localPath -Unique | Measure-Object).Count
$authMode = if ([string]::IsNullOrWhiteSpace($script:ResolvedGitHubToken)) { 'unauthenticated' } else { 'token' }

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
    authMode    = $authMode
    summary     = $summary
    results     = $results
}

if ($OutputJson) {
    $output | ConvertTo-Json -Depth 10
}
else {
    Write-Host "Meta upstream sync check complete"
    Write-Host ("Auth: {0} | Files: {1} | Upstreams: {2} | Up-to-date: {3} | Update-available: {4} | Failed: {5} | Recommend: {6}" -f $authMode, $summary.filesChecked, $summary.upstreamChecks, $summary.upToDateCount, $summary.updateAvailableCount, $summary.failedCount, $summary.recommendCount)
    if ($authMode -eq 'unauthenticated') {
        Write-Host "Tip: Set GITHUB_TOKEN (or GH_TOKEN) or pass -GitHubToken to avoid GitHub API rate-limit 403 errors."
    }
    if (-not $IncludeChangeDetails) {
        Write-Host "Tip: Run again with -IncludeChangeDetails and a narrow -IncludePath for updated items to inspect commit-level upstream changes."
    }

    foreach ($result in $results) {
        if ($IncludeChangeDetails -and $null -ne $result.upstreamChanges) {
            $changeCount = [int]$result.upstreamChanges.commitCount
            Write-Host ("[{0}] {1} ({2}) <- {3} | {4} | upstream commits since local: {5} | recommendation: {6}" -f $result.status, $result.localPath, $result.mode, $result.sourceUrl, $result.reason, $changeCount, $result.recommendation)
        }
        else {
            Write-Host ("[{0}] {1} ({2}) <- {3} | {4} | recommendation: {5}" -f $result.status, $result.localPath, $result.mode, $result.sourceUrl, $result.reason, $result.recommendation)
        }
    }
}
