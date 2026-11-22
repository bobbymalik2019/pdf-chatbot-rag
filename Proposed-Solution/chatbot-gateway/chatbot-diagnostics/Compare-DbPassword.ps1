# Windows PowerShell 5.1+ compatible. Run from chatbot-gateway directory.
# This compares a password typed securely with the value Node reads from .env.
# Does not print either password or their hashes.
param([string]$ScriptPath = (Join-Path $PSScriptRoot 'diagnose.cjs'))
$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.env')) { throw 'Run this command from chatbot-gateway, where .env is located.' }
if (Test-Path Env:CHATBOT_DB_PASSWORD) {
    Write-Warning 'CHATBOT_DB_PASSWORD is set in this shell and can override .env; check its source.'
}
$raw = & node --env-file=.env $ScriptPath fingerprint
if ($LASTEXITCODE -ne 0) { throw 'Could not read Node password fingerprint.' }
$actual = $raw | ConvertFrom-Json
$secure = Read-Host 'Enter expected database password' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$sha = $null
try {
    $expected = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    $bytes = [Text.Encoding]::UTF8.GetBytes($expected)
    $sha = [Security.Cryptography.SHA256]::Create()
    $hash = $sha.ComputeHash($bytes)
    $hex = [BitConverter]::ToString($hash).Replace('-', '').ToLowerInvariant()
    # This method's length counts UTF-16 code units; Node uses Unicode code points.
    # Hash equality, rather than length, is the authoritative comparison.
    Write-Host ('Password matches the value Node loaded: {0}' -f ($hex -ceq $actual.sha256))
    if ($hex -cne $actual.sha256) { Write-Host 'Check .env quoting, # characters, whitespace, and inherited environment values.' }
} finally {
    if ($sha) { $sha.Dispose() }
    if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    Remove-Variable expected, bytes, hash, hex, secure, ptr, raw, actual -ErrorAction SilentlyContinue
}
