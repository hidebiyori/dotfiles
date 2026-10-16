#requires -Version 5.1
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\bin\install-windows.ps1')

$script:Passed = 0
$script:OriginalFunctions = @{}
$script:Calls = New-Object 'System.Collections.Generic.List[string]'

function Assert-True {
    param($Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Assert-Throws {
    param([scriptblock]$Body, [string]$Pattern)
    $caught = $null
    try { & $Body | Out-Null } catch { $caught = $_.Exception.Message }
    Assert-True ($null -ne $caught -and $caught -like $Pattern) ("Expected error matching: {0}; got: {1}" -f $Pattern, $caught)
}

function Set-Mock {
    param([string]$Name, [scriptblock]$Body)
    if (-not $script:OriginalFunctions.ContainsKey($Name)) {
        $command = Get-Item -LiteralPath ("Function:{0}" -f $Name) -ErrorAction SilentlyContinue
        $script:OriginalFunctions[$Name] = $(if ($command) { $command.ScriptBlock } else { $null })
    }
    Set-Item -Path ("Function:script:{0}" -f $Name) -Value $Body
}

function Test-Case {
    param([string]$Name, [scriptblock]$Body)
    $script:Calls.Clear()
    try {
        & $Body
        $script:Passed++
        Write-Host ("PASS {0}" -f $Name)
    } finally {
        foreach ($functionName in @($script:OriginalFunctions.Keys)) {
            $original = $script:OriginalFunctions[$functionName]
            if ($null -eq $original) {
                Remove-Item -Path ("Function:script:{0}" -f $functionName)
            } else {
                Set-Item -Path ("Function:script:{0}" -f $functionName) -Value $original
            }
        }
        $script:OriginalFunctions.Clear()
    }
}

Test-Case 'Exact desktop package IDs, without Codex CLI' {
    $apps = @(Get-ManagedWindowsApps)
    Assert-True ($apps.Count -eq 3) 'Expected three managed apps.'
    Assert-True ($apps[0].Id -eq '9PLM9XGG6VKS' -and $apps[0].Source -eq 'msstore') 'Expected official desktop Store package.'
    Assert-True ($apps[1].Id -eq 'Google.Chrome' -and $apps[2].Id -eq 'Microsoft.VisualStudioCode') 'Unexpected package IDs.'
}

Test-Case 'Signed WinGet HRESULT is normalized' {
    Set-Mock 'winget.exe' { $global:LASTEXITCODE = -1978335212 }
    $code = Invoke-WingetNative -CommandArguments @('list')
    Assert-True ($code -eq 2316632084L) 'Signed HRESULT was not normalized.'
}

Test-Case 'Installed apps are not reinstalled' {
    Set-Mock 'Invoke-WingetNative' {
        param([string[]]$CommandArguments)
        $script:Calls.Add(($CommandArguments -join ' '))
        return 0
    }
    Install-WindowsApps
    Assert-True ($script:Calls.Count -eq 3) 'Only three list queries expected.'
    Assert-True (@($script:Calls | Where-Object { -not $_.StartsWith('list ') }).Count -eq 0) 'Unexpected install or upgrade.'
}

Test-Case 'Missing apps install only the exact selected packages' {
    Set-Mock 'Invoke-WingetNative' {
        param([string[]]$CommandArguments)
        $script:Calls.Add(($CommandArguments -join ' '))
        if ($CommandArguments[0] -eq 'list') { return 2316632084L }
        return 0
    }
    Install-WindowsApps
    Assert-True ($script:Calls.Count -eq 6) 'Expected one query and install per app.'
    Assert-True ($script:Calls[1] -like 'install --id 9PLM9XGG6VKS --exact --source msstore *--no-upgrade') 'Wrong Store installation.'
    Assert-True ($script:Calls[3] -like 'install --id Google.Chrome --exact --source winget *') 'Wrong Chrome installation.'
    Assert-True (($script:Calls -join ' ') -notlike '*--all*') 'Must not install/upgrade all applications.'
}

Test-Case 'WinGet query errors do not cause an install' {
    Set-Mock 'Invoke-WingetNative' {
        param([string[]]$CommandArguments)
        $script:Calls.Add(($CommandArguments -join ' '))
        return 5
    }
    Assert-Throws { Install-WindowsApps } '*no install attempted*'
    Assert-True ($script:Calls.Count -eq 1) 'Query failure must stop immediately.'
}

Test-Case 'Explicit upgrades accept only the no-update HRESULT' {
    Set-Mock 'Invoke-WingetNative' {
        param([string[]]$CommandArguments)
        $script:Calls.Add(($CommandArguments -join ' '))
        if ($CommandArguments[0] -eq 'upgrade') { return 2316632107L }
        return 0
    }
    Install-WindowsApps -Upgrade
    Assert-True (@($script:Calls | Where-Object { $_.StartsWith('upgrade --id ') }).Count -eq 3) 'Expected three targeted upgrades.'
}

Test-Case 'Installer failures stop later app installations' {
    Set-Mock 'Invoke-WingetNative' {
        param([string[]]$CommandArguments)
        $script:Calls.Add(($CommandArguments -join ' '))
        if ($CommandArguments[0] -eq 'list') { return 2316632084L }
        return 1603
    }
    Assert-Throws { Install-WindowsApps } '*install failed*'
    Assert-True ($script:Calls.Count -eq 2) 'Failed installation must stop the batch.'
}

Test-Case 'AppsOnly does not touch WSL' {
    Set-Mock 'Assert-WindowsHost' { param([switch]$OnlyApps) Assert-True $OnlyApps 'Apps-only host check expected.' }
    Set-Mock 'Install-WindowsApps' { param([switch]$Upgrade) $script:Calls.Add('apps') }
    Set-Mock 'Install-WslExtension' { $script:Calls.Add('extension') }
    Set-Mock 'Initialize-Wsl' { throw 'Unexpected WSL operation.' }
    Assert-True (Invoke-WindowsSetup -Name Ubuntu -OnlyApps) 'Apps-only setup should complete.'
    Assert-True (($script:Calls -join ',') -eq 'apps,extension') 'Wrong apps-only operations.'
}

Test-Case 'New WSL installation stops before Linux bootstrap' {
    Set-Mock 'Get-WslDistribution' { param([string]$Name) return $null }
    Set-Mock 'Install-WslDistribution' { param([string]$Name) $script:Calls.Add($Name) }
    Set-Mock 'Install-WslDotfiles' { throw 'Unexpected bootstrap before restart/user creation.' }
    Assert-True (-not (Initialize-Wsl -Name 'Ubuntu-24.04')) 'New WSL setup must report pending.'
    Assert-True (($script:Calls -join ',') -eq 'Ubuntu-24.04') 'Wrong installation target.'
}

Test-Case 'WSL1 is neither replaced nor converted automatically' {
    Set-Mock 'Get-WslDistribution' { param([string]$Name) [pscustomobject]@{ Name = $Name; Version = 1 } }
    Set-Mock 'Install-WslDistribution' { throw 'Unexpected reinstall.' }
    Set-Mock 'Install-WslDotfiles' { throw 'Unexpected bootstrap.' }
    Assert-Throws { Initialize-Wsl -Name Ubuntu } '*WSL1*'
}

Test-Case 'Root is never used as the dotfiles account' {
    Set-Mock 'Get-WslDistribution' { param([string]$Name) [pscustomobject]@{ Name = $Name; Version = 2 } }
    Set-Mock 'Invoke-WslCapture' { param([string[]]$CommandArguments) '0' }
    Set-Mock 'Install-WslDotfiles' { throw 'Unexpected root bootstrap.' }
    Assert-True (-not (Initialize-Wsl -Name Ubuntu)) 'Root must report pending user setup.'
}

Test-Case 'Ready WSL2 hands off using its registered name' {
    Set-Mock 'Get-WslDistribution' { param([string]$Name) [pscustomobject]@{ Name = 'Ubuntu-24.04'; Version = 2 } }
    Set-Mock 'Invoke-WslCapture' { param([string[]]$CommandArguments) '1000' }
    Set-Mock 'Install-WslDotfiles' { param([string]$Name) $script:Calls.Add($Name) }
    Assert-True (Initialize-Wsl -Name 'ubuntu-24.04') 'Expected successful bootstrap.'
    Assert-True (($script:Calls -join ',') -eq 'Ubuntu-24.04') 'Must use the registered distribution name.'
}

Test-Case 'An unavailable WSL environment is not reinstalled' {
    Set-Mock 'Get-WslDistribution' { param([string]$Name) [pscustomobject]@{ Name = $Name; Version = 2 } }
    Set-Mock 'Invoke-WslCapture' { param([string[]]$CommandArguments) throw 'WSL command failed.' }
    Set-Mock 'Install-WslDistribution' { throw 'Unexpected reinstall.' }
    Assert-Throws { Initialize-Wsl -Name Ubuntu } '*WSL command failed*'
}

Test-Case 'Bootstrap uses a UTF8 LF file and retains interactive stdin' {
    $script:TemporaryBootstrap = $null
    Set-Mock 'Invoke-WslCapture' {
        param([string[]]$CommandArguments)
        $script:TemporaryBootstrap = $CommandArguments[-1]
        Assert-True (Test-Path -LiteralPath $script:TemporaryBootstrap) 'Temporary bootstrap is missing.'
        $bytes = [IO.File]::ReadAllBytes($script:TemporaryBootstrap)
        Assert-True (-not ($bytes[0] -eq 239 -and $bytes[1] -eq 187)) 'Unexpected UTF8 BOM.'
        Assert-True (-not ($bytes -contains 13)) 'Unexpected CRLF line endings.'
        '/mnt/c/temporary path/bootstrap.sh'
    }
    Set-Mock 'Invoke-WslBootstrapNative' {
        param([string]$Name, [string]$LinuxPath)
        Assert-True ($Name -eq 'Ubuntu' -and $LinuxPath -eq '/mnt/c/temporary path/bootstrap.sh') 'Path with spaces was not preserved.'
        $script:Calls.Add('bootstrap')
    }
    Install-WslDotfiles -Name Ubuntu
    Assert-True (($script:Calls -join ',') -eq 'bootstrap') 'Expected one bootstrap.'
    Assert-True (-not (Test-Path -LiteralPath $script:TemporaryBootstrap)) 'Temporary bootstrap was not removed.'
}

Test-Case 'Temporary files are removed after Linux setup failure' {
    $script:TemporaryBootstrap = $null
    Set-Mock 'Invoke-WslCapture' {
        param([string[]]$CommandArguments)
        $script:TemporaryBootstrap = $CommandArguments[-1]
        '/mnt/c/bootstrap.sh'
    }
    Set-Mock 'Invoke-WslBootstrapNative' { param([string]$Name, [string]$LinuxPath) throw 'Synthetic setup failure.' }
    Assert-Throws { Install-WslDotfiles -Name Ubuntu } '*Synthetic setup failure*'
    Assert-True (-not (Test-Path -LiteralPath $script:TemporaryBootstrap)) 'Failed bootstrap left a temporary file.'
}

Test-Case 'WSL capture preserves Unicode and restores console encoding' {
    $previous = [Console]::OutputEncoding.CodePage
    Set-Mock 'wsl.exe' {
        Assert-True ([Console]::OutputEncoding.CodePage -eq 65001) 'WSL output must be decoded as UTF8.'
        $global:LASTEXITCODE = 0
        '/mnt/c/' + [char]0x65e5 + [char]0x672c + ' User/bootstrap.sh'
    }
    $translated = Invoke-WslCapture -CommandArguments @('synthetic')
    Assert-True ($translated -eq ('/mnt/c/' + [char]0x65e5 + [char]0x672c + ' User/bootstrap.sh')) 'Unicode path was not preserved.'
    Assert-True ([Console]::OutputEncoding.CodePage -eq $previous) 'Console encoding was not restored.'
}

Test-Case 'WSL capture restores console encoding on failure' {
    $previous = [Console]::OutputEncoding.CodePage
    Set-Mock 'wsl.exe' { $global:LASTEXITCODE = 37 }
    Assert-Throws { Invoke-WslCapture -CommandArguments @('synthetic') } '*WSL command failed (exit 37)*'
    Assert-True ([Console]::OutputEncoding.CodePage -eq $previous) 'Failed capture changed the console encoding.'
}

Test-Case 'WSL registrations are selected by exact name and version' {
    Set-Mock 'Test-Path' { param([string]$LiteralPath) return $true }
    Set-Mock 'Get-ChildItem' { param([string]$LiteralPath) [pscustomobject]@{ PSPath = 'synthetic:one' }; [pscustomobject]@{ PSPath = 'synthetic:two' } }
    Set-Mock 'Get-ItemProperty' {
        param([string]$LiteralPath)
        if ($LiteralPath -eq 'synthetic:one') { return [pscustomobject]@{ DistributionName = 'Ubuntu-Other'; Version = 1 } }
        [pscustomobject]@{ DistributionName = 'Ubuntu'; Version = 2 }
    }
    $selected = Get-WslDistribution -Name Ubuntu
    Assert-True ($selected.Name -eq 'Ubuntu' -and $selected.Version -eq 2) 'Wrong WSL registration.'
}

Test-Case 'WSL elevation uses only the selected installation command' {
    Set-Mock 'Get-Command' { param([string]$Name, $ErrorAction) [pscustomobject]@{ Source = 'C:\Windows\System32\wsl.exe' } }
    Set-Mock 'Start-Process' {
        param([string]$FilePath, [string[]]$ArgumentList, [string]$Verb, [switch]$Wait, [switch]$PassThru)
        Assert-True ($FilePath -eq 'C:\Windows\System32\wsl.exe' -and $Verb -eq 'RunAs' -and $Wait -and $PassThru) 'Wrong elevation call.'
        Assert-True (($ArgumentList -join ' ') -eq '--install --distribution Ubuntu-24.04 --no-launch') 'Wrong WSL arguments.'
        [pscustomobject]@{ ExitCode = 3010 }
    }
    Install-WslDistribution -Name 'Ubuntu-24.04'
}

Test-Case 'VS Code extension is installed once' {
    Set-Mock 'Find-WindowsCode' { 'synthetic-code' }
    Set-Mock 'synthetic-code' {
        $global:LASTEXITCODE = 0
        $script:Calls.Add(($args -join ' '))
        if ($args[0] -eq '--list-extensions') { 'other.extension' }
    }
    Install-WslExtension
    Assert-True (($script:Calls -join ',') -eq '--list-extensions,--install-extension ms-vscode-remote.remote-wsl') 'Unexpected extension operations.'
}

Test-Case 'Existing VS Code WSL extension is not reinstalled' {
    Set-Mock 'Find-WindowsCode' { 'synthetic-code' }
    Set-Mock 'synthetic-code' {
        $global:LASTEXITCODE = 0
        $script:Calls.Add(($args -join ' '))
        'ms-vscode-remote.remote-wsl'
    }
    Install-WslExtension
    Assert-True (($script:Calls -join ',') -eq '--list-extensions') 'Unexpected extension reinstall.'
}

Write-Host ("{0} Windows bootstrap tests passed." -f $script:Passed)
