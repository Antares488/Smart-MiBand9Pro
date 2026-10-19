$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3 -m venv .venv-build
if ($LASTEXITCODE -ne 0) { throw 'venv failed' }
$python = Join-Path $PSScriptRoot '.venv-build\Scripts\python.exe'
& $python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $python run_tests.py
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $python -m PyInstaller --clean --noconfirm SmartMiBand.spec
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Write-Host 'Ready: dist\SmartMiBand.exe'
