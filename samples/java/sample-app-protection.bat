@echo off
REM Sample script to run SampleAppProtection
REM Demonstrates data protection operations using Protegrity Application Protector

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "JAR_FILE=%SCRIPT_DIR%\target\protegrity-java-samples-1.0.0-jar-with-dependencies.jar"
set "MAIN_CLASS=com.protegrity.devedition.samples.SampleAppProtection"

REM Function to display usage
if "%~1"=="" goto :usage
if "%~1"=="--help" goto :usage
if "%~1"=="-h" goto :usage
goto :checkjar

:usage
echo Running SampleAppProtection...
echo ========================================
echo Usage: sample-app-protection.bat [OPTIONS]
echo.
echo Protect and unprotect data using Protegrity
echo.
echo Required arguments:
echo   --input_data ^<data^>       The data to protect (e.g., 'John Smith')
echo   --policy_user ^<user^>      Policy user for the session (e.g., 'superuser')
echo   --data_element ^<element^>  Data element type (e.g., 'string', 'email')
echo.
echo Optional arguments:
echo   --protect                 Only perform protect operation
echo   --unprotect               Only perform unprotect operation
echo   --enc                     Only perform encrypt operation (output in hex format)
echo   --dec                     Only perform decrypt operation
echo.
echo Examples:
echo   sample-app-protection.bat --input_data "John Smith" --policy_user superuser --data_element string
echo   sample-app-protection.bat --input_data "john@example.com" --policy_user superuser --data_element email --protect
echo   sample-app-protection.bat --input_data "0QjD@example.com" --policy_user superuser --data_element email --unprotect
echo   sample-app-protection.bat --input_data "John Smith" --policy_user superuser --data_element text --enc
echo   sample-app-protection.bat --input_data "e7087f449913bca6471e2b3209166dbb" --policy_user superuser --data_element text --dec
echo   sample-app-protection.bat --input_data "ELatin1_S+NSABC¹º»¼½¾¿ÄÅÆÇÈAlice1234567Bob" --policy_user superuser --data_element fpe_latin1_alphanumeric --protect
echo   sample-app-protection.bat --input_data "VðÈuXñ5_À+Áîg1ÿ¹º»¼½¾¿12ÔP1ëÕÖlgxÏHóFÚ6O3W" --policy_user superuser --data_element fpe_latin1_alphanumeric --unprotect
echo   sample-app-protection.bat --input_data "John Smith" --policy_user hr --data_element mask --unprotect
echo   sample-app-protection.bat --input_data "John Smith" --policy_user superuser --data_element no_encryption --protect
echo   sample-app-protection.bat --input_data "John Smith" --policy_user superuser --data_element no_encryption --unprotect
goto :eof

:checkjar
REM Check if JAR exists
if not exist "%JAR_FILE%" (
    echo Building the project...
    cd /d "%SCRIPT_DIR%"
    call mvnw.cmd clean package -q
)

echo Running SampleAppProtection...
echo ========================================
java -cp "%JAR_FILE%" %MAIN_CLASS% %*
