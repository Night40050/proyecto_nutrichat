@echo off
chcp 65001 > nul
echo ========================================
echo 🚀 INICIADOR DE SCRAPING NUTRICHAT
echo ========================================
echo.

REM Activar entorno virtual si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo ✅ Entorno virtual activado
)

REM Verificar Tesseract
python -c "import pytesseract; print(f'✅ Tesseract configurado: {pytesseract.pytesseract.tesseract_cmd}')"

echo.
echo 📊 OPCIONES:
echo   1. Probar scraping rápido
echo   2. Ejecutar servidor completo
echo   3. Verificar sistema
echo.

set /p choice="Selecciona opción [1-3]: "

if "%choice%"=="1" (
    echo.
    echo 🧪 Probando scraping...
    python -c "from app.scraper.d1_scraper import test_scraping; test_scraping()"
    pause
    exit
)

if "%choice%"=="2" (
    echo.
    echo 🚀 Iniciando servidor completo...
    python run.py
)

if "%choice%"=="3" (
    echo.
    echo 🔍 Verificando sistema...
    python check_system.py
    pause
    exit
)

echo Opción no válida
pause