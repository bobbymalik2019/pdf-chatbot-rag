# Checks only response status, redirect origin/path and required parameter presence.
# No cookies, state, nonce, code challenge or other parameter values are printed.
param([string]$Url = 'https://chatbottest.charter26.com/auth/login')
$ErrorActionPreference = 'Stop'
$headers = & curl.exe --ssl-no-revoke -sS -D - -o NUL $Url
if ($LASTEXITCODE -ne 0) { throw "curl failed with exit code $LASTEXITCODE" }
$status = @($headers | Where-Object { $_ -match '^HTTP/' }) | Select-Object -Last 1
$locationLine = @($headers | Where-Object { $_ -match '^Location:\s*' }) | Select-Object -Last 1
Write-Host "HTTP status: $status"
if (-not $locationLine) { Write-Host 'Redirect location absent'; exit }
$location = ($locationLine -replace '^Location:\s*', '').Trim()
$uri = [uri]$location
Write-Host ('Redirect destination: {0}://{1}{2}' -f $uri.Scheme, $uri.Authority, $uri.AbsolutePath)
$query = [uri]::UnescapeDataString($uri.Query)
foreach ($param in @('response_type','client_id','redirect_uri','scope','state','nonce','code_challenge','code_challenge_method')) {
    Write-Host ('{0}: present={1}' -f $param, ($query -match ('(?:^\?|&)' + [regex]::Escape($param) + '=')))
}
