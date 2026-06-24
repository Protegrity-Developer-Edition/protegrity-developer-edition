@echo off
setlocal enabledelayedexpansion
:: ==============================================================================
:: Protegrity AI Developer Edition Trial Center — Windows Deployment Script
::
:: Dockerised deployment with upfront prerequisite validation.
::
:: Usage:
::   scripts\deploy.bat              Full deployment (docker compose up)
::   scripts\deploy.bat --check      Prerequisite check only
::   scripts\deploy.bat --clean      Tear down containers and volumes
::   scripts\deploy.bat --logs       Tail container logs
::   scripts\deploy.bat --help       Show usage
:: ==============================================================================

:: ─── Configuration ───────────────────────────────────────────────────────────

set "PROJECT_ROOT=%~dp0.."
set "STREAMLIT_PORT=8502"
set "GUARDRAIL_PORT=8581"
set "DISCOVERY_PORT=8580"
set "MIN_DOCKER=20.10"
set "MIN_COMPOSE=2.0"
set "BLOCKERS=0"
set "WARNINGS=0"

if defined TRIAL_CENTER_PORT set "STREAMLIT_PORT=%TRIAL_CENTER_PORT%"
if defined SEMANTIC_GUARDRAIL_PORT set "GUARDRAIL_PORT=%SEMANTIC_GUARDRAIL_PORT%"
if defined CLASSIFICATION_SERVICE_PORT set "DISCOVERY_PORT=%CLASSIFICATION_SERVICE_PORT%"

:: ─── Route Command ───────────────────────────────────────────────────────────

if "%~1"=="--help" goto :show_help
if "%~1"=="-h" goto :show_help
if "%~1"=="--clean" goto :do_clean
if "%~1"=="--logs" goto :do_logs
if "%~1"=="--check" (
    call :run_checks
    call :display_results
    goto :eof
)

:: Default: full deployment
call :run_checks
call :display_results
if !BLOCKERS! GTR 0 (
    echo.
    echo   Please resolve blocker(s) above and re-run.
    exit /b 1
)

echo.
set /p "RESPONSE=  Proceed with deployment? [Y/n] "
if /i "!RESPONSE!"=="n" (
    echo Aborted.
    exit /b 0
)
if /i "!RESPONSE!"=="no" (
    echo Aborted.
    exit /b 0
)

call :deploy
goto :eof

:: ─── Prerequisite Checks ─────────────────────────────────────────────────────

:run_checks
set "CHECK_INDEX=0"

:: Check Docker
docker version >nul 2>&1
if errorlevel 1 (
    call :add_check "Docker" ">= %MIN_DOCKER%" "not installed/not running" "FAIL" "Install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/"
) else (
    for /f "tokens=*" %%v in ('docker version --format "{{.Server.Version}}" 2^>nul') do set "DOCKER_VER=%%v"
    call :add_check "Docker" ">= %MIN_DOCKER%" "!DOCKER_VER!" "PASS" ""
)

:: Check Docker Compose
docker compose version >nul 2>&1
if errorlevel 1 (
    call :add_check "Docker Compose" ">= %MIN_COMPOSE%" "not installed" "FAIL" "Update Docker Desktop (includes Compose V2)"
) else (
    for /f "tokens=*" %%v in ('docker compose version --short 2^>nul') do set "COMPOSE_VER=%%v"
    call :add_check "Docker Compose" ">= %MIN_COMPOSE%" "!COMPOSE_VER!" "PASS" ""
)

:: Check docker-compose.yml
if exist "%PROJECT_ROOT%\docker-compose.yml" (
    call :add_check "docker-compose.yml" "present" "found" "PASS" ""
) else if exist "%PROJECT_ROOT%\docker-compose.yaml" (
    call :add_check "docker-compose.yml" "present" "found" "PASS" ""
) else (
    call :add_check "docker-compose.yml" "present" "missing" "FAIL" "File should exist at project root. Check your git clone."
)

:: Check ports
call :check_port %STREAMLIT_PORT% "TRIAL_CENTER"
call :check_port %GUARDRAIL_PORT% "SEMANTIC_GUARDRAIL"
call :check_port %DISCOVERY_PORT% "CLASSIFICATION_SERVICE"

:: Check .env
if exist "%PROJECT_ROOT%\.env" (
    call :add_check ".env file" "present" "found" "PASS" ""
) else (
    call :add_check ".env file" "present" "missing" "WARN" "copy .env.example .env and edit with your credentials"
)

goto :eof

:: ─── Port Check ──────────────────────────────────────────────────────────────

:check_port
set "PORT=%~1"
set "LABEL=%~2"
netstat -an 2>nul | findstr /c:":%PORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    call :add_check "Port %PORT% (%LABEL%)" "available" "in use" "FAIL" "Free the port or set %LABEL%_PORT env var"
) else (
    call :add_check "Port %PORT% (%LABEL%)" "available" "available" "PASS" ""
)
goto :eof

:: ─── Add Check Result ────────────────────────────────────────────────────────

:add_check
set "CHK_NAME_%CHECK_INDEX%=%~1"
set "CHK_REQ_%CHECK_INDEX%=%~2"
set "CHK_FOUND_%CHECK_INDEX%=%~3"
set "CHK_STATUS_%CHECK_INDEX%=%~4"
set "CHK_FIX_%CHECK_INDEX%=%~5"
if "%~4"=="FAIL" set /a "BLOCKERS+=1"
if "%~4"=="WARN" set /a "WARNINGS+=1"
set /a "CHECK_INDEX+=1"
goto :eof

:: ─── Display Results ─────────────────────────────────────────────────────────

:display_results
echo.
echo ======================================================================
echo        Protegrity Trial Center - Prerequisite Check
echo ======================================================================
echo   Requirement              Required         Found                Status
echo ----------------------------------------------------------------------

set /a "IDX=0"
:display_loop
if !IDX! GEQ !CHECK_INDEX! goto :display_done

set "STATUS_ICON=[OK]"
if "!CHK_STATUS_%IDX%!"=="FAIL" set "STATUS_ICON=[FAIL]"
if "!CHK_STATUS_%IDX%!"=="WARN" set "STATUS_ICON=[WARN]"

echo   !CHK_NAME_%IDX%!	!CHK_REQ_%IDX%!	!CHK_FOUND_%IDX%!	!STATUS_ICON!

set /a "IDX+=1"
goto :display_loop

:display_done
echo ----------------------------------------------------------------------
if !BLOCKERS! EQU 0 if !WARNINGS! EQU 0 (
    echo   All prerequisites met - ready to deploy!
) else (
    echo   Result: !BLOCKERS! BLOCKER(S), !WARNINGS! WARNING(S)
)
echo ======================================================================

:: Show remediation
if !BLOCKERS! GTR 0 (
    echo.
    set /a "IDX=0"
    :fix_loop
    if !IDX! GEQ !CHECK_INDEX! goto :fix_done
    if "!CHK_STATUS_%IDX%!"=="FAIL" (
        echo   [FAIL] !CHK_NAME_%IDX%!
        echo          -^> !CHK_FIX_%IDX%!
        echo.
    )
    set /a "IDX+=1"
    goto :fix_loop
    :fix_done
)
if !WARNINGS! GTR 0 (
    set /a "IDX=0"
    :warn_loop
    if !IDX! GEQ !CHECK_INDEX! goto :warn_done
    if "!CHK_STATUS_%IDX%!"=="WARN" (
        echo   [WARN] !CHK_NAME_%IDX%!
        echo          -^> !CHK_FIX_%IDX%!
        echo.
    )
    set /a "IDX+=1"
    goto :warn_loop
    :warn_done
)
goto :eof

:: ─── Deploy ──────────────────────────────────────────────────────────────────

:deploy
echo.
echo   Deploying Protegrity AI Developer Edition Trial Center...
echo.

docker compose -f "%PROJECT_ROOT%\docker-compose.yml" up -d --build
if errorlevel 1 (
    echo   [ERROR] Docker Compose failed. Check errors above.
    exit /b 1
)

echo.
echo   [OK] Containers started!
echo.
echo   Waiting for Trial Center to become healthy...

set "HEALTHY=0"
for /l %%i in (1,1,30) do (
    if !HEALTHY! EQU 0 (
        curl -sf --max-time 2 "http://localhost:%STREAMLIT_PORT%/_stcore/health" >nul 2>&1
        if not errorlevel 1 set "HEALTHY=1"
        if !HEALTHY! EQU 0 (
            <nul set /p"=."
            timeout /t 2 /nobreak >nul
        )
    )
)
echo.

if !HEALTHY! EQU 1 (
    echo.
    echo   ============================================================
    echo     Protegrity AI Developer Edition Trial Center
    echo.
    echo     UI:     http://localhost:%STREAMLIT_PORT%
    echo.
    echo     Logs:   scripts\deploy.bat --logs
    echo     Stop:   scripts\deploy.bat --clean
    echo     Status: docker compose ps
    echo   ============================================================
    echo.
) else (
    echo   [WARN] Trial Center did not become healthy within 60s.
    echo          Check logs: scripts\deploy.bat --logs
)

docker compose -f "%PROJECT_ROOT%\docker-compose.yml" ps
goto :eof

:: ─── Clean ───────────────────────────────────────────────────────────────────

:do_clean
echo.
echo   Stopping and removing containers...
docker compose -f "%PROJECT_ROOT%\docker-compose.yml" down --volumes --remove-orphans 2>nul
echo   [OK] Containers stopped and removed.
echo.
set /p "RESPONSE=  Remove built images too? [y/N] "
if /i "!RESPONSE!"=="y" (
    docker compose -f "%PROJECT_ROOT%\docker-compose.yml" down --rmi local 2>nul
    echo   [OK] Local images removed.
)
echo.
echo   Run scripts\deploy.bat to redeploy.
goto :eof

:: ─── Logs ────────────────────────────────────────────────────────────────────

:do_logs
docker compose -f "%PROJECT_ROOT%\docker-compose.yml" logs -f --tail=100
goto :eof

:: ─── Help ────────────────────────────────────────────────────────────────────

:show_help
echo.
echo   Protegrity AI Developer Edition Trial Center - Deployment
echo.
echo   Usage: scripts\deploy.bat [OPTION]
echo.
echo   Options:
echo     (none)      Full deployment: prerequisite check, build, launch
echo     --check     Run prerequisite check only (no action taken)
echo     --clean     Stop and remove all containers and volumes
echo     --logs      Tail logs from all containers
echo     --help      Show this help message
echo.
echo   Prerequisites:
echo     - Docker Desktop (Docker ^>= 20.10, Compose ^>= 2.0)
echo     - Ports %STREAMLIT_PORT%, %GUARDRAIL_PORT%, %DISCOVERY_PORT% available
echo     - .env file with credentials (optional)
echo.
echo   Environment variables:
echo     TRIAL_CENTER_PORT            UI port (default: 8502)
echo     SEMANTIC_GUARDRAIL_PORT      Guardrail port (default: 8581)
echo     CLASSIFICATION_SERVICE_PORT  Discovery port (default: 8580)
echo.
goto :eof
