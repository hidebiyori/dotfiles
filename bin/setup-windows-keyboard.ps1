#requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$Restore)

# ASCII source remains compatible with Windows PowerShell 5.1.
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function ConvertTo-KeyboardMapBytes {
    param([string]$Hex)
    if ($Hex -notmatch '^(?:[0-9A-Fa-f]{8}){4,}$') { throw 'Invalid Scancode Map hex data.' }
    $bytes = [byte[]]@(for ($index = 0; $index -lt $Hex.Length; $index += 2) {
        [Convert]::ToByte($Hex.Substring($index, 2), 16)
    })
    if ([BitConverter]::ToUInt64($bytes, 0) -ne 0 -or
        [BitConverter]::ToUInt32($bytes, 8) -ne (($bytes.Length - 12) / 4) -or
        [BitConverter]::ToUInt32($bytes, $bytes.Length - 4) -ne 0) {
        throw 'Invalid Scancode Map header, count, or terminator.'
    }
    return ,$bytes
}

function ConvertTo-KeyboardState {
    param($State)
    foreach ($name in @('ScancodeMap', 'PrintScreenSnipping')) {
        if ($null -eq $State -or -not $State.PSObject.Properties[$name]) { throw 'Invalid keyboard state.' }
    }
    $map = $State.ScancodeMap
    if ($null -ne $map) {
        if ($map -isnot [string]) { throw 'Invalid Scancode Map value.' }
        ConvertTo-KeyboardMapBytes -Hex $map | Out-Null
        $map = $map.ToUpperInvariant()
    }
    $snipping = $State.PrintScreenSnipping
    if ($null -ne $snipping -and (($snipping -isnot [int] -and $snipping -isnot [long]) -or $snipping -notin @(0, 1))) {
        throw 'Invalid Print Screen snipping value.'
    }
    [pscustomobject]@{ ScancodeMap = $map; PrintScreenSnipping = $snipping }
}

function Get-WindowsKeyboardProfile {
    $path = Join-Path $PSScriptRoot '..\src\.config\dotfiles\windows-keyboard.json'
    $profile = ConvertTo-KeyboardState (Get-Content -LiteralPath $path -Raw | ConvertFrom-Json)
    if ($null -eq $profile.ScancodeMap) { throw 'The keyboard profile must contain a Scancode Map.' }
    return $profile
}

function Get-WindowsKeyboardState {
    $layout = Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Keyboard Layout'
    $keyboard = Get-ItemProperty -LiteralPath 'HKCU:\Control Panel\Keyboard'
    $map = $layout.PSObject.Properties['Scancode Map']
    $snipping = $keyboard.PSObject.Properties['PrintScreenKeyForSnippingEnabled']
    if ($map -and $map.Value -isnot [byte[]]) { throw 'Scancode Map is not a REG_BINARY value.' }
    if ($snipping -and $snipping.Value -isnot [int]) { throw 'Print Screen snipping is not a REG_DWORD value.' }
    ConvertTo-KeyboardState ([pscustomobject]@{
        ScancodeMap = $(if ($map) { [BitConverter]::ToString($map.Value).Replace('-', '') } else { $null })
        PrintScreenSnipping = $(if ($snipping) { $snipping.Value } else { $null })
    })
}

function Test-KeyboardStateEqual {
    param($Left, $Right)
    $Left.ScancodeMap -eq $Right.ScancodeMap -and $Left.PrintScreenSnipping -eq $Right.PrintScreenSnipping
}

function Set-WindowsKeyboardState {
    param($Before, $After)
    $entries = @(
        @{ Field = 'ScancodeMap'; Path = 'HKLM:\SYSTEM\CurrentControlSet\Control\Keyboard Layout'; Name = 'Scancode Map'; Type = 'Binary' }
        @{ Field = 'PrintScreenSnipping'; Path = 'HKCU:\Control Panel\Keyboard'; Name = 'PrintScreenKeyForSnippingEnabled'; Type = 'DWord' }
    )
    foreach ($entry in $entries) {
        $value = $After.($entry.Field)
        if ($Before.($entry.Field) -eq $value) { continue }
        if ($null -eq $value) {
            Remove-ItemProperty -LiteralPath $entry.Path -Name $entry.Name
        } else {
            if ($entry.Type -eq 'Binary') { $value = ConvertTo-KeyboardMapBytes -Hex $value }
            New-ItemProperty -LiteralPath $entry.Path -Name $entry.Name -PropertyType $entry.Type -Value $value -Force | Out-Null
        }
    }
}

function Save-WindowsKeyboardBackup {
    param([string]$Path, $Before, $Applied)
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $temporary = Join-Path $directory ([Guid]::NewGuid().ToString() + '.tmp')
    try {
        $contents = [pscustomobject]@{ Version = 1; Before = $Before; Applied = $Applied } | ConvertTo-Json -Depth 4
        [IO.File]::WriteAllText($temporary, $contents, (New-Object Text.UTF8Encoding($false)))
        Move-Item -LiteralPath $temporary -Destination $Path
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
    }
}

function Get-WindowsKeyboardBackup {
    param([string]$Path)
    $backup = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    foreach ($name in @('Version', 'Before', 'Applied')) {
        if ($null -eq $backup -or -not $backup.PSObject.Properties[$name]) { throw 'Invalid keyboard backup; keeping it unchanged.' }
    }
    if ($backup.Version -ne 1) { throw 'Unsupported keyboard backup version.' }
    [pscustomobject]@{
        Before = ConvertTo-KeyboardState $backup.Before
        Applied = ConvertTo-KeyboardState $backup.Applied
    }
}

function Assert-WindowsKeyboardAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Use an administrator PowerShell with the same Windows account. Use -WhatIf for a preview.'
    }
}

function Invoke-WindowsKeyboardSetup {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [switch]$Restore,
        [string]$BackupPath = (Join-Path $env:LOCALAPPDATA 'dotfiles\windows-keyboard.backup.json')
    )
    if ($env:OS -ne 'Windows_NT') { throw 'This script requires Windows.' }
    $backup = $null
    if (Test-Path -LiteralPath $BackupPath) { $backup = Get-WindowsKeyboardBackup -Path $BackupPath }
    if ($Restore -and $null -eq $backup) {
        Write-Host 'No keyboard backup found; no settings changed.'
        return
    }
    $current = Get-WindowsKeyboardState
    if ($Restore) {
        foreach ($name in @('ScancodeMap', 'PrintScreenSnipping')) {
            if (@($backup.Before.$name, $backup.Applied.$name) -notcontains $current.$name) {
                throw 'Keyboard settings changed outside this script; no restore attempted. Backup kept.'
            }
        }
        $target = $backup.Before
        $action = 'Restore the original Scancode Map and Print Screen settings'
    } else {
        $target = Get-WindowsKeyboardProfile
        if ($null -ne $backup -and -not (Test-KeyboardStateEqual $backup.Applied $target)) {
            throw 'Restore the previous keyboard profile before applying a changed profile.'
        }
        if ($null -ne $current.ScancodeMap -and $current.ScancodeMap -ne $target.ScancodeMap) {
            throw 'A different Scancode Map already exists; no settings changed.'
        }
        if (Test-KeyboardStateEqual $current $target) {
            Write-Host 'The requested keyboard registry settings are already saved. A restart may still be pending.'
            return
        }
        $action = 'Map left Windows to left Alt and enable Print Screen snipping'
    }
    if (-not $PSCmdlet.ShouldProcess('Windows keyboard registry settings', $action)) { return }
    Assert-WindowsKeyboardAdministrator
    if (-not $Restore -and $null -eq $backup) {
        Save-WindowsKeyboardBackup -Path $BackupPath -Before $current -Applied $target
    }
    Set-WindowsKeyboardState -Before $current -After $target
    if (-not (Test-KeyboardStateEqual (Get-WindowsKeyboardState) $target)) {
        throw 'Keyboard registry verification failed. Backup kept; retry or use -Restore.'
    }
    if ($Restore) { Remove-Item -LiteralPath $BackupPath }
    Write-Host 'Keyboard registry settings saved. Restart Windows manually for the key mapping to take effect.'
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        Invoke-WindowsKeyboardSetup -Restore:$Restore -WhatIf:$WhatIfPreference
    } catch {
        Write-Error $_ -ErrorAction Continue
        exit 1
    }
}
