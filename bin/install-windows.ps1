#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')]
    [string]$Distribution = 'Ubuntu',
    [switch]$AppsOnly,
    [switch]$UpgradeApps
)

# Keep this entry point self-contained: a new PC does not need Git for Windows.
# ASCII source also works with Windows PowerShell 5.1 without an encoding change.
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Get-ManagedWindowsApps {
    @(
        [pscustomobject]@{ Name = 'Codex / ChatGPT desktop'; Id = '9PLM9XGG6VKS'; Source = 'msstore' }
        [pscustomobject]@{ Name = 'Google Chrome'; Id = 'Google.Chrome'; Source = 'winget' }
        [pscustomobject]@{ Name = 'Visual Studio Code'; Id = 'Microsoft.VisualStudioCode'; Source = 'winget' }
    )
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-WindowsHost {
    param([switch]$OnlyApps)
    if ($env:OS -ne 'Windows_NT' -or [Environment]::OSVersion.Version.Build -lt 22000) {
        throw 'This entry point requires Windows 11.'
    }
    if (Test-IsAdministrator) {
        throw 'Use a non-administrator PowerShell for your usual Windows account. Only WSL installation requests elevation.'
    }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw 'WinGet is missing. Install/update App Installer from Microsoft Store, reopen PowerShell, and retry.'
    }
    if (-not $OnlyApps -and -not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        throw 'wsl.exe is missing. Check Windows Update before retrying.'
    }
}

function Invoke-WingetNative {
    param([string[]]$CommandArguments)
    & winget.exe @CommandArguments | Out-Host
    # WinGet HRESULTs appear as signed integers in Windows PowerShell.
    [long]$LASTEXITCODE -band 4294967295L
}

function Install-WindowsApps {
    param([switch]$Upgrade)
    foreach ($app in (Get-ManagedWindowsApps)) {
        Write-Host ("Checking {0} ({1})" -f $app.Name, $app.Id)
        $selection = @('--id', $app.Id, '--exact', '--source', $app.Source)
        $queryArguments = @('list') + $selection + @('--accept-source-agreements', '--disable-interactivity')
        $queryExit = Invoke-WingetNative -CommandArguments $queryArguments
        if ($queryExit -eq 0) {
            if (-not $Upgrade) {
                Write-Host 'Already installed; keeping the current installation.'
                continue
            }
            $action = 'upgrade'
        } elseif ($queryExit -eq 2316632084L) { # APPINSTALLER_CLI_ERROR_NO_APPLICATIONS_FOUND
            $action = 'install'
        } else {
            throw ("WinGet could not determine whether {0} is installed (exit {1}); no install attempted." -f $app.Id, $queryExit)
        }
        $installArguments = @($action) + $selection + @(
            '--accept-source-agreements', '--accept-package-agreements', '--disable-interactivity', '--silent'
        )
        if ($action -eq 'install') {
            $installArguments += '--no-upgrade'
        }
        $result = Invoke-WingetNative -CommandArguments $installArguments
        if ($result -ne 0) {
            # Official HRESULTs: microsoft/winget-cli, AppInstallerErrors.h.
            # A concurrent install or an up-to-date package is a normal rerun.
            $noChangeResults = @(
                2316632107L, # APPINSTALLER_CLI_ERROR_UPDATE_NOT_APPLICABLE
                2316632143L, # APPINSTALLER_CLI_ERROR_UPGRADE_VERSION_NOT_NEWER
                2316632161L  # APPINSTALLER_CLI_ERROR_PACKAGE_ALREADY_INSTALLED
            )
            if ($result -in $noChangeResults) {
                $confirmedExit = Invoke-WingetNative -CommandArguments $queryArguments
                if ($confirmedExit -eq 0) {
                    Write-Host 'Already installed or no newer version; keeping the confirmed installation.'
                    continue
                }
                throw ("WinGet reported no change for {0}, but its installation could not be confirmed (exit {1})." -f $app.Id, $confirmedExit)
            }
            throw ("WinGet {0} failed for {1} (exit {2})." -f $action, $app.Id, $result)
        }
    }
}

function Find-WindowsCode {
    $command = Get-Command code.cmd -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($directory in @($env:LOCALAPPDATA, $env:ProgramFiles)) {
        if (-not $directory) { continue }
        $relative = 'Microsoft VS Code\bin\code.cmd'
        if ($directory -eq $env:LOCALAPPDATA) { $relative = 'Programs\' + $relative }
        $candidate = Join-Path $directory $relative
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw 'VS Code CLI was not found. Reopen PowerShell after installation and retry.'
}

function Install-WslExtension {
    $codeCommand = Find-WindowsCode
    $extensions = @(& $codeCommand --list-extensions)
    if ($LASTEXITCODE -ne 0) { throw 'Could not list VS Code extensions.' }
    if ($extensions -contains 'ms-vscode-remote.remote-wsl') { return }
    & $codeCommand --install-extension ms-vscode-remote.remote-wsl | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the VS Code WSL extension.' }
}

function Get-WslDistribution {
    param([string]$Name)
    # Per-user WSL registrations let us inspect a clean Windows installation
    # without invoking wsl.exe before its optional components have been enabled.
    $registryRoot = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
    if (-not (Test-Path -LiteralPath $registryRoot)) { return $null }
    foreach ($key in (Get-ChildItem -LiteralPath $registryRoot)) {
        $entry = Get-ItemProperty -LiteralPath $key.PSPath
        if ($entry.PSObject.Properties['DistributionName'] -and $entry.DistributionName -eq $Name) {
            if (-not $entry.PSObject.Properties['Version']) {
                throw 'The existing WSL registration has no version. Check WSL before retrying.'
            }
            return [pscustomobject]@{ Name = $entry.DistributionName; Version = [int]$entry.Version }
        }
    }
    return $null
}

function Install-WslDistribution {
    param([string]$Name)
    Write-Host 'Windows will request administrator approval for WSL installation.'
    Write-Host 'Use the same Windows account. Do not switch to another administrator account.'
    $wslCommand = (Get-Command wsl.exe -ErrorAction Stop).Source
    $process = Start-Process -FilePath $wslCommand -ArgumentList @(
        '--install', '--distribution', $Name, '--no-launch'
    ) -Verb RunAs -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) {
        throw ("WSL installation failed (exit {0})." -f $process.ExitCode)
    }
    Write-Host 'WSL setup is pending: restart Windows if requested, open the distribution from Start,'
    Write-Host 'create your Linux user/password, then run this script again.'
    Write-Host 'If installation was deferred until reboot, rerun this script to finish installing the distribution.'
}

function Invoke-WslCapture {
    param([string[]]$CommandArguments)
    $previousEncoding = [Console]::OutputEncoding
    try {
        # Linux command output is UTF8, including Windows user paths in wslpath.
        [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
        $captured = @(& wsl.exe @CommandArguments)
        if ($LASTEXITCODE -ne 0) {
            throw ("WSL command failed (exit {0}). Resolve the error/restart request before retrying." -f $LASTEXITCODE)
        }
        (($captured -join "`n") -replace "`0", '').Trim()
    } finally {
        [Console]::OutputEncoding = $previousEncoding
    }
}

function Get-LinuxBootstrapScript {
    @'
set +x
set -euo pipefail
linux_user_id="$(id -u)"
if [ "${linux_user_id}" = 0 ]; then
  echo 'Run the setup as your regular WSL user, not root.' >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y ca-certificates git
fi
repository="${HOME}/git/dotfiles"
mkdir -p "${HOME}/git"
if [ -e "${repository}" ]; then
  if [ ! -d "${repository}/.git" ] && [ ! -f "${repository}/.git" ]; then
    echo '~/git/dotfiles already exists but is not a Git checkout; keeping it unchanged.' >&2
    exit 1
  fi
  checkout_status="$(git -C "${repository}" status --porcelain)"
  if [ -n "${checkout_status}" ]; then
    echo '~/git/dotfiles has local changes; commit or preserve them before retrying.' >&2
    exit 1
  fi
  if [ "$(git -C "${repository}" branch --show-current)" != main ]; then
    echo 'Switch ~/git/dotfiles to main after preserving your work, then retry.' >&2
    exit 1
  fi
  origin="$(git -C "${repository}" config --get remote.origin.url || true)"
  if [[ "${origin}" == https://* ]]; then
    public_origin="${origin%%[?#]*}"
    public_origin="${public_origin#https://}"
    public_origin="https://${public_origin##*@}"
    if [ "${public_origin}" != https://github.com/hidebiyori/dotfiles.git ]; then
      echo '~/git/dotfiles has a different origin; keeping it unchanged.' >&2
      exit 1
    fi
    if [ "${origin}" != "${public_origin}" ]; then
      git -C "${repository}" remote set-url origin "${public_origin}"
    fi
  elif [[ "${origin}" != git@github.com:hidebiyori/dotfiles.git &&
          "${origin}" != ssh://git@github.com/hidebiyori/dotfiles.git ]]; then
    echo '~/git/dotfiles has an unsupported origin; check it before retrying.' >&2
    exit 1
  fi
  git -C "${repository}" pull --ff-only origin main
else
  git clone https://github.com/hidebiyori/dotfiles.git "${repository}"
fi
cd "${repository}"
bash bin/install.sh
'@
}

function Invoke-ConsoleNative {
    param([string]$FilePath, [string[]]$CommandArguments)
    # Start-Process bypasses PowerShell's success stream. Even when the caller
    # captures a setup result, stdout/stderr and keyboard input stay connected
    # to this console, including prompts that do not end with a newline.
    $process = Start-Process -FilePath $FilePath -ArgumentList $CommandArguments -NoNewWindow -Wait -PassThru
    try {
        if ($null -eq $process.ExitCode) { throw 'Could not determine the console process exit code.' }
        $process.ExitCode
    } finally {
        $process.Dispose()
    }
}

function Invoke-WslBootstrapNative {
    param([string]$Name, [string]$LinuxPath)
    Write-Host 'Running Linux setup in this console. Respond to sudo/apt prompts here; downloads may take time.'
    $wslCommand = (Get-Command wsl.exe -ErrorAction Stop).Source
    # Start-Process joins ArgumentList; quote the translated path for spaces.
    $quotedPath = '"{0}"' -f $LinuxPath.Replace('"', '\"')
    $exitCode = Invoke-ConsoleNative -FilePath $wslCommand -CommandArguments @(
        '--distribution', $Name, '--exec', 'bash', '--noprofile', '--norc', $quotedPath
    )
    if ($exitCode -ne 0) { throw ("Linux setup failed (exit {0})." -f $exitCode) }
}

function Install-WslDotfiles {
    param([string]$Name)
    $temporaryScript = Join-Path ([IO.Path]::GetTempPath()) ('dotfiles-wsl-' + [guid]::NewGuid().ToString('N') + '.sh')
    try {
        $body = (Get-LinuxBootstrapScript) -replace "`r", ''
        [IO.File]::WriteAllText($temporaryScript, $body + "`n", (New-Object Text.UTF8Encoding($false)))
        $linuxPath = Invoke-WslCapture -CommandArguments @('--distribution', $Name, '--exec', 'wslpath', '-a', '-u', $temporaryScript)
        if (-not $linuxPath.StartsWith('/')) { throw 'Could not translate the temporary script path for WSL.' }
        Invoke-WslBootstrapNative -Name $Name -LinuxPath $linuxPath
    } finally {
        if (Test-Path -LiteralPath $temporaryScript) { Remove-Item -LiteralPath $temporaryScript }
    }
}

function Initialize-Wsl {
    param([string]$Name)
    $existing = Get-WslDistribution -Name $Name
    if (-not $existing) {
        Install-WslDistribution -Name $Name
        return $false
    }
    if ($existing.Version -ne 2) {
        throw 'The selected distribution uses WSL1. Back up your data and explicitly convert it to WSL2 before retrying.'
    }
    $userId = Invoke-WslCapture -CommandArguments @('--distribution', $existing.Name, '--exec', 'id', '-u')
    if ($userId -eq '0') {
        Write-Host ("Open {0} from Start (or run wsl --distribution {0}), create/select a regular Linux user, exit, and retry." -f $existing.Name)
        return $false
    }
    if ($userId -notmatch '^\d+$') { throw 'Could not determine the default Linux user.' }
    Install-WslDotfiles -Name $existing.Name
    return $true
}

function Invoke-WindowsSetup {
    param([string]$Name, [switch]$OnlyApps, [switch]$Upgrade)
    Assert-WindowsHost -OnlyApps:$OnlyApps
    Install-WindowsApps -Upgrade:$Upgrade
    Install-WslExtension
    if ($OnlyApps) { return $true }
    Initialize-Wsl -Name $Name
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        $ready = Invoke-WindowsSetup -Name $Distribution -OnlyApps:$AppsOnly -Upgrade:$UpgradeApps
        if (-not $ready) {
            Write-Host 'Setup is not complete yet. Follow the instructions above, then rerun the same command.'
            exit 2
        }
        Write-Host 'Success: requested Windows / WSL setup finished. Service sign-ins are separate.'
    } catch {
        Write-Error $_ -ErrorAction Continue
        exit 1
    }
}
