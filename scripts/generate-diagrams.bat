@echo off
REM Generate PlantUML diagrams using Docker

echo Generating PlantUML diagrams...

docker run --rm -v "%cd%\docs\diagrams:/data" plantuml/plantuml:latest -tpng "/data/*.puml"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ Diagrams generated successfully in docs\diagrams\
) else (
    echo.
    echo ✗ Failed to generate diagrams
    exit /b 1
)
