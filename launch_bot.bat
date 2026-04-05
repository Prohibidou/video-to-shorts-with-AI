@echo off
title Auto-Accept Bot - Launcher
color 0B

echo.
echo  ============================================
echo   AUTO-ACCEPT BOT para Antigravity
echo   Launcher v1.0
echo  ============================================
echo.

:: Verificar si AutoHotkey está instalado
where AutoHotkey >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo  [!] AutoHotkey no encontrado en PATH.
    echo  Buscando en ubicaciones comunes...
    
    if exist "C:\Program Files\AutoHotkey\AutoHotkey.exe" (
        set "AHK_PATH=C:\Program Files\AutoHotkey\AutoHotkey.exe"
        echo  [OK] Encontrado: %AHK_PATH%
    ) else if exist "C:\Program Files\AutoHotkey\v2\AutoHotkey.exe" (
        set "AHK_PATH=C:\Program Files\AutoHotkey\v2\AutoHotkey.exe"
        echo  [OK] Encontrado: %AHK_PATH%
    ) else if exist "%LocalAppData%\Programs\AutoHotkey\AutoHotkey.exe" (
        set "AHK_PATH=%LocalAppData%\Programs\AutoHotkey\AutoHotkey.exe"
        echo  [OK] Encontrado: %AHK_PATH%
    ) else (
        echo.
        echo  [ERROR] AutoHotkey NO esta instalado.
        echo  Descargalo de: https://www.autohotkey.com/
        echo.
        pause
        exit /b 1
    )
) else (
    set "AHK_PATH=AutoHotkey"
    echo  [OK] AutoHotkey encontrado en PATH
)

echo.
echo  Iniciando Auto-Accept Bot...
echo  -------------------------------------------
echo  Controles:
echo    F1 = Iniciar    ^|  F2 = Pausar
echo    F3 = Detener    ^|  Ctrl+Shift+P = Capturar color
echo  -------------------------------------------
echo.

:: Ejecutar el script AHK
start "" "%AHK_PATH%" "%~dp0auto_accept.ahk"

echo  [OK] Bot lanzado! Podes cerrar esta ventana.
echo.
timeout /t 3 >nul
