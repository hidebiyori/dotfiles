#requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$PrinterHostAddress,
    [string]$DriverInf
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Assert-WindowsPrinterAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Open an administrator PowerShell to register the printer. Use -WhatIf for a preview.'
    }
}

function Install-BrotherPrinterDriver {
    param([IO.FileInfo]$Inf, [string]$DriverName)

    $catalog = Join-Path $Inf.DirectoryName 'BROCH17A.CAT'
    if ((Get-AuthenticodeSignature -LiteralPath $catalog).Status -ne 'Valid') {
        throw 'The Brother printer driver catalog signature is not valid.'
    }
    # PnPUtil validates the signed package and stages it in the Windows driver store.
    & "$env:windir\System32\pnputil.exe" /add-driver $Inf.FullName | Out-Host
    if ($LASTEXITCODE -eq 3010) { throw 'Windows requested a restart. Restart Windows and rerun the setup.' }
    if ($LASTEXITCODE -ne 0) { throw "PnPUtil could not stage the Brother driver (exit $LASTEXITCODE)." }

    $hash = (Get-FileHash -LiteralPath $Inf.FullName).Hash
    $driverStore = Join-Path $env:windir 'System32\DriverStore\FileRepository'
    $storedInfs = @(Get-ChildItem -LiteralPath $driverStore -Directory -Filter 'broch17a.inf_amd64_*' | ForEach-Object {
        $candidate = Join-Path $_.FullName 'BROCH17A.INF'
        if ((Test-Path -LiteralPath $candidate -PathType Leaf) -and (Get-FileHash -LiteralPath $candidate).Hash -eq $hash) {
            $candidate
        }
    })
    if ($storedInfs.Count -ne 1) { throw 'Could not identify the staged Brother printer INF uniquely.' }
    Add-PrinterDriver -Name $DriverName -InfPath $storedInfs[0] -PrinterEnvironment 'Windows x64'
}

function Assert-BrotherPrinterPort {
    param([string]$PortName, [string]$PrinterHostAddress)

    $port = Get-CimInstance -ClassName Win32_TCPIPPrinterPort | Where-Object Name -eq $PortName
    if (-not $port -or $port.HostAddress -ne $PrinterHostAddress -or $port.PortNumber -ne 9100 -or $port.Protocol -ne 1) {
        throw "Port '$PortName' must use RAW TCP 9100 at the requested address."
    }
}

function Invoke-WindowsPrinterSetup {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param([string]$PrinterHostAddress, [string]$DriverInf)

    if ($env:OS -ne 'Windows_NT' -or [Environment]::OSVersion.Version.Build -lt 22000 -or -not [Environment]::Is64BitProcess -or
        [Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne 'X64') {
        throw 'Use 64-bit PowerShell on x64 Windows 11.'
    }
    if ([Uri]::CheckHostName($PrinterHostAddress) -notin 'Dns', 'IPv4') {
        throw 'Specify the printer hostname or IPv4 address with -PrinterHostAddress.'
    }

    $printerName = 'Brother HL-L3230CDW'
    $driverName = 'Brother HL-L3230CDW series'
    $portName = 'Brother HL-L3230CDW TCP-IP'
    $printer = Get-Printer | Where-Object Name -eq $printerName
    if ($printer) {
        if ($printer.DriverName -ne $driverName) { throw "Printer '$printerName' already exists with a different driver." }
        $portName = $printer.PortName
    }
    $port = Get-PrinterPort | Where-Object Name -eq $portName
    if ($printer -or $port) { Assert-BrotherPrinterPort -PortName $portName -PrinterHostAddress $PrinterHostAddress }

    $driver = Get-PrinterDriver | Where-Object { $_.Name -eq $driverName -and $_.PrinterEnvironment -eq 'Windows x64' }
    if ($driver -and ($driver.Manufacturer -ne 'Brother' -or
        [IO.Path]::GetFileName($driver.InfPath) -ne 'BROCH17A.INF')) {
        throw "Driver '$driverName' does not match the Brother printer driver (BROCH17A.INF)."
    }
    if ($printer -and $driver) {
        Write-Host "Already registered: $printerName"
        return
    }

    if (-not $driver) {
        if (-not $DriverInf) { throw 'Provide the extracted Brother printer driver (gdi\BROCH17A.INF) with -DriverInf.' }
        $inf = Get-Item -LiteralPath $DriverInf
        if ($inf -isnot [IO.FileInfo] -or $inf.Name -ne 'BROCH17A.INF') {
            throw 'Use the BROCH17A.INF file from the extracted Brother printer driver.'
        }
    }

    if (-not $PSCmdlet.ShouldProcess($PrinterHostAddress, "Register $printerName with the Brother driver on TCP port 9100")) { return }
    Assert-WindowsPrinterAdministrator
    if (-not $driver) {
        Install-BrotherPrinterDriver -Inf $inf -DriverName $driverName
        $installed = Get-PrinterDriver -Name $driverName -PrinterEnvironment 'Windows x64'
        if (-not $installed -or $installed.Manufacturer -ne 'Brother' -or
            [IO.Path]::GetFileName($installed.InfPath) -ne 'BROCH17A.INF') {
            throw 'The installed Brother driver could not be verified.'
        }
    }
    if (-not $port) {
        Add-PrinterPort -Name $portName -PrinterHostAddress $PrinterHostAddress -PortNumber 9100
        Assert-BrotherPrinterPort -PortName $portName -PrinterHostAddress $PrinterHostAddress
    }
    if (-not $printer) {
        Add-Printer -Name $printerName -DriverName $driverName -PortName $portName -Shared:$false
    }
    $registered = Get-Printer -Name $printerName
    if (-not $registered -or $registered.DriverName -ne $driverName -or $registered.PortName -ne $portName) {
        throw 'The registered Brother queue could not be verified.'
    }
    Write-Host "Registered: $printerName"
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        Invoke-WindowsPrinterSetup -PrinterHostAddress $PrinterHostAddress -DriverInf $DriverInf
    } catch {
        Write-Error $_ -ErrorAction Continue
        exit 1
    }
}
