@echo off
echo ========================================
echo    D1 SCRAPER - EJECUCION RAPIDA
echo ========================================
echo.

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Ejecutar scraper
python -c "
print('🚀 INICIANDO D1 SCRAPER...')
print('=' * 50)

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

try:
    from app.scraping.d1_scraper import D1Scraper
    
    # Crear scraper
    scraper = D1Scraper()
    
    # Scrapear frutas y verduras
    print('\\n🍎 Scrapeando Frutas y Verduras...')
    productos = scraper.scrape_category('frutas-verduras', max_products=15)
    
    if productos:
        print(f'✅ {len(productos)} productos encontrados:\\n')
        
        for i, p in enumerate(productos[:10], 1):
            nombre = p['name'][:30] + '...' if len(p['name']) > 30 else p['name']
            print(f'{i:2d}. {nombre:33} - ${p[\"price\"]:8,.0f}')
        
        if len(productos) > 10:
            print(f'   ... y {len(productos) - 10} productos más')
        
        # Guardar
        import json
        from datetime import datetime
        
        datos = {
            'fecha': datetime.now().isoformat(),
            'categoria': 'Frutas y Verduras',
            'productos': productos
        }
        
        with open('productos_d1.json', 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        print('\\n💾 Resultados guardados en productos_d1.json')
    else:
        print('❌ No se encontraron productos')
        
except Exception as e:
    print(f'\\n❌ Error: {e}')
    import traceback
    traceback.print_exc()
"

echo.
echo ========================================
echo    SCRAPING COMPLETADO
echo ========================================
pause