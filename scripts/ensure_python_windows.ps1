$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Get-UsablePython {
    $commands = @()
    $launcher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if ($launcher) { $commands += [pscustomobject]@{ Path = $launcher.Source; Prefix = @('-3') } }
    foreach ($name in @('python.exe', 'python3.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $commands += [pscustomobject]@{ Path = $command.Source; Prefix = @() } }
    }

    foreach ($candidate in $commands) {
        try {
            $version = & $candidate.Path @($candidate.Prefix) -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
            if ($LASTEXITCODE -eq 0 -and $version -match '^([0-9]+)\.([0-9]+)$') {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                    $executable = & $candidate.Path @($candidate.Prefix) -c 'import sys; print(sys.executable)' 2>$null
                    if ($LASTEXITCODE -eq 0 -and $executable) { return $executable.Trim() }
                }
            }
        } catch { }
    }
    return $null
}

$python = Get-UsablePython
if (-not $python) {
    Write-Host 'Python 3.10+ is required. The installer will use the official Python package in Windows Package Manager (winget).' -ForegroundColor Yellow
    $winget = Get-Command 'winget.exe' -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host 'winget was not found. Install Python 3.12 from https://www.python.org/downloads/windows/ and run start.bat again.' -ForegroundColor Red
        exit 1
    }
    $answer = Read-Host 'Install Python 3.12 for your Windows user now? [y/N]'
    if ($answer -notmatch '^(y|yes)$') { Write-Host 'Cancelled.'; exit 1 }
    & $winget.Source install --id Python.Python.3.12 --exact --scope user --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "winget failed with exit code $LASTEXITCODE" }
    $python = Get-UsablePython
    if (-not $python) {
        $pythonDirs = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Programs\Python') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
        foreach ($dir in $pythonDirs) {
            $candidate = Join-Path $dir.FullName 'python.exe'
            if (Test-Path $candidate) { $python = $candidate; break }
        }
    }
}

if (-not $python) {
    Write-Host 'Python installation was not detected. Close and reopen the terminal, or install Python manually.' -ForegroundColor Red
    exit 1
}

& $python -c 'import tkinter' 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tkinter is not available in this Python installation: $python" -ForegroundColor Red
    Write-Host 'Repair/reinstall Python from python.org and make sure Tcl/Tk support is included.'
    exit 1
}

$appDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $appDir
& $python (Join-Path $appDir 'gui.py')
exit $LASTEXITCODE
