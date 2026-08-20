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

function Resolve-GitHubToken {
    param([string]$ExplicitToken)

    # Explicit parameter and env vars win, for CI or override scenarios.
    if (-not [string]::IsNullOrWhiteSpace($ExplicitToken)) { return $ExplicitToken.Trim() }
    if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) { return $env:GITHUB_TOKEN.Trim() }
    if (-not [string]::IsNullOrWhiteSpace($env:GH_TOKEN)) { return $env:GH_TOKEN.Trim() }

    # Default: reuse the gh CLI's stored login (gh is a project prerequisite).
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        try {
            $token = (& gh auth token 2>$null)
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($token)) {
                return $token.Trim()
            }
        }
        catch {
            # gh present but not logged in — fall through to unauthenticated.
        }
    }

    return ""
}

$script:ResolvedGitHubToken = Resolve-GitHubToken -ExplicitToken $GitHubToken

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
                throw "GitHub API returned 403 (likely unauthenticated rate limit). Run 'gh auth login', or set GITHUB_TOKEN/GH_TOKEN, or pass -GitHubToken."
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

function Get-AdaptedEntriesFromFrontmatter {
    <#
      Parse a provenance block into url/took/license/fidelity records.

      Three accepted forms:
        adaptedFrom: "https://..."                          whole file, one upstream
        adaptedFrom:
          - "https://..."                                   whole file, several upstreams
        adaptedFrom:
          - url: "https://..."                              scoped adaptation
            license: MIT                                    SPDX id of the upstream, or NONE
            fidelity: partly-derived                        obligation level (see below)
            took: "what was taken"

      `took` records only what was taken — never what was *not* taken, and never a
      measurement; both rot with no local change to trigger a refresh. It is
      single-line only (block scalars are not parsed).

      `fidelity` is one of inspiration-only / structural-echo / partly-derived /
      largely-derived. Absent means whole-file derivation, which check-licenses.py
      treats as largely-derived. `license` and `fidelity` are consumed by
      scripts/check-licenses.py and scripts/gen-notices.py in the .llmctl root; this
      script carries them through so both tools read one parse of the same block.

      Line-based rather than one regex: the object form nests, and a regex that
      tries to span it silently matches nothing, which drops the file from the
      audit without an error.
    #>
    param(
        [string]$Frontmatter
    )

    $entries = New-Object System.Collections.Generic.List[object]
    $lines = $Frontmatter -split '\r?\n'
    $keyIndent = -1

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]

        if ($keyIndent -lt 0) {
            if ($line -match '^(?<indent>[ \t]*)adaptedFrom[ \t]*:[ \t]*(?<inline>.*)$') {
                $keyIndent = $Matches.indent.Length
                $inline = $Matches.inline.Trim()
                if ($inline -match '^["'']?(?<url>https?://[^"''\s]+?)["'']?$') {
                    $entries.Add([pscustomobject]@{ url = $Matches.url; took = ''; license = ''; fidelity = '' })
                    return $entries
                }
            }
            continue
        }

        if ($line.Trim() -eq '') { continue }

        # The block ends at the first line indented no deeper than the key itself.
        $indent = ($line -replace '^([ \t]*).*$', '$1').Length
        if ($indent -le $keyIndent) { break }

        if ($line -match '^[ \t]*-[ \t]*url[ \t]*:[ \t]*["'']?(?<url>https?://[^"''\s]+?)["'']?[ \t]*$') {
            $entries.Add([pscustomobject]@{ url = $Matches.url; took = ''; license = ''; fidelity = '' })
        }
        elseif ($line -match '^[ \t]*-[ \t]*["'']?(?<url>https?://[^"''\s]+?)["'']?[ \t]*$') {
            $entries.Add([pscustomobject]@{ url = $Matches.url; took = ''; license = ''; fidelity = '' })
        }
        elseif ($line -match '^[ \t]*took[ \t]*:[ \t]*(?<took>.+?)[ \t]*$' -and $entries.Count -gt 0) {
            $entries[$entries.Count - 1].took = ($Matches.took.Trim() -replace '^["'']', '' -replace '["'']$', '')
        }
        elseif ($line -match '^[ \t]*license[ \t]*:[ \t]*(?<license>.+?)[ \t]*$' -and $entries.Count -gt 0) {
            $entries[$entries.Count - 1].license = ($Matches.license.Trim() -replace '^["'']', '' -replace '["'']$', '')
        }
        elseif ($line -match '^[ \t]*fidelity[ \t]*:[ \t]*(?<fidelity>.+?)[ \t]*$' -and $entries.Count -gt 0) {
            $entries[$entries.Count - 1].fidelity = ($Matches.fidelity.Trim() -replace '^["'']', '' -replace '["'']$', '')
        }
    }

    return $entries
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

    # Collect metadata.provenance.adaptedFrom (string, array, or object form),
    # one entry per upstream URL.
    $adapted = Get-AdaptedEntriesFromFrontmatter -Frontmatter $frontmatter

    $entries = New-Object System.Collections.Generic.List[object]

    foreach ($a in $adapted) {
        $entries.Add([pscustomobject]@{
            id        = $relativePath
            localPath = $relativePath
            sourceUrl = $a.url
            took      = $a.took
            license   = $a.license
            fidelity  = $a.fidelity
        })
    }

    return $entries
}

function Test-TrackableSource {
    <#
    .SYNOPSIS
    Can this source URL be compared against a local commit date at all?

    .DESCRIPTION
    Drift detection needs an upstream revision history to read a date from, which
    limits it to the hosts Convert-GitHubUrlToQuery understands. Anything else --
    an ISBN or DOI resolver standing in for a book, a paper, a vendor doc page --
    is a legitimate provenance source that simply has nothing to diff, and is
    reported as `not_trackable` rather than as a fetch failure.

    Keep the host list here identical to the one Convert-GitHubUrlToQuery
    accepts; the two answering differently would either throw on something this
    admits, or silently skip something that could have been checked.
    #>
    param([string]$Url)

    $parsed = $null
    if (-not [System.Uri]::TryCreate($Url, [System.UriKind]::Absolute, [ref]$parsed)) {
        return $false
    }
    return $parsed.Host -eq 'github.com'
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
        # A bare repository URL names no branch, so leave the ref empty and let
        # the API fall back to the repository's own default. Hardcoding 'main'
        # here 404s on every repo that still uses 'master' or a custom default
        # -- and a 404 is reported as `fetch_failed`, which reads like a broken
        # URL rather than a wrong assumption on our side.
        return [pscustomobject]@{
            owner = $owner
            repo  = $repo
            ref   = ''
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

function Get-CommitsApiUrl {
    <#
    .SYNOPSIS
    Build a /commits query, omitting the parameters that have no value.

    .DESCRIPTION
    `path` and `sha` are both optional to the GitHub API, and both are genuinely
    absent for some source URL forms: a repository-level entry has no path, and
    a bare repository URL names no branch. Sending `sha=` empty is not the same
    as omitting it -- omitting it is what makes the API use the repository's own
    default branch. Assembled here so all three callers agree.
    #>
    param($Query, [hashtable]$Extra = @{})

    $params = [ordered]@{}
    if ($Query.path) { $params['path'] = $Query.path }
    if ($Query.ref) { $params['sha'] = $Query.ref }
    foreach ($key in $Extra.Keys) { $params[$key] = $Extra[$key] }

    $pairs = foreach ($key in $params.Keys) { '{0}={1}' -f $key, $params[$key] }
    return 'https://api.github.com/repos/{0}/{1}/commits?{2}' -f $Query.owner, $Query.repo, ($pairs -join '&')
}

function Get-GitHubLatestCommitInfo {
    param($Query)

    $apiUrl = Get-CommitsApiUrl -Query $Query -Extra @{ per_page = 1 }

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

    $apiUrl = Get-CommitsApiUrl -Query $Query -Extra @{ since = $sinceEscaped; per_page = $MaxCommits }

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

    $apiUrl = Get-CommitsApiUrl -Query $Query -Extra @{ per_page = $MaxCommits }

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

# Directories that hold copies rather than sources: APM dependencies, the
# per-target deploy mirrors `apm install` writes, and build scratch. Must stay
# identical to `skip` in scripts/provenance.py — release-check.py's parity gate
# compares what the two parsers find, so a directory scanned by one and not the
# other reports as a parser disagreement rather than as the duplicate it is.
# A vendored upstream carries its own `adaptedFrom`, and a deployed mirror
# carries the same one twice; auditing either would attribute an upstream's
# provenance to this repository.
$script:ExcludedDirs = @('.git', 'apm_modules', 'build', 'node_modules',
                         '__pycache__', '.claude', '.agents', 'LICENSES')

function Test-ExcludedPath {
    param(
        [string]$Repo,
        [string]$AbsolutePath
    )

    $relative = [IO.Path]::GetRelativePath($Repo, $AbsolutePath).Replace('\', '/')
    foreach ($segment in ($relative -split '/')) {
        if ($script:ExcludedDirs -contains $segment) { return $true }
    }
    return $false
}

function Discover-TrackedEntries {
    param([string]$Repo)

    $patterns = @('*.agent.md', 'SKILL.md', '*.instructions.md', '*.prompt.md')
    $entries = New-Object System.Collections.Generic.List[object]

    foreach ($pattern in $patterns) {
        $files = Get-ChildItem -LiteralPath $Repo -Recurse -File -Force -Filter $pattern
        foreach ($file in $files) {
            if (Test-ExcludedPath -Repo $Repo -AbsolutePath $file.FullName) { continue }
            $fileEntries = Get-TrackEntriesFromFile -Repo $Repo -AbsolutePath $file.FullName
            foreach ($entry in $fileEntries) {
                $entries.Add($entry)
            }
        }
    }

    return $entries
}

$repoRootResolved = Get-RepoRoot -Hint $RepoRoot
$trackedEntries = @(Discover-TrackedEntries -Repo $repoRootResolved)

if ($IncludePath) {
    $trackedEntries = @($trackedEntries | Where-Object { $_.localPath -like $IncludePath })
}

if ($trackedEntries.Count -eq 0) {
    if ($IncludePath) {
        throw "No tracked files found for IncludePath '$IncludePath'."
    }
    throw "No tracked files found. Add metadata.provenance.adaptedFrom URLs in frontmatter."
}

$results = New-Object System.Collections.Generic.List[object]

foreach ($item in $trackedEntries) {
    # A source with no commit history cannot be drift-checked at all -- a book,
    # a paper, a vendor doc page. That is a permanent property of the URL, not a
    # failure to fetch it, so it is classified before anything is attempted and
    # kept out of failedCount. Filing these as `fetch_failed` would park
    # unfixable rows in the audit, which is how an audit stops being read.
    if (-not (Test-TrackableSource -Url $item.sourceUrl)) {
        $results.Add([pscustomobject]@{
            id              = $item.id
            localPath       = $item.localPath
            sourceUrl       = $item.sourceUrl
            took            = $item.took
            license         = $item.license
            fidelity        = $item.fidelity
            status          = 'not_trackable'
            recommendation  = 'none_source_has_no_revision_history'
            recommendUpdate = $false
            reason          = 'source_host_is_not_revision_controlled'
            localGit        = [pscustomobject]@{ commitSha = ''; commitDate = '' }
            upstream        = [pscustomobject]@{ commitSha = ''; commitDate = '' }
            upstreamChanges = New-UpstreamChangesEmpty
            comparison      = [pscustomobject]@{ localIsOlder = $null; deltaDays = $null }
        })
        continue
    }

    $localGit = Get-LocalGitInfo -Repo $repoRootResolved -Path $item.localPath
    if (-not $localGit.commitDate) {
        if (-not $AllowNoLocalCommit) {
            $results.Add([pscustomobject]@{
                id              = $item.id
                localPath       = $item.localPath
                sourceUrl       = $item.sourceUrl
                took            = $item.took
                license         = $item.license
                fidelity        = $item.fidelity
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
                sourceUrl       = $item.sourceUrl
                took            = $item.took
                license         = $item.license
                fidelity        = $item.fidelity
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

        $results.Add([pscustomobject]@{
            id              = $item.id
            localPath       = $item.localPath
            sourceUrl       = $item.sourceUrl
            took            = $item.took
            license         = $item.license
            fidelity        = $item.fidelity
            status          = 'update_available'
            recommendation  = 'bootstrap_review_and_merge_from_upstream'
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
            sourceUrl       = $item.sourceUrl
            took            = $item.took
            license         = $item.license
            fidelity        = $item.fidelity
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
        $recommendation = 'review_and_merge_from_upstream'

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
        sourceUrl       = $item.sourceUrl
        took            = $item.took
        license         = $item.license
        fidelity        = $item.fidelity
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
    notTrackableCount    = ($results | Where-Object { $_.status -eq 'not_trackable' } | Measure-Object).Count
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
    Write-Host ("Auth: {0} | Files: {1} | Upstreams: {2} | Up-to-date: {3} | Update-available: {4} | Failed: {5} | Not-trackable: {6} | Recommend: {7}" -f $authMode, $summary.filesChecked, $summary.upstreamChecks, $summary.upToDateCount, $summary.updateAvailableCount, $summary.failedCount, $summary.notTrackableCount, $summary.recommendCount)
    if ($authMode -eq 'unauthenticated') {
        Write-Host "Tip: Run 'gh auth login' (or set GITHUB_TOKEN/GH_TOKEN, or pass -GitHubToken) to avoid GitHub API rate-limit 403 errors."
    }
    if (-not $IncludeChangeDetails) {
        Write-Host "Tip: Run again with -IncludeChangeDetails and a narrow -IncludePath for updated items to inspect commit-level upstream changes."
    }

    foreach ($result in $results) {
        if ($IncludeChangeDetails -and $null -ne $result.upstreamChanges) {
            $changeCount = [int]$result.upstreamChanges.commitCount
            Write-Host ("[{0}] {1} <- {2} | {3} | upstream commits since local: {4} | recommendation: {5}" -f $result.status, $result.localPath, $result.sourceUrl, $result.reason, $changeCount, $result.recommendation)
        }
        else {
            Write-Host ("[{0}] {1} <- {2} | {3} | recommendation: {4}" -f $result.status, $result.localPath, $result.sourceUrl, $result.reason, $result.recommendation)
        }
    }
}
