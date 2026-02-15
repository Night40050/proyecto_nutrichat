"""
API de scraping para NutriChat - CONECTA CON TU SCRAPER REAL d1_scraper.py
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape(category_id=1, mode='auto', session_id=None, user_id=None):
    """
    Conecta con TU scraper REAL d1_scraper.py
    """
    try:
        logger.info(f"🚀 Iniciando scraping REAL para usuario {user_id}, categoría {category_id}")
        
        # Mapeo de categorías (1: Frutas y Verduras, etc.)
        categories = {
            1: "Frutas y Verduras",
            2: "Lácteos y Huevos",
            3: "Carnes y Pescados",
            4: "Despensa",
            5: "Aseo y Hogar",
            6: "Bebidas",
            7: "Panadería y Pastelería"
        }
        
        category_name = categories.get(category_id, "Frutas y Verduras")
        
        # IMPORTAR TU SCRAPER REAL
        try:
            # Asegurar que el directorio actual está en el path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            logger.info(f"📂 Importando desde: {current_dir}/d1_scraper.py")
            
            # Importar d1_scraper
            import d1_scraper
            
            # Verificar que la clase existe
            if not hasattr(d1_scraper, 'D1ScraperV8'):
                logger.error("❌ Clase D1ScraperV8 no encontrada")
                available_classes = [attr for attr in dir(d1_scraper) if attr.startswith('D1')]
                logger.info(f"Clases disponibles: {available_classes}")
                return {
                    'success': False,
                    'error': f'Clase D1ScraperV8 no encontrada. Clases: {available_classes}'
                }
            
            logger.info(f"✅ Scraper importado correctamente")
            
        except ImportError as e:
            logger.error(f"❌ Error importando d1_scraper: {e}")
            return {
                'success': False,
                'error': f'No se pudo importar d1_scraper.py: {str(e)}'
            }
        
        # Crear instancia del scraper
        scraper = d1_scraper.D1ScraperV8()
        
        # Ejecutar scraping según el modo
        products = []
        
        if mode == 'auto':
            logger.info(f"🔍 Modo AUTO para categoría: {category_name}")
            products = scraper.scrape_category_auto(category_name)
            
        elif mode == 'manual':
            logger.info(f"🔍 Modo MANUAL para categoría: {category_name}")
            products = scraper.scrape_category_manual(category_name)
            
        else:
            logger.info(f"🔍 Usando modo por defecto")
            products = scraper.scrape_category_auto(category_name)
        
        # ===== GUARDAR EN USER_PRODUCTS =====
        if products and user_id:
            try:
                logger.info(f"💾 Guardando {len(products)} productos en user_products para usuario {user_id}")
                scraper.save_to_user_products(products, user_id)
                logger.info(f"✅ Productos guardados exitosamente en user_products")
            except Exception as e:
                logger.error(f"❌ Error guardando en user_products: {e}")
                import traceback
                traceback.print_exc()
        # ===== FIN GUARDAR =====
        
        # Cerrar scraper
        if hasattr(scraper, 'close'):
            scraper.close()
        
        # Verificar productos
        if not products or len(products) == 0:
            logger.warning("⚠️ No se encontraron productos")
            products = []
        
        logger.info(f"✅ Scraper encontró {len(products)} productos")
        
        # Guardar resultados en archivo
        if session_id:
            results_dir = Path('scraping_results_v8/data')
            results_dir.mkdir(parents=True, exist_ok=True)
            
            results_file = results_dir / f'products_{session_id}.json'
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'session_id': session_id,
                    'user_id': user_id,
                    'category': category_name,
                    'category_id': category_id,
                    'mode': mode,
                    'timestamp': datetime.now().isoformat(),
                    'products': products
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Resultados guardados en {results_file}")
        
        # Calcular totales
        total_value = sum(p.get('price', 0) for p in products if p.get('price'))
        
        return {
            'success': True,
            'message': f'Scraping completado: {len(products)} productos',
            'total_products': len(products),
            'new_products': len(products),
            'updated_products': 0,
            'total_value': total_value,
            'products': products
        }
        
    except Exception as e:
        logger.error(f"❌ Error en scraping: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }