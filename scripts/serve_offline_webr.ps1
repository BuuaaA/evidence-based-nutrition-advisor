param(
    [int]$Port = 8321,
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$rootPath = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar)
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
$mime = @{
    '.html'='text/html; charset=utf-8'; '.js'='text/javascript; charset=utf-8';
    '.mjs'='text/javascript; charset=utf-8'; '.json'='application/json; charset=utf-8';
    '.wasm'='application/wasm'; '.css'='text/css; charset=utf-8'; '.tgz'='application/gzip';
    '.gz'='application/gzip'; '.data'='application/octet-stream'; '.rds'='application/octet-stream';
    '.txt'='text/plain; charset=utf-8'; '.csv'='text/csv; charset=utf-8'
}

function Send-Response($stream, [int]$status, [string]$reason, [byte[]]$body, [string]$contentType) {
    $head = "HTTP/1.1 $status $reason`r`nContent-Type: $contentType`r`nContent-Length: $($body.Length)`r`nConnection: close`r`nCross-Origin-Opener-Policy: same-origin`r`nCross-Origin-Embedder-Policy: require-corp`r`n`r`n"
    $headBytes = [Text.Encoding]::ASCII.GetBytes($head)
    $stream.Write($headBytes, 0, $headBytes.Length)
    if ($body.Length) { $stream.Write($body, 0, $body.Length) }
}

$listener.Start()
Write-Host "Offline webR server: http://localhost:$Port/webr-offline/reports/"
Write-Host "Root: $rootPath  (Ctrl+C to stop)"
try {
    while ($true) {
        $client = $listener.AcceptTcpClient()
        try {
            $stream = $client.GetStream()
            $reader = [IO.StreamReader]::new($stream, [Text.Encoding]::ASCII, $false, 4096, $true)
            $request = $reader.ReadLine()
            while (($line = $reader.ReadLine()) -ne '') { if ($null -eq $line) { break } }
            if (-not $request -or $request -notmatch '^(GET|HEAD)\s+([^\s]+)') {
                Send-Response $stream 400 'Bad Request' ([Text.Encoding]::UTF8.GetBytes('Bad Request')) 'text/plain; charset=utf-8'
                continue
            }
            $method = $Matches[1]
            $urlPath = [Uri]::UnescapeDataString(($Matches[2] -split '\?')[0]).TrimStart('/')
            $candidate = [IO.Path]::GetFullPath((Join-Path $rootPath ($urlPath -replace '/', [IO.Path]::DirectorySeparatorChar)))
            if (-not ($candidate.Equals($rootPath, [StringComparison]::OrdinalIgnoreCase) -or
                      $candidate.StartsWith($rootPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase))) {
                Send-Response $stream 403 'Forbidden' ([Text.Encoding]::UTF8.GetBytes('Forbidden')) 'text/plain; charset=utf-8'
                continue
            }
            if (Test-Path -LiteralPath $candidate -PathType Container) { $candidate = Join-Path $candidate 'index.html' }
            if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
                Send-Response $stream 404 'Not Found' ([Text.Encoding]::UTF8.GetBytes('Not Found')) 'text/plain; charset=utf-8'
                continue
            }
            $body = if ($method -eq 'HEAD') { [byte[]]::new(0) } else { [IO.File]::ReadAllBytes($candidate) }
            $ext = [IO.Path]::GetExtension($candidate).ToLowerInvariant()
            $contentType = if ($mime.ContainsKey($ext)) { $mime[$ext] } else { 'application/octet-stream' }
            Send-Response $stream 200 'OK' $body $contentType
        } finally {
            $client.Dispose()
        }
    }
} finally {
    $listener.Stop()
}
