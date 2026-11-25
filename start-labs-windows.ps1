$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$mongo = Get-Command mongod.exe -ErrorAction SilentlyContinue
if ($mongo) {
    $mongoPath = $mongo.Source
} else {
    $mongoPath = Get-ChildItem "$env:ProgramFiles\MongoDB\Server\*\bin\mongod.exe" -File -ErrorAction SilentlyContinue |
        Sort-Object { [version]$_.Directory.Parent.Name } -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $mongoPath) { throw 'Install MongoDB Community Server for Windows first.' }

$port = 27029
$data = Join-Path $env:LOCALAPPDATA 'CTI-Sentinel\mongo-labs'
New-Item -ItemType Directory -Force -Path $data | Out-Null
$lock = [System.IO.File]::Open((Join-Path $data 'launcher.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
$server = $null
try {
    python -c 'import pymongo, flask, flask_cors, dotenv, rich, numpy'
    if ($LASTEXITCODE -ne 0) { throw 'Run python -m pip install -r requirements.txt first.' }
    if (-not (Test-Path -LiteralPath 'frontend\node_modules\.bin\vite.cmd')) {
        npm.cmd ci --prefix frontend
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    }

    $env:MONGO_LABS_URI = "mongodb://127.0.0.1:$port/?directConnection=true"
    $env:MONGO_URI = $env:MONGO_LABS_URI
    $env:DATABASE_NAME = 'ctiSentinelLocalLabs'
    $env:ENABLE_LAB_RUNNER = '1'
    $env:FLASK_HOST = '127.0.0.1'
    $env:FLASK_PORT = '5000'

    $log = Join-Path $data 'mongod.log'
    $server = Start-Process -FilePath $mongoPath -ArgumentList "--dbpath `"$data`" --logpath `"$log`" --logappend --bind_ip 127.0.0.1 --port $port --replSet ctiLabs" -WindowStyle Hidden -PassThru
    $env:CTI_LABS_MONGOD_PID = $server.Id
    @'
import os
import time
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

with MongoClient(os.environ['MONGO_LABS_URI'], serverSelectionTimeoutMS=1000) as client:
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        try:
            status = client.admin.command('hello')
            if client.admin.command('serverStatus')['pid'] != int(os.environ['CTI_LABS_MONGOD_PID']):
                raise SystemExit('Port 27029 is already in use by another MongoDB process.')
            if status.get('setName') == 'ctiLabs' and status.get('isWritablePrimary'):
                break
            if status.get('isreplicaset'):
                try:
                    client.admin.command('replSetInitiate', {
                        '_id': 'ctiLabs',
                        'members': [{'_id': 0, 'host': 'localhost:27029'}],
                    })
                except OperationFailure as exc:
                    if exc.code != 23:  # AlreadyInitialized
                        raise
        except ConnectionFailure:
            pass
        time.sleep(0.5)
    else:
        raise SystemExit('MongoDB did not become primary. Check the local mongod.log.')
'@ | python -B -
    if ($LASTEXITCODE -ne 0 -or $server.HasExited) { throw "MongoDB lab startup failed. Log at $log" }

    @'
from backend.config.connection import get_db
from backend.scripts.seed import main

if not get_db().list_collection_names():
    main()
'@ | python -B -
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the local demo database.' }

    Write-Host 'Open http://localhost:5173 after Vite starts. Keep this launcher open while using the labs.'
    & '.\start-windows.bat'
    Read-Host 'Press Enter here after closing the API and frontend to stop the lab database'
} finally {
    if ($server -and -not $server.HasExited) {
        @'
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

with MongoClient(os.environ['MONGO_LABS_URI'], serverSelectionTimeoutMS=2000) as client:
    try:
        if client.admin.command('serverStatus')['pid'] == int(os.environ['CTI_LABS_MONGOD_PID']):
            client.admin.command('shutdown', timeoutSecs=5)
    except ConnectionFailure:
        pass
'@ | python -B -
        if (-not $server.WaitForExit(8000)) { Stop-Process -InputObject $server }
    }
    $lock.Dispose()
}
