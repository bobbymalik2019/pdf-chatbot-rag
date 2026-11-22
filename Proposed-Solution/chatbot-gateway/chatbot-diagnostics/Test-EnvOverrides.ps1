# Do not print values: these may include secrets.
$names = @('CHATBOT_DB_HOST','CHATBOT_DB_PORT','CHATBOT_DB_NAME','CHATBOT_DB_USER','CHATBOT_DB_PASSWORD', 'OIDC_CLIENT_SECRET')
foreach ($name in $names) {
    $exists = Test-Path "Env:$name"
    Write-Host ('{0}: inherited variable present = {1}' -f $name, $exists)
}
Write-Host 'Reminder: node --env-file=.env does not override existing environment variables.'
