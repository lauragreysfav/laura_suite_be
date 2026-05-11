param()

$eventType = $env:whisparr_eventtype
if ($eventType -ne "Grab") { exit 0 }

$downloadId = $env:whisparr_download_id
$releaseTitle = $env:whisparr_release_title
$movieTitle = $env:whisparr_movie_title
$movieYear = $env:whisparr_movie_year

if (-not $downloadId) {
    Write-Output "No download_id (info hash) provided by Whisparr"
    exit 1
}

$magnet = "magnet:?xt=urn:btih:$downloadId&dn=$([System.Uri]::EscapeDataString("$releaseTitle"))"

$body = @{ magnet = $magnet; seed = 1 } | ConvertTo-Json

try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/torrents/add" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
    Write-Output "Added to TorBox: $releaseTitle (hash: $downloadId)"
} catch {
    Write-Output "Failed to add to TorBox: $_"
    exit 1
}
