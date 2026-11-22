# Recreate the *empty scaffold* of the PDF Ingestion Service, not its implementations.
# Generated from the sanitized project archive. Does not modify the existing RAG service.
# Usage: .\setup-pdf-ingestion-service.ps1 [-DestinationParent <path>] [-SkipInstall]
# Place the accompanying uv.lock beside this script for the original locked dependencies.
[CmdletBinding()]
param(
    [string]$DestinationParent = $PSScriptRoot,
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$projectName = 'pdf-ingestion-service'
$parent = [System.IO.Path]::GetFullPath($DestinationParent)
if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    throw "Destination parent folder not found: $parent"
}
$target = Join-Path $parent $projectName
if (Test-Path -LiteralPath $target) {
    throw "Refusing to overwrite existing folder: $target"
}

# Confirm prerequisites before creating any folders.
if (-not $SkipInstall -and -not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was not found in PATH. Install uv or run with -SkipInstall."
}

# Exact layout of the uploaded sanitized scaffold, including empty placeholder files.
$emptyFiles = @(
    'fixes.txt'
    'README.md'
    'scripts/test_ollama_rag.py'
    'scripts/test_rag_answer.py'
    'src/pdf_ingestion_service/dependencies.py'
    'src/pdf_ingestion_service/main.py'
    'src/pdf_ingestion_service/__init__.py'
    'src/pdf_ingestion_service/api/document_files.py'
    'src/pdf_ingestion_service/api/ingestion.py'
    'src/pdf_ingestion_service/api/knowledge_projects.py'
    'src/pdf_ingestion_service/api/rag_answer.py'
    'src/pdf_ingestion_service/api/routes.py'
    'src/pdf_ingestion_service/api/__init__.py'
    'src/pdf_ingestion_service/application/ingestion_service.py'
    'src/pdf_ingestion_service/application/rag_context_builder.py'
    'src/pdf_ingestion_service/application/rag_prompt_builder.py'
    'src/pdf_ingestion_service/application/__init__.py'
    'src/pdf_ingestion_service/config/logging_config.py'
    'src/pdf_ingestion_service/config/settings.py'
    'src/pdf_ingestion_service/config/__init__.py'
    'src/pdf_ingestion_service/embeddings/embedding_generator.py'
    'src/pdf_ingestion_service/embeddings/ollama_embedding_generator.py'
    'src/pdf_ingestion_service/generation/ollama_text_generator.py'
    'src/pdf_ingestion_service/generation/__init__.py'
    'src/pdf_ingestion_service/infrastructure/docker-compose.yml'
    'src/pdf_ingestion_service/infrastructure/__init__.py'
    'src/pdf_ingestion_service/llm/ollama_llm_client.py'
    'src/pdf_ingestion_service/llm/__init__.py'
    'src/pdf_ingestion_service/models/chunk.py'
    'src/pdf_ingestion_service/models/document.py'
    'src/pdf_ingestion_service/models/knowledge_project.py'
    'src/pdf_ingestion_service/models/rag_answer.py'
    'src/pdf_ingestion_service/models/rag_answer_request.py'
    'src/pdf_ingestion_service/models/rag_context.py'
    'src/pdf_ingestion_service/models/semantic_search.py'
    'src/pdf_ingestion_service/models/__init__.py'
    'src/pdf_ingestion_service/persistence/app_user_repository.py'
    'src/pdf_ingestion_service/persistence/database.py'
    'src/pdf_ingestion_service/persistence/document_repository.py'
    'src/pdf_ingestion_service/persistence/knowledge_project_repository.py'
    'src/pdf_ingestion_service/persistence/semantic_search_repository.py'
    'src/pdf_ingestion_service/processing/document_chunker.py'
    'src/pdf_ingestion_service/processing/text_normalizer.py'
    'src/pdf_ingestion_service/processing/__init__.py'
    'src/pdf_ingestion_service/readers/content_reader.py'
    'src/pdf_ingestion_service/readers/pdf_content_reader.py'
    'src/pdf_ingestion_service/readers/__init__.py'
    'src/pdf_ingestion_service/security/current_user.py'
    'src/pdf_ingestion_service/security/jwt_auth.py'
    'src/pdf_ingestion_service/security/__init__.py'
    'src/pdf_ingestion_service/services/document_service.py'
    'src/pdf_ingestion_service/services/knowledge_project_service.py'
    'src/pdf_ingestion_service/services/rag_answer_service.py'
    'src/pdf_ingestion_service/services/semantic_search_service.py'
    'tests/test_document_chunker.py'
    'tests/test_document_repository.py'
    'tests/test_knowledge_projects_api.py'
    'tests/test_ollama_embedding_generator.py'
    'tests/test_ollama_llm_client.py'
    'tests/test_rag_answer_service.py'
    'tests/test_rag_context_builder.py'
    'tests/test_rag_prompt_builder.py'
    'tests/test_text_normalizer.py'
    'tests/__init__.py'
)

# Write metadata and blank source/test/config placeholders.
New-Item -ItemType Directory -Path $target -ErrorAction Stop | Out-Null
foreach ($relativePath in $emptyFiles) {
    $absolute = Join-Path $target ($relativePath -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    $directory = Split-Path -Path $absolute -Parent
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    [System.IO.File]::WriteAllBytes($absolute, [byte[]]::new(0))
}

# Manifest preserved from the uploaded original project.
$pyproject = @'
[project]
name = "pdf-ingestion-service"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
authors = [
    { name = "bobbymalik2019", email = "writetobobby@yahoo.com" }
]
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.162.4",
    "httpx>=0.28.1",
    "pgvector>=0.5.1",
    "psycopg>=3.3.9",
    "pydantic-settings>=2.16.2",
    "pyjwt[crypto]>=2.10,<3",
    "pymupdf>=2.1",
    "python-multipart>=0.0.33",
    "uvicorn[standard]>=0.54.0",
]

[project.scripts]
pdf-ingestion-service = "pdf_ingestion_service:main"

[build-system]
requires = ["uv_build>=0.12.5,<0.13.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "pytest>=9.2.0",
    "requests>=2.34.2",
]
'@
$gitignore = @'
# Python-generated files
__pycache__/
*.py[oc]
build/
dist/
wheels/
*.egg-info

# Virtual environments
.venv

.env
'@
$pythonVersion = @'
3.13
'@
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $target 'pyproject.toml'), $pyproject + "`n", $utf8)
[System.IO.File]::WriteAllText((Join-Path $target '.gitignore'), $gitignore + "`n", $utf8)
[System.IO.File]::WriteAllText((Join-Path $target '.python-version'), $pythonVersion + "`n", $utf8)

# Prefer the exact original lockfile when supplied alongside the setup script.
$lockSource = Join-Path $PSScriptRoot 'uv.lock'
$hasOriginalLock = Test-Path -LiteralPath $lockSource -PathType Leaf
if ($hasOriginalLock) {
    Copy-Item -LiteralPath $lockSource -Destination (Join-Path $target 'uv.lock')
    Write-Host 'Copied original uv.lock (locked dependency versions).' -ForegroundColor Cyan
} else {
    Write-Warning 'Original uv.lock not found beside script; uv will resolve dependencies afresh.'
}

if (-not $SkipInstall) {
    Push-Location $target
    try {
        if ($hasOriginalLock) {
            & uv sync --locked
        } else {
            & uv sync
        }
        if ($LASTEXITCODE -ne 0) { throw "uv sync failed (exit code $LASTEXITCODE)." }
        & uv run --no-sync python -c 'import fastapi, psycopg, fitz, pgvector, jwt; print("Dependencies import OK")'
        if ($LASTEXITCODE -ne 0) { throw "Dependency import verification failed (exit code $LASTEXITCODE)." }
    } finally {
        Pop-Location
    }
} else {
    Write-Host 'Skipped dependency installation, as requested.' -ForegroundColor Yellow
}

$actual = @(Get-ChildItem -LiteralPath $target -Recurse -File -Force |
    Where-Object { $_.FullName -notmatch '[\/](\.venv|__pycache__)[\/]' }).Count
Write-Host "Created scaffold: $target" -ForegroundColor Green
Write-Host "Scaffold files present (excluding virtual environment): $actual" -ForegroundColor Green
Write-Warning 'Files under src/, tests/, scripts/ and docker-compose.yml are intentionally EMPTY. This is not a runnable RAG API.'
Write-Warning 'Original pyproject.toml specifies psycopg[binary]. On your Windows setup this binary may be blocked; consider replacing with psycopg before installation if needed.'
