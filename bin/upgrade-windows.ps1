#requires -Version 5.1
[CmdletBinding()]
param([switch]$IncludeSteam)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'install-windows.ps1') -IncludeSteam:$IncludeSteam

function Invoke-WindowsUpgrade {
    param([switch]$IncludeSteam)
    Assert-WindowsHost -OnlyApps
    Install-WindowsApps -Upgrade -OnlyInstalled -IncludeSteam:$IncludeSteam
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        Invoke-WindowsUpgrade -IncludeSteam:$IncludeSteam
        Write-Host 'Success: installed managed Windows apps were upgraded.'
    } catch {
        Write-Error $_ -ErrorAction Continue
        exit 1
    }
}
