@echo off
REM ============================================================
REM  Gemini Watermark Remover
REM  Usage: remove_watermark.bat "path\to\image.png"
REM  Output: same folder, same name + _removed suffix
REM ============================================================

if "%~1"=="" (
    echo Usage: remove_watermark.bat "path\to\image"
    echo.
    echo   Removes the Gemini watermark from the provided image.
    echo   Saves the result in the same folder with _removed appended.
    echo   Example: remove_watermark.bat "D:\Photos\my_image.png"
    exit /b 1
)

set INPUT=%~1
set DIR=%~dp1
set BASE=%~n1
set EXT=%~x1
set OUTPUT=%DIR%%BASE%_removed%EXT%

echo Input:  %INPUT%
echo Output: %OUTPUT%
echo.

python "%~dp0remove_watermark.py" "%INPUT%" "%OUTPUT%"
