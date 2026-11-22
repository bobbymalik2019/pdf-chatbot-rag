$ErrorActionPreference = "Stop"

$ProjectName = "chat-history-service"

Write-Host "Initializing Chat History Service..." -ForegroundColor Cyan

# Verify uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed or not available in PATH."
}

# Avoid overwriting an existing project
if (Test-Path $ProjectName) {
    throw "Directory '$ProjectName' already exists."
}

# Initialize Python project with src layout
uv init --package $ProjectName
if ($LASTEXITCODE -ne 0) {
    throw "Project initialization failed."
}

Set-Location $ProjectName

# Add application dependencies
uv add fastapi uvicorn pydantic-settings psycopg
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}

# Add development dependencies
uv add --dev pytest httpx requests
if ($LASTEXITCODE -ne 0) {
    throw "Development dependency installation failed."
}

# Create application directories
$Directories = @(
    "src/chat_history_service/api",
    "src/chat_history_service/config",
    "src/chat_history_service/models",
    "src/chat_history_service/repositories",
    "src/chat_history_service/services",
    "tests"
)

foreach ($Directory in $Directories) {
    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
}

# Add Python package markers
foreach ($Directory in $Directories) {
    if ($Directory -ne "tests") {
        New-Item -ItemType File -Force `
            -Path "$Directory/__init__.py" | Out-Null
    }
}

# Verify installation
uv run python -c "import fastapi, psycopg; print('Dependencies OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Dependency verification failed."
}

Write-Host "Chat History Service project created successfully!" -ForegroundColor Green