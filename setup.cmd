@echo off
title setup
setlocal enabledelayedexpansion

python --version >nul 2>&1 || (
    echo python yukleniyor..
    curl -o python-3.11.8.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
    python-3.11.8.exe /quiet InstallAllUsers=1 PrependPath=1
    del python-3.11.8.exe
)

for /f "tokens=2" %%I in ('python --version 2^>^&1') do (
    echo %%I | findstr /R "3.11" >nul || (
        echo python 3.11 yukleniyor..
        curl -o python-3.11.8.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
        python-3.11.8.exe /quiet InstallAllUsers=1 PrependPath=1
        del python-3.11.8.exe
    )
)

python -m pip install --upgrade pip && pip install -r requirements.txt
pause >nul