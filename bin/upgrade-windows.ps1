#requires -Version 5.1
[CmdletBinding()]
param([switch]$IncludeSteam, [switch]$IncludeDynaFiler)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'install-windows.ps1') -IncludeSteam:$IncludeSteam -IncludeDynaFiler:$IncludeDynaFiler

function Invoke-WindowsUpgrade {
    param([switch]$IncludeSteam, [switch]$IncludeDynaFiler)
    Assert-WindowsHost -OnlyApps
    Install-WindowsApps -Upgrade -OnlyInstalled -IncludeSteam:$IncludeSteam -IncludeDynaFiler:$IncludeDynaFiler
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        Invoke-WindowsUpgrade -IncludeSteam:$IncludeSteam -IncludeDynaFiler:$IncludeDynaFiler
        Write-Host 'Success: installed managed Windows apps were upgraded.'
    } catch {
        Write-Error $_ -ErrorAction Continue
        exit 1
    }
}
