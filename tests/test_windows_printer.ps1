# Included by test_windows.ps1. Printer queries and changes are stubbed.
. (Join-Path $PSScriptRoot '..\bin\setup-windows-printer.ps1')

function Initialize-PrinterMocks {
    $script:BrotherQueue = $null
    $script:BrotherPort = $null
    $script:BrotherDriver = [pscustomobject]@{
        Name = 'Brother HL-L3230CDW series'
        Manufacturer = 'Brother'
        PrinterEnvironment = 'Windows x64'
        InfPath = 'C:\Windows\System32\DriverStore\FileRepository\broch17a.inf_amd64_example\broch17a.inf'
    }
    Set-Mock 'Get-Printer' { param($Name) if ($script:BrotherQueue) { $script:BrotherQueue } }
    Set-Mock 'Get-PrinterPort' { if ($script:BrotherPort) { $script:BrotherPort } }
    Set-Mock 'Get-PrinterDriver' { if ($script:BrotherDriver) { $script:BrotherDriver } }
    Set-Mock 'Get-CimInstance' {
        param($ClassName)
        Assert-True ($ClassName -eq 'Win32_TCPIPPrinterPort') 'Unexpected port query.'
        if ($script:BrotherPort) { $script:BrotherPort }
    }
    Set-Mock 'Assert-WindowsPrinterAdministrator' { $script:Calls.Add('administrator') }
    Set-Mock 'Install-BrotherPrinterDriver' { throw 'Unexpected driver installation.' }
    Set-Mock 'Add-PrinterPort' {
        param($Name, $PrinterHostAddress, $PortNumber)
        $script:Calls.Add('port')
        $script:BrotherPort = [pscustomobject]@{
            Name = $Name
            HostAddress = $PrinterHostAddress
            PortNumber = $PortNumber
            Protocol = 1
        }
    }
    Set-Mock 'Add-Printer' {
        param($Name, $DriverName, $PortName, [switch]$Shared)
        Assert-True (-not $Shared) 'The new printer must be local to this PC.'
        $script:Calls.Add('queue')
        $script:BrotherQueue = [pscustomobject]@{ Name = $Name; DriverName = $DriverName; PortName = $PortName }
    }
}

Test-Case 'Brother setup registers a RAW port and the model driver, then reuses them' {
    Initialize-PrinterMocks
    Invoke-WindowsPrinterSetup -PrinterHostAddress printer.local
    Assert-True ($script:BrotherPort.HostAddress -eq 'printer.local' -and $script:BrotherPort.PortNumber -eq 9100) 'Incorrect print endpoint.'
    Assert-True ($script:BrotherQueue.Name -eq 'Brother HL-L3230CDW' -and
        $script:BrotherQueue.DriverName -eq 'Brother HL-L3230CDW series' -and
        $script:BrotherQueue.PortName -eq $script:BrotherPort.Name) 'Incorrect queue settings.'
    Invoke-WindowsPrinterSetup -PrinterHostAddress printer.local
    Assert-True (($script:Calls -join ',') -eq 'administrator,port,queue') 'Repeat setup must reuse the existing port, driver, and queue.'
}

Test-Case 'Brother setup preserves a conflicting printer or port' {
    Initialize-PrinterMocks
    $script:BrotherQueue = [pscustomobject]@{
        Name = 'Brother HL-L3230CDW'
        DriverName = 'Microsoft IPP Class Driver'
        PortName = 'WSD-example'
    }
    Assert-Throws { Invoke-WindowsPrinterSetup -PrinterHostAddress printer.local } '*already exists with a different driver*'
    $script:BrotherQueue = $null
    $script:BrotherPort = [pscustomobject]@{ Name = 'Brother HL-L3230CDW TCP-IP'; HostAddress = 'other.local'; PortNumber = 9100; Protocol = 1 }
    Assert-Throws { Invoke-WindowsPrinterSetup -PrinterHostAddress printer.local } '*must use RAW TCP 9100 at the requested address*'
    Assert-True ($script:Calls.Count -eq 0) 'A conflicting queue or port must be preserved.'
}

Test-Case 'Brother setup reuses a manually registered matching queue' {
    Initialize-PrinterMocks
    $script:BrotherPort = [pscustomobject]@{ Name = 'printer.local'; HostAddress = 'printer.local'; PortNumber = 9100; Protocol = 1 }
    $script:BrotherQueue = [pscustomobject]@{ Name = 'Brother HL-L3230CDW'; DriverName = $script:BrotherDriver.Name; PortName = 'printer.local' }
    Invoke-WindowsPrinterSetup -PrinterHostAddress printer.local
    $script:BrotherPort.Protocol = 2
    Assert-Throws { Invoke-WindowsPrinterSetup -PrinterHostAddress printer.local } '*must use RAW TCP 9100 at the requested address*'
    Assert-True ($script:Calls.Count -eq 0) 'A manually assigned port must be verified and preserved.'
}

Test-Case 'Brother setup can resume with an existing matching port' {
    Initialize-PrinterMocks
    $script:BrotherPort = [pscustomobject]@{ Name = 'Brother HL-L3230CDW TCP-IP'; HostAddress = '192.0.2.10'; PortNumber = 9100; Protocol = 1 }
    Invoke-WindowsPrinterSetup -PrinterHostAddress 192.0.2.10
    Assert-True (($script:Calls -join ',') -eq 'administrator,queue') 'A matching port should be reused after an interrupted setup.'
}

Test-Case 'Brother setup requires the model INF when the driver is missing' {
    Initialize-PrinterMocks
    $script:BrotherDriver = $null
    Assert-Throws { Invoke-WindowsPrinterSetup -PrinterHostAddress printer.local } '*-DriverInf*'
    Assert-True ($script:Calls.Count -eq 0) 'A missing driver must be reported before changes.'
}

Test-Case 'Brother setup passes the selected INF for installation before creating the queue' {
    Initialize-PrinterMocks
    $script:BrotherDriverToInstall = $script:BrotherDriver
    $script:BrotherDriver = $null
    Set-Mock 'Get-Item' {
        param($LiteralPath)
        Assert-True ($LiteralPath -eq 'C:\driver package\gdi\BROCH17A.INF') 'Incorrect requested INF path.'
        [IO.FileInfo]::new((Join-Path ([IO.Path]::GetTempPath()) 'BROCH17A.INF'))
    }
    Set-Mock 'Install-BrotherPrinterDriver' {
        param([IO.FileInfo]$Inf, [string]$DriverName)
        Assert-True ($Inf.Name -eq 'BROCH17A.INF' -and $DriverName -eq 'Brother HL-L3230CDW series') 'Incorrect INF or driver name.'
        $script:Calls.Add('driver')
        $script:BrotherDriver = $script:BrotherDriverToInstall
    }
    Invoke-WindowsPrinterSetup -PrinterHostAddress printer.local -DriverInf 'C:\driver package\gdi\BROCH17A.INF'
    Assert-True (($script:Calls -join ',') -eq 'administrator,driver,port,queue') 'Driver installation must precede port and queue creation.'
}

Test-Case 'Brother setup preview checks inputs without installing or registering anything' {
    Initialize-PrinterMocks
    Assert-Throws { Invoke-WindowsPrinterSetup -PrinterHostAddress 'http://printer.local/' -WhatIf } '*hostname or IPv4 address*'
    Invoke-WindowsPrinterSetup -PrinterHostAddress printer.local -WhatIf
    Assert-True ($script:Calls.Count -eq 0) 'Preview must not request administrator access or change print settings.'
}
