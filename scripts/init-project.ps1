<#
.SYNOPSIS
  Initialize a copy of this template as a new project: renames the app in the
  few places the template hardcodes a default name.

.EXAMPLE
  pwsh ./scripts/init-project.ps1 -Name receipt-budget
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$Name
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$utf8NoBom = New-Object System.Text.UTF8Encoding $false

function Replace-In($relPath, $from, $to) {
  $path = Join-Path $root $relPath
  if (-not (Test-Path $path)) { Write-Warning "skip (missing): $relPath"; return }
  $text = [System.IO.File]::ReadAllText($path)
  $new = $text.Replace($from, $to)
  if ($new -ne $text) {
    [System.IO.File]::WriteAllText($path, $new, $utf8NoBom)
    Write-Host "updated: $relPath"
  }
}

Replace-In 'apps\api\app\core\config.py' 'app_name: str = "app-api"' "app_name: str = `"$Name`""
Replace-In 'apps\api\.env.example'       'APP_NAME=app-api'           "APP_NAME=$Name"
Replace-In 'apps\web\package.json'       '"name": "app-web"'          "`"name`": `"$Name-web`""
Replace-In 'apps\web\index.html'         '<title>App</title>'         "<title>$Name</title>"

Write-Host ""
Write-Host "Done. Project renamed to '$Name'." -ForegroundColor Green
Write-Host "Next: fill apps/api/.env and apps/web/.env.local, then /startproject in Claude Code."
