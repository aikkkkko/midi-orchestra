param(
    [string]$Root = ".runtime/surge",
    [string]$Config = "config.local.json"
)
$ErrorActionPreference = "Stop"
& py -3.11 (Join-Path $PSScriptRoot "setup_surge.py") --root $Root --config $Config
if ($LASTEXITCODE -ne 0) { throw "Surge setup failed; see the error above." }
