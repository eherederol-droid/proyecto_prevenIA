$ErrorActionPreference = 'Stop'

$backendPath = Join-Path $PSScriptRoot 'backend'
$python = Join-Path $backendPath 'venv\Scripts\python.exe'
$cloudflaredPath = $env:CLOUDFLARED_PATH
if (-not $cloudflaredPath) {
    $cloudflaredCommand = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cloudflaredCommand) {
        $cloudflaredPath = $cloudflaredCommand.Source
    }
}

if (-not (Test-Path $python)) {
    throw "No se encontro el Python del proyecto: $python"
}
if (-not $cloudflaredPath -or -not (Test-Path $cloudflaredPath)) {
    throw 'Falta cloudflared. Instala Cloudflare Tunnel para Windows y vuelve a ejecutar este script.'
}

$portsInUse = @(8000, 3001) | Where-Object {
    Get-NetTCPConnection -LocalPort $_ -State Listen -ErrorAction SilentlyContinue
}
if ($portsInUse.Count -gt 0) {
    throw "Los puertos $($portsInUse -join ', ') ya estan ocupados. Deten esos servidores e intentalo otra vez."
}

$logDirectory = Join-Path $env:TEMP 'prevenia-demo-share'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$backendLog = Join-Path $logDirectory 'backend.log'
$backendErrorLog = Join-Path $logDirectory 'backend-error.log'
$proxyLog = Join-Path $logDirectory 'proxy.log'
$proxyErrorLog = Join-Path $logDirectory 'proxy-error.log'
$tunnelLog = Join-Path $logDirectory 'tunnel.log'
$tunnelErrorLog = Join-Path $logDirectory 'tunnel-error.log'
Remove-Item $backendLog, $backendErrorLog, $proxyLog, $proxyErrorLog, $tunnelLog, $tunnelErrorLog -Force -ErrorAction SilentlyContinue

$environmentVariables = @('DEBUG', 'ALLOWED_HOSTS', 'SECRET_KEY')
$previousEnvironment = @{}
foreach ($name in $environmentVariables) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$randomBytes = New-Object byte[] 64
$randomGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$randomGenerator.GetBytes($randomBytes)
$env:DEBUG = 'False'
$env:ALLOWED_HOSTS = 'localhost,127.0.0.1'
$env:SECRET_KEY = [Convert]::ToBase64String($randomBytes)

$backendProcess = $null
$proxyProcess = $null
$tunnelProcess = $null

try {
    $backendProcess = Start-Process -FilePath $python `
        -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000', '--noreload') `
        -WorkingDirectory $backendPath -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $backendLog -RedirectStandardError $backendErrorLog
    Start-Sleep -Seconds 2
    if ($backendProcess.HasExited) {
        Get-Content $backendLog -Tail 30 -ErrorAction SilentlyContinue
        throw 'Django no pudo iniciar. Revisa la configuración y la base de datos.'
    }
    Remove-Item Env:\SECRET_KEY -ErrorAction SilentlyContinue

    $proxyProcess = Start-Process -FilePath $python `
        -ArgumentList @('share_server.py') -WorkingDirectory $backendPath `
        -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $proxyLog -RedirectStandardError $proxyErrorLog
    Start-Sleep -Seconds 2
    if ($proxyProcess.HasExited) {
        Get-Content $proxyLog -Tail 30 -ErrorAction SilentlyContinue
        throw 'El servidor seguro para compartir no pudo iniciar.'
    }

    $tunnelProcess = Start-Process -FilePath $cloudflaredPath `
        -ArgumentList @('tunnel', '--url', 'http://127.0.0.1:3001', '--no-autoupdate') `
        -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $tunnelLog -RedirectStandardError $tunnelErrorLog

    $shareUrl = $null
    for ($attempt = 0; $attempt -lt 60 -and -not $shareUrl; $attempt++) {
        if ($tunnelProcess.HasExited) {
            Get-Content $tunnelLog -Tail 30 -ErrorAction SilentlyContinue
            Get-Content $tunnelErrorLog -Tail 30 -ErrorAction SilentlyContinue
            throw 'Cloudflare Tunnel se cerró antes de crear el enlace.'
        }
        $tunnelOutput = (Get-Content $tunnelLog, $tunnelErrorLog -Raw -ErrorAction SilentlyContinue) -join "`n"
        if ($tunnelOutput -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
            $shareUrl = $Matches[0]
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not $shareUrl) {
        Get-Content $tunnelLog -Tail 30 -ErrorAction SilentlyContinue
        Get-Content $tunnelErrorLog -Tail 30 -ErrorAction SilentlyContinue
        throw 'No se recibió el enlace temporal de Cloudflare.'
    }

    try {
        $health = Invoke-WebRequest 'http://127.0.0.1:3001/healthz' -UseBasicParsing -TimeoutSec 10
        if ($health.StatusCode -ne 200) {
            throw 'El servidor local no pasó su prueba de salud.'
        }
    } catch {
        throw "El enlace se creó, pero el servidor local no responde: $($_.Exception.Message)"
    }

    Write-Host ''
    Write-Host "Enlace temporal para compartir: $shareUrl" -ForegroundColor Green
    Write-Host 'Comparte el enlace solo con tus amigos y usa exclusivamente datos ficticios.'
    Write-Host 'Deja esta ventana abierta. Presiona Ctrl+C para cerrar el enlace.'
    Write-Host ''

    while (-not $tunnelProcess.HasExited -and -not $backendProcess.HasExited -and -not $proxyProcess.HasExited) {
        Start-Sleep -Seconds 2
    }
    throw 'Uno de los procesos del servidor terminó. El enlace dejará de funcionar.'
} finally {
    foreach ($process in @($tunnelProcess, $proxyProcess, $backendProcess)) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    $randomGenerator.Dispose()
    [Array]::Clear($randomBytes, 0, $randomBytes.Length)
    foreach ($name in $environmentVariables) {
        if ($null -eq $previousEnvironment[$name]) {
            Remove-Item "Env:\$name" -ErrorAction SilentlyContinue
        } else {
            [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
        }
    }
}
