# Included by test_windows.ps1; all registry access is stubbed.
. (Join-Path $PSScriptRoot '..\bin\setup-windows-keyboard.ps1')

function Initialize-KeyboardMocks {
    $script:KeyboardBackup = Join-Path $script:KeyboardTestRoot ([Guid]::NewGuid().ToString() + '.json')
    $script:KeyboardRegistry = [pscustomobject]@{ ScancodeMap = $null; PrintScreenSnipping = $null }
    $script:FailKeyboardSnipping = $false
    Set-Mock 'Assert-WindowsKeyboardAdministrator' {}
    Set-Mock 'Get-ItemProperty' {
        param([string]$LiteralPath)
        $values = @{}
        if ($LiteralPath -eq 'HKLM:\SYSTEM\CurrentControlSet\Control\Keyboard Layout') {
            if ($null -ne $script:KeyboardRegistry.ScancodeMap) {
                $values['Scancode Map'] = ConvertTo-KeyboardMapBytes $script:KeyboardRegistry.ScancodeMap
            }
        } elseif ($LiteralPath -eq 'HKCU:\Control Panel\Keyboard') {
            if ($null -ne $script:KeyboardRegistry.PrintScreenSnipping) {
                $values['PrintScreenKeyForSnippingEnabled'] = $script:KeyboardRegistry.PrintScreenSnipping
            }
        } else { throw 'Unexpected registry read.' }
        [pscustomobject]$values
    }
    Set-Mock 'New-ItemProperty' {
        param([string]$LiteralPath, [string]$Name, [string]$PropertyType, $Value, [switch]$Force)
        Assert-True $Force 'Expected an explicit registry value update.'
        if ($LiteralPath -eq 'HKLM:\SYSTEM\CurrentControlSet\Control\Keyboard Layout' -and $Name -eq 'Scancode Map' -and $PropertyType -eq 'Binary') {
            Assert-True ($Value -is [byte[]]) 'Scancode Map must be REG_BINARY.'
            $script:KeyboardRegistry.ScancodeMap = [BitConverter]::ToString($Value).Replace('-', '')
        } elseif ($LiteralPath -eq 'HKCU:\Control Panel\Keyboard' -and $Name -eq 'PrintScreenKeyForSnippingEnabled' -and $PropertyType -eq 'DWord') {
            if ($script:FailKeyboardSnipping) { throw 'Synthetic Print Screen failure.' }
            $script:KeyboardRegistry.PrintScreenSnipping = [int]$Value
        } else { throw 'Unexpected registry write.' }
        $script:Calls.Add('set:' + $Name)
    }
    Set-Mock 'Remove-ItemProperty' {
        param([string]$LiteralPath, [string]$Name)
        if ($LiteralPath -eq 'HKLM:\SYSTEM\CurrentControlSet\Control\Keyboard Layout' -and $Name -eq 'Scancode Map') {
            $script:KeyboardRegistry.ScancodeMap = $null
        } elseif ($LiteralPath -eq 'HKCU:\Control Panel\Keyboard' -and $Name -eq 'PrintScreenKeyForSnippingEnabled') {
            $script:KeyboardRegistry.PrintScreenSnipping = $null
        } else { throw 'Unexpected registry removal.' }
        $script:Calls.Add('remove:' + $Name)
    }
}

$script:KeyboardTestRoot = Join-Path ([IO.Path]::GetTempPath()) ('dotfiles-keyboard-' + [Guid]::NewGuid().ToString())
try {
    Test-Case 'Keyboard profile maps only left Windows to left Alt' {
        $profile = Get-WindowsKeyboardProfile
        $bytes = ConvertTo-KeyboardMapBytes $profile.ScancodeMap
        Assert-True ($bytes.Length -eq 20 -and [BitConverter]::ToUInt32($bytes, 8) -eq 2) 'Expected one mapping plus the terminator.'
        Assert-True ([BitConverter]::ToUInt16($bytes, 12) -eq 0x0038) 'Expected left Alt as the destination.'
        Assert-True ([BitConverter]::ToUInt16($bytes, 14) -eq 0xE05B) 'Expected left Windows as the source.'
        Assert-True ($profile.PrintScreenSnipping -eq 1) 'Expected Print Screen snipping.'
        Assert-Throws { ConvertTo-KeyboardMapBytes 'not-hex' } '*Invalid Scancode Map*'
        Assert-Throws { ConvertTo-KeyboardMapBytes '00000000000000000300000038005BE000000000' } '*Invalid Scancode Map*'
    }

    Test-Case 'Keyboard apply backs up absent values and repeated apply preserves the backup' {
        Initialize-KeyboardMocks
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup
        Assert-True (Test-KeyboardStateEqual $script:KeyboardRegistry (Get-WindowsKeyboardProfile)) 'Requested settings were not saved.'
        $original = Get-Content -LiteralPath $script:KeyboardBackup -Raw
        $backup = Get-WindowsKeyboardBackup $script:KeyboardBackup
        Assert-True ($null -eq $backup.Before.ScancodeMap -and $null -eq $backup.Before.PrintScreenSnipping) 'Original absence must be recorded.'
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup
        Assert-True ($script:Calls.Count -eq 2) 'Repeated apply must not write registry values again.'
        Assert-True ((Get-Content -LiteralPath $script:KeyboardBackup -Raw) -ceq $original) 'Repeated apply replaced the original backup.'
    }

    Test-Case 'Keyboard restore removes values that were originally absent and is repeatable' {
        Initialize-KeyboardMocks
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup -Restore
        Assert-True ($null -eq $script:KeyboardRegistry.ScancodeMap -and $null -eq $script:KeyboardRegistry.PrintScreenSnipping) 'Originally absent values were not removed.'
        Assert-True (-not (Test-Path -LiteralPath $script:KeyboardBackup)) 'Verified restore must remove the backup.'
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup -Restore
        Assert-True ($script:Calls.Count -eq 4) 'Repeated restore must not change registry values.'
    }

    Test-Case 'Keyboard restore preserves a preexisting matching map and disabled Print Screen setting' {
        Initialize-KeyboardMocks
        $script:KeyboardRegistry.ScancodeMap = (Get-WindowsKeyboardProfile).ScancodeMap
        $script:KeyboardRegistry.PrintScreenSnipping = 0
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup -Restore
        Assert-True ($script:KeyboardRegistry.ScancodeMap -eq (Get-WindowsKeyboardProfile).ScancodeMap) 'Preexisting matching map was removed.'
        Assert-True ($script:KeyboardRegistry.PrintScreenSnipping -eq 0) 'Explicit zero was confused with an absent value.'
        Assert-True (($script:Calls -join ',') -eq 'set:PrintScreenKeyForSnippingEnabled,set:PrintScreenKeyForSnippingEnabled') 'Only the Print Screen setting should change.'
    }

    Test-Case 'A conflicting Scancode Map stops before changing either setting or saving a backup' {
        Initialize-KeyboardMocks
        $script:KeyboardRegistry.ScancodeMap = '0000000000000000020000001D003A0000000000'
        Assert-Throws { Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup } '*different Scancode Map*'
        Assert-True ($script:Calls.Count -eq 0 -and -not (Test-Path -LiteralPath $script:KeyboardBackup)) 'Conflict must not write settings or a backup.'
    }

    Test-Case 'Keyboard preview needs no administrator and does not create a backup' {
        Initialize-KeyboardMocks
        Set-Mock 'Assert-WindowsKeyboardAdministrator' { throw 'Preview must not request administrator access.' }
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup -WhatIf
        Assert-True ($script:Calls.Count -eq 0 -and -not (Test-Path -LiteralPath $script:KeyboardBackup)) 'Preview changed persistent state.'
    }

    Test-Case 'An unexpected registry value type is preserved without a backup or write' {
        Initialize-KeyboardMocks
        $script:KeyboardRegistry.PrintScreenSnipping = [long]0
        Assert-Throws { Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup } '*not a REG_DWORD*'
        Assert-True ($script:Calls.Count -eq 0 -and -not (Test-Path -LiteralPath $script:KeyboardBackup)) 'An unexpected value type was overwritten.'
    }

    Test-Case 'Keyboard apply without administrator access stops before backup and writes' {
        Initialize-KeyboardMocks
        Set-Mock 'Assert-WindowsKeyboardAdministrator' { throw 'Administrator required.' }
        Assert-Throws { Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup } '*Administrator required*'
        Assert-True ($script:Calls.Count -eq 0 -and -not (Test-Path -LiteralPath $script:KeyboardBackup)) 'Non-administrator apply changed persistent state.'
    }

    Test-Case 'Restore preserves externally modified registry settings and its backup' {
        Initialize-KeyboardMocks
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup
        $script:KeyboardRegistry.PrintScreenSnipping = 0
        Assert-Throws { Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup -Restore } '*changed outside this script*'
        Assert-True ($script:Calls.Count -eq 2 -and (Test-Path -LiteralPath $script:KeyboardBackup)) 'Restore overwrote an external change or discarded its backup.'
    }

    Test-Case 'A partial keyboard apply keeps a usable backup for restore' {
        Initialize-KeyboardMocks
        $script:FailKeyboardSnipping = $true
        Assert-Throws { Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup } '*Synthetic Print Screen failure*'
        Assert-True ($null -ne $script:KeyboardRegistry.ScancodeMap -and (Test-Path -LiteralPath $script:KeyboardBackup)) 'Partial apply lost its backup.'
        Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup -Restore
        Assert-True ($null -eq $script:KeyboardRegistry.ScancodeMap -and $null -eq $script:KeyboardRegistry.PrintScreenSnipping) 'Partial apply could not be restored.'
    }

    Test-Case 'Backup failure stops before any keyboard registry write' {
        Initialize-KeyboardMocks
        Set-Mock 'Save-WindowsKeyboardBackup' { throw 'Synthetic backup failure.' }
        Assert-Throws { Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup } '*Synthetic backup failure*'
        Assert-True ($script:Calls.Count -eq 0) 'Settings changed without a backup.'
    }

    Test-Case 'Unreadable registry and malformed backup stop before writes' {
        Initialize-KeyboardMocks
        New-Item -ItemType Directory -Path $script:KeyboardTestRoot -Force | Out-Null
        Set-Content -LiteralPath $script:KeyboardBackup -Value '{"Version":1}'
        Assert-Throws { Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup } '*Invalid keyboard backup*'
        Remove-Item -LiteralPath $script:KeyboardBackup
        Set-Mock 'Get-ItemProperty' { throw 'Synthetic registry read failure.' }
        Assert-Throws { Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup } '*Synthetic registry read failure*'
        Assert-True ($script:Calls.Count -eq 0 -and -not (Test-Path -LiteralPath $script:KeyboardBackup)) 'Invalid input changed persistent state.'
    }

    Test-Case 'Registry verification failure keeps the original keyboard backup' {
        Initialize-KeyboardMocks
        Set-Mock 'Set-WindowsKeyboardState' {}
        Assert-Throws { Invoke-WindowsKeyboardSetup -BackupPath $script:KeyboardBackup } '*verification failed*'
        Assert-True (Test-Path -LiteralPath $script:KeyboardBackup) 'Failed verification discarded the backup.'
    }
} finally {
    if (Microsoft.PowerShell.Management\Test-Path -LiteralPath $script:KeyboardTestRoot) {
        Microsoft.PowerShell.Management\Remove-Item -LiteralPath $script:KeyboardTestRoot -Recurse -Force
    }
}
