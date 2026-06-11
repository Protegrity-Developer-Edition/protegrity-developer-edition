@echo off
REM Sample script to run SampleAppFindAndRedact
REM Discovers PII and redacts it

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "JAVA_PROJECT_DIR=%SCRIPT_DIR%\..\..\data-protection\samples\java"

set "JAR_FILE=%JAVA_PROJECT_DIR%\target\protegrity-java-samples-1.0.0-jar-with-dependencies.jar"
set "MAIN_CLASS=com.protegrity.devedition.samples.SampleAppFindAndRedact"

REM Check if JAR exists
if not exist "%JAR_FILE%" (
    echo Building the project...
    cd /d "%JAVA_PROJECT_DIR%"
    call mvnw.cmd clean package -q
)

echo Running SampleAppFindAndRedact...
echo ========================================
java -cp "%JAR_FILE%" %MAIN_CLASS% %*
