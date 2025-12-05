@echo off
REM Sample script to run SampleAppFindAndProtect
REM Discovers PII and protects it in one operation

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "JAR_FILE=%SCRIPT_DIR%\target\protegrity-java-samples-1.0.0-jar-with-dependencies.jar"
set "MAIN_CLASS=com.protegrity.devedition.samples.SampleAppFindAndProtect"

REM Check if JAR exists
if not exist "%JAR_FILE%" (
    echo Building the project...
    cd /d "%SCRIPT_DIR%"
    call mvnw.cmd clean package -q
)

echo Running SampleAppFindAndProtect...
echo ========================================
java -cp "%JAR_FILE%" %MAIN_CLASS% %*
