"""
D1 Scraper v8.0 - Captura Inteligente con Detección Visual
Script principal para ejecución desde línea de comandos y API
"""

import os
import sys
import time
import json
import re
import csv
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess

# Configurar el path para importaciones
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# Instalar dependencias automáticamente si faltan
def install_required():
    """Instala dependencias si no están disponibles"""
    required = ['selenium', 'pytesseract', 'Pillow', 'pyautogui']
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            print(f"📦 Instalando {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# Llamar a install_required solo cuando se ejecuta directamente
if __name__ == "__main__":
    install_required()

# Importar después de instalar
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import pyautogui

class D1ScraperV8:
    """Scraper v8.0 con detección visual inteligente"""
    
    def __init__(self):
        self.base_url = "https://domicilios.tiendasd1.com/search?name=frutas"
        self.results_dir = Path("scraping_results_v8")
        self.screenshots_dir = self.results_dir / "screenshots"
        self.data_dir = self.results_dir / "data"
        
        for d in [self.results_dir, self.screenshots_dir, self.data_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Configurar Tesseract
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"✅ Tesseract configurado en: {tesseract_path}")
        else:
            print("⚠️  Tesseract no encontrado, usando ubicación por defecto")
        
        # Driver (se inicializa cuando se necesita)
        self.driver = None
        
        # Categorías de D1
        self.CATEGORIES = [
            'Frutas y Verduras',
            'Lácteos y Huevos', 
            'Carnes y Pescados',
            'Despensa',
            'Aseo y Hogar',
            'Bebidas',
            'Panadería y Pastelería'
        ]
        
        self.category_slugs = {
            'Frutas y Verduras': 'frutas-verduras',
            'Lácteos y Huevos': 'lacteos-huevos',
            'Carnes y Pescados': 'carnes-pescados',
            'Despensa': 'despensa',
            'Aseo y Hogar': 'aseo-hogar', 
            'Bebidas': 'bebidas',
            'Panadería y Pastelería': 'panaderia-pasteleria'
        }
    
    def setup_driver(self):
        """Configura Chrome con opciones optimizadas"""
        if self.driver:
            return self.driver
            
        print("🚀 Configurando navegador Chrome...")
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return self.driver
    
    def smart_navigation(self, category_name: str):
        """Navegación inteligente para cargar productos"""
        if category_name not in self.category_slugs:
            print(f"❌ Categoría no válida: {category_name}")
            return False
            
        category_slug = self.category_slugs[category_name]
        print(f"\n🌐 Navegando a {category_name}...")
        
        url = f"{self.base_url}/search?category={category_slug}"
        self.driver.get(url)
        time.sleep(4)
        
        # Cerrar popups
        self.close_popups()
        
        # Estrategia de scroll inteligente
        print("📜 Cargando productos...")
        
        # Scroll suave en secciones
        for i in range(4):
            self.driver.execute_script(f"window.scrollBy(0, {400});")
            time.sleep(1.2)
            
            # Pausa más larga después del segundo scroll
            if i == 1:
                time.sleep(2)
        
        # Volver un poco arriba para mejor composición
        self.driver.execute_script("window.scrollBy(0, -200);")
        time.sleep(2)
        
        print("✅ Página lista para captura")
        return True
    
    def close_popups(self):
        """Cierra popups comunes"""
        try:
            # Buscar botones de cerrar/aceptar
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons:
                try:
                    text = btn.text.lower()
                    if any(word in text for word in ['aceptar', 'entendido', 'continuar', 'ok']):
                        btn.click()
                        time.sleep(1)
                        print("✅ Popup cerrado")
                        break
                except:
                    continue
        except:
            pass
    
    def find_products_visually(self):
        """
        Encuentra visualmente dónde están los productos en la pantalla
        usando píxeles rojos (precios en D1 son rojos)
        """
        print("🔍 Buscando productos visualmente...")
        
        # 1. Tomar captura de toda la pantalla
        screenshot = pyautogui.screenshot()
        
        # 2. Convertir a RGB para análisis
        pixels = screenshot.load()
        width, height = screenshot.size
        
        # 3. Buscar píxeles rojos (precios D1 son rojos: ~ RGB(200, 0-50, 0-50))
        red_regions = []
        
        # Escanear la pantalla en pasos para ser más rápido
        step = 5
        for y in range(200, height - 200, step):  # Evitar bordes
            for x in range(100, width - 100, step):
                r, g, b = pixels[x, y]
                
                # Detectar rojo D1: R alto, G y B bajos
                if r > 180 and g < 100 and b < 100:
                    # Verificar que no sea un píxel aislado
                    red_regions.append((x, y))
        
        print(f"   📍 {len(red_regions)} puntos rojos encontrados (posibles precios)")
        
        if len(red_regions) < 5:
            print("⚠️  Pocos precios detectados, usando área por defecto")
            return None
        
        # 4. Agrupar regiones cercanas
        from collections import defaultdict
        
        # Agrupar por coordenada Y (misma fila de productos)
        y_groups = defaultdict(list)
        for x, y in red_regions:
            # Redondear Y a múltiplos de 100 para agrupar por filas
            y_group = (y // 100) * 100
            y_groups[y_group].append((x, y))
        
        # 5. Encontrar las filas con más precios (probablemente filas de productos)
        product_rows = []
        for y_group, points in y_groups.items():
            if len(points) >= 3:  # Al menos 3 precios en la misma fila
                product_rows.append(y_group)
        
        if product_rows:
            product_rows.sort()
            print(f"   📊 {len(product_rows)} filas de productos identificadas")
            
            # Calcular área que contiene todas las filas
            min_y = min(product_rows) - 80  # Margen arriba
            max_y = max(product_rows) + 200  # Margen abajo
            
            # Coordenadas X (márgenes izquierdo/derecho)
            left = 100
            right = width - 100
            
            return (left, min_y, right - left, max_y - min_y)
        
        return None
    
    def capture_best_area(self, category_name: str) -> Optional[Path]:
        """
        Captura el mejor área donde están los productos
        """
        print("📸 Capturando área óptima...")
        
        # Intentar detección visual primero
        area = self.find_products_visually()
        
        if area:
            left, top, width, height = area
            print(f"   🎯 Área detectada: {width}x{height} pixels")
        else:
            # Área por defecto (centro de la pantalla)
            screen_width, screen_height = pyautogui.size()
            left = 150
            top = 200
            width = screen_width - 300
            height = screen_height - 350
            print(f"   📍 Usando área por defecto: {width}x{height}")
        
        # Tomar captura
        time.sleep(1)  # Esperar estabilización
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        
        # Guardar
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"d1_{category_name.replace(' ', '_')}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        
        screenshot.save(filepath)
        print(f"✅ Captura guardada: {filename}")
        
        return filepath
    
    def enhanced_ocr_for_d1(self, image_path: Path) -> str:
        """
        OCR mejorado específicamente para formato D1
        """
        print("🔍 Procesando imagen con OCR mejorado...")
        
        # Abrir imagen
        image = Image.open(image_path)
        
        # PRIMERA PASADA: OCR normal
        text1 = pytesseract.image_to_string(image, config='--psm 6', lang='spa')
        
        # SEGUNDA PASADA: Preprocesamiento para texto D1
        # 1. Convertir a blanco y negro con alto contraste
        gray = image.convert('L')
        enhancer = ImageEnhance.Contrast(gray)
        high_contrast = enhancer.enhance(3.0)
        
        # 2. Umbral para hacer texto más nítido
        threshold = 150
        binary = high_contrast.point(lambda p: 255 if p > threshold else 0)
        
        # 3. Guardar imagen procesada
        processed_path = self.screenshots_dir / f"processed_{image_path.name}"
        binary.save(processed_path)
        
        # 4. OCR en imagen procesada
        text2 = pytesseract.image_to_string(binary, config='--psm 6', lang='spa')
        
        # 5. Combinar resultados (usar el más largo)
        if len(text2) > len(text1):
            final_text = text2
        else:
            final_text = text1
        
        # Guardar texto extraído
        text_path = self.data_dir / f"ocr_{datetime.now().strftime('%H%M%S')}.txt"
        text_path.write_text(final_text, encoding='utf-8')
        
        print(f"✅ {len(final_text)} caracteres extraídos")
        
        # Mostrar líneas con precios para debug
        lines = final_text.split('\n')
        price_lines = [line for line in lines if '$' in line or re.search(r'\d{3,}', line)]
        
        if price_lines:
            print(f"   📄 {len(price_lines)} líneas con posibles precios:")
            for i, line in enumerate(price_lines[:8], 1):
                print(f"   {i:2d}. {line.strip()}")
        
        return final_text
    
    def extract_products_from_text(self, text: str, category: str) -> List[Dict[str, Any]]:
        """
        Extrae productos del texto usando múltiples estrategias
        """
        products = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        print(f"🔍 Analizando {len(lines)} líneas...")
        
        # ESTRATEGIA 1: Buscar patrones tipo "PRECIO NOMBRE" o "NOMBRE PRECIO"
        for i, line in enumerate(lines):
            # Patrones comunes en D1
            patterns = [
                # Formato: $ 6.500 NOMBRE
                (r'\$\s*(\d[\d\.,]*)\s+(.+)', 'price_first'),
                # Formato: NOMBRE $ 6.500
                (r'(.+?)\s+\$\s*(\d[\d\.,]*)', 'name_first'),
                # Formato: solo precio seguido de nombre en línea siguiente
                (r'\$\s*(\d[\d\.,]*)', 'price_only'),
            ]
            
            for pattern, pattern_type in patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        if pattern_type == 'price_first':
                            price_str = match.group(1)
                            name = match.group(2)
                        elif pattern_type == 'name_first':
                            name = match.group(1)
                            price_str = match.group(2)
                        elif pattern_type == 'price_only':
                            price_str = match.group(1)
                            # Buscar nombre en línea siguiente
                            if i + 1 < len(lines):
                                name = lines[i + 1]
                            else:
                                continue
                        
                        # Convertir precio
                        price = self.parse_price(price_str)
                        
                        if price and self.is_valid_product_name(name):
                            product = {
                                'id': f"d1_{hash(name) % 1000000:06d}",
                                'name': name,
                                'price': price,
                                'price_display': f"${price_str}",
                                'category': category,
                                'store': 'Tiendas D1',
                                'scraped_at': datetime.now().isoformat(),
                                'source': 'ocr'
                            }
                            products.append(product)
                            print(f"   ✅ {name[:25]}... - ${price:,}")
                            break
                    
                    except:
                        continue
        
        # ESTRATEGIA 2: Buscar líneas consecutivas que parezcan productos
        if len(products) < 3:
            for i in range(len(lines) - 1):
                line1, line2 = lines[i], lines[i + 1]
                
                # Si una línea tiene precio y la otra parece nombre
                has_price1 = bool(re.search(r'\$\s*\d', line1))
                has_price2 = bool(re.search(r'\$\s*\d', line2))
                
                if has_price1 and not has_price2 and self.is_valid_product_name(line2):
                    price_match = re.search(r'\$\s*(\d[\d\.,]*)', line1)
                    if price_match:
                        price = self.parse_price(price_match.group(1))
                        if price:
                            product = {
                                'id': f"d1_line_{i:04d}",
                                'name': line2,
                                'price': price,
                                'category': category,
                                'store': 'Tiendas D1',
                                'scraped_at': datetime.now().isoformat(),
                                'source': 'line_pair'
                            }
                            products.append(product)
        
        print(f"✅ {len(products)} productos extraídos del OCR")
        return products
    
    def parse_price(self, price_str: str) -> Optional[float]:
        """Convierte string de precio a float"""
        try:
            # Limpiar
            clean = price_str.replace('$', '').strip()
            
            # Si tiene puntos de miles y coma decimal: "6.500,00" -> 6500.00
            if '.' in clean and ',' in clean:
                # Formato europeo: 6.500,00
                parts = clean.split(',')
                integer_part = parts[0].replace('.', '')
                if len(parts) > 1:
                    return float(f"{integer_part}.{parts[1]}")
                else:
                    return float(integer_part)
            
            # Si solo tiene coma: "6,500" o "6,50"
            elif ',' in clean:
                # Verificar si es decimal o separador de miles
                if clean.count(',') == 1 and len(clean.split(',')[1]) <= 2:
                    # Probable decimal: "6,50" -> 6.50
                    return float(clean.replace(',', '.'))
                else:
                    # Separador de miles: "6,500" -> 6500
                    return float(clean.replace(',', ''))
            
            # Si solo tiene punto: "6500.00" o "6.500"
            elif '.' in clean:
                # Verificar si es decimal o separador de miles
                parts = clean.split('.')
                if len(parts[-1]) <= 2:
                    # Decimal: "6500.50" -> 6500.50
                    return float(clean)
                else:
                    # Separador de miles: "6.500" -> 6500
                    return float(clean.replace('.', ''))
            
            # Solo números: "6500"
            else:
                return float(clean)
                
        except:
            return None
    
    def is_valid_product_name(self, name: str) -> bool:
        """Verifica si un string parece un nombre válido de producto"""
        if not name or len(name) < 3:
            return False
        
        # No debe ser principalmente números
        if re.match(r'^\d+$', name):
            return False
        
        # No debe contener palabras comunes de interfaz
        interface_words = ['buscar', 'carrito', 'categoría', 'iniciar', 'sesión', 
                          'domicilio', 'tienda', 'menú', 'logo']
        name_lower = name.lower()
        
        for word in interface_words:
            if word in name_lower:
                return False
        
        # Debe contener al menos una letra
        if not re.search(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]', name):
            return False
        
        return True
    
    def get_real_products_from_page(self) -> List[Dict[str, Any]]:
        """
        Intenta extraer productos directamente de la página usando JavaScript
        """
        print("🔍 Intentando extracción directa desde la página...")
        
        try:
            # Ejecutar JavaScript para obtener elementos visibles
            script = """
            var products = [];
            var elements = document.querySelectorAll('div, article, li, section');
            
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                var text = el.innerText || el.textContent;
                
                // Buscar elementos que contengan signo de dólar y texto
                if (text && text.includes('$') && text.length > 10 && text.length < 200) {
                    var rect = el.getBoundingClientRect();
                    
                    // Solo elementos visibles en la pantalla
                    if (rect.width > 0 && rect.height > 0) {
                        products.push({
                            text: text.trim(),
                            top: rect.top,
                            left: rect.left
                        });
                    }
                }
            }
            
            // Ordenar por posición vertical
            products.sort(function(a, b) {
                return a.top - b.top;
            });
            
            return products.map(function(p) { return p.text; });
            """
            
            product_texts = self.driver.execute_script(script)
            
            if product_texts and len(product_texts) > 0:
                print(f"✅ {len(product_texts)} elementos con precios encontrados en página")
                
                # Procesar textos
                products = []
                seen_names = set()
                
                for text in product_texts[:20]:  # Limitar a 20
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    # Buscar precio en el texto
                    for line in lines:
                        price_match = re.search(r'\$\s*(\d[\d\.,]*)', line)
                        if price_match:
                            price = self.parse_price(price_match.group(1))
                            if price:
                                # Buscar nombre (puede ser la misma línea o anterior)
                                name = ""
                                
                                # Intentar extraer nombre de la misma línea
                                if len(line) > len(price_match.group()):
                                    potential_name = line.replace(price_match.group(), '').strip()
                                    if self.is_valid_product_name(potential_name):
                                        name = potential_name
                                
                                # Si no, buscar en líneas cercanas
                                if not name and len(lines) > 1:
                                    for other_line in lines:
                                        if other_line != line and self.is_valid_product_name(other_line):
                                            name = other_line
                                            break
                                
                                if name and price:
                                    # Evitar duplicados por nombre
                                    name_key = name.lower()[:30]
                                    if name_key not in seen_names:
                                        seen_names.add(name_key)
                                        products.append({
                                            'id': f"d1_js_{hash(name) % 1000000:06d}",
                                            'name': name,
                                            'price': price,
                                            'category': 'Extraído de página',
                                            'store': 'Tiendas D1',
                                            'scraped_at': datetime.now().isoformat(),
                                            'source': 'javascript'
                                        })
                                        print(f"   ✅ {name[:25]}... - ${price:,}")
                                    break
                
                print(f"✅ Total: {len(products)} productos extraídos de la página")
                return products
            
        except Exception as e:
            print(f"⚠️  Error en extracción JS: {e}")
        
        return []
    
    def scrape_category_auto(self, category_name: str) -> List[Dict[str, Any]]:
        """Ejecuta scraping automático para una categoría"""
        print(f"\n🎯 Iniciando scraping automático para: {category_name}")
        all_products = []
        
        try:
            # 1. Configurar driver
            self.setup_driver()
            
            # 2. Navegar
            if not self.smart_navigation(category_name):
                print("❌ Error en navegación")
                return []
            
            # 3. Intentar extracción directa desde JavaScript
            js_products = self.get_real_products_from_page()
            if js_products:
                all_products.extend(js_products)
            
            # 4. Captura y OCR
            if len(all_products) < 5:  # Si no extrajo suficientes
                screenshot_path = self.capture_best_area(category_name)
                
                if screenshot_path:
                    # OCR
                    ocr_text = self.enhanced_ocr_for_d1(screenshot_path)
                    
                    # Extraer productos del OCR
                    ocr_products = self.extract_products_from_text(ocr_text, category_name)
                    all_products.extend(ocr_products)
            
            # 5. Procesar resultados
            if all_products:
                # Eliminar duplicados
                unique_products = []
                seen = set()
                
                for product in all_products:
                    key = (product['name'].lower(), product['price'])
                    if key not in seen:
                        seen.add(key)
                        unique_products.append(product)
                
                # Asignar categoría correcta
                for product in unique_products:
                    product['category'] = category_name
                
                # Mostrar resultados
                self.display_results(unique_products, category_name)
                
                # Guardar
                self.save_results(unique_products, category_name)
                
                return unique_products
            else:
                print("❌ No se encontraron productos")
                return []
                
        except Exception as e:
            print(f"❌ Error en scraping automático: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            self.close()
    
    def scrape_category_manual(self, category_name: str, image_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scraping manual desde una imagen"""
        print(f"\n🎯 Modo manual para: {category_name}")
        
        if image_path and os.path.exists(image_path):
            # Procesar imagen proporcionada
            screenshot_path = Path(image_path)
        else:
            # Capturar imagen de la pantalla
            self.setup_driver()
            self.smart_navigation(category_name)
            screenshot_path = self.capture_best_area(category_name)
            self.close()
        
        # Procesar con OCR
        ocr_text = self.enhanced_ocr_for_d1(screenshot_path)
        products = self.extract_products_from_text(ocr_text, category_name)
        
        if products:
            self.display_results(products, category_name)
            self.save_results(products, category_name)
            return products
        else:
            print("❌ No se extrajeron productos del OCR")
            return []
    
    def display_results(self, products: List[Dict[str, Any]], category: str):
        """Muestra los resultados"""
        print(f"\n{'='*60}")
        print(f"✅ RESULTADOS - {category}")
        print(f"{'='*60}")
        print(f"📦 Total productos: {len(products)}")
        print(f"💰 Valor total: ${sum(p['price'] for p in products):,}")
        
        if products:
            avg_price = sum(p['price'] for p in products) / len(products)
            min_price = min(p['price'] for p in products)
            max_price = max(p['price'] for p in products)
            
            print(f"📊 Precio promedio: ${avg_price:,.0f}")
            print(f"📈 Rango: ${min_price:,} - ${max_price:,}")
            
            print(f"\n📋 PRODUCTOS ENCONTRADOS:")
            print("-" * 70)
            
            for i, p in enumerate(products[:15], 1):
                name = p['name']
                if len(name) > 40:
                    name = name[:37] + "..."
                
                # Mostrar fuente
                source = p.get('source', 'unknown')
                source_icon = '🔍' if source == 'ocr' else '⚡' if source == 'javascript' else '📋'
                
                print(f"{i:2d}. {source_icon} {name:38} ${p['price']:8,.0f}")
            
            if len(products) > 15:
                print(f"   ... y {len(products) - 15} más")
    
    def save_results(self, products: List[Dict[str, Any]], category: str):
        """Guarda resultados en JSON y CSV (VERSIÓN CORREGIDA)"""
        if not products:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_category = category.replace(' ', '_')
        
        # JSON - guardar completo
        json_data = {
            'scraper': 'D1Scraper v8.0',
            'category': category,
            'scraped_at': datetime.now().isoformat(),
            'total_products': len(products),
            'total_value': sum(p['price'] for p in products),
            'products': products
        }
        
        json_file = self.data_dir / f"d1_{safe_category}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # CSV - SOLO CAMPOS ESTÁNDAR
        csv_file = self.data_dir / f"d1_{safe_category}_{timestamp}.csv"
        if products:
            # Campos fijos para CSV (evita el error de price_display)
            fieldnames = ['name', 'price', 'category', 'store', 'source', 'id']
            
            # Limpiar productos: solo mantener campos estándar
            clean_products = []
            for p in products:
                clean_p = {}
                for field in fieldnames:
                    clean_p[field] = p.get(field, '')
                clean_products.append(clean_p)
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(clean_products)
        
        print(f"\n💾 RESULTADOS GUARDADOS:")
        print(f"   📄 JSON: {json_file}")
        print(f"   📊 CSV:  {csv_file}")
    
    # ========== NUEVA FUNCIÓN AGREGADA (SIN DAÑAR NADA) ==========
    def save_to_user_products(self, products, user_id=None):
        """
        Guarda los productos en la tabla user_products de PostgreSQL
        """
        if not products or not user_id:
            print("❌ No hay productos o user_id para guardar")
            return
        
        try:
            # Importar db aquí para evitar importación circular
            from app.models.database import db
            from sqlalchemy import text
            
            print(f"💾 Guardando {len(products)} productos en user_products para usuario {user_id}")
            
            for product in products:
                # Verificar si el producto ya existe (por nombre)
                check_query = text("""
                    SELECT id FROM user_products 
                    WHERE user_id = :user_id AND name = :name
                """)
                
                result = db.session.execute(check_query, {
                    'user_id': user_id,
                    'name': product.get('name', '')
                })
                
                existing = result.fetchone()
                
                if existing:
                    # Actualizar precio si existe
                    update_query = text("""
                        UPDATE user_products 
                        SET price = :price, last_updated = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    db.session.execute(update_query, {
                        'id': existing[0],
                        'price': product.get('price', 0)
                    })
                    print(f"🔄 Actualizado: {product.get('name')} - ${product.get('price', 0)}")
                else:
                    # Insertar nuevo producto
                    insert_query = text("""
                        INSERT INTO user_products (
                            user_id, name, category, price, source, description,
                            added_date, last_updated
                        ) VALUES (
                            :user_id, :name, :category, :price, :source, :description,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                    """)
                    
                    db.session.execute(insert_query, {
                        'user_id': user_id,
                        'name': product.get('name', 'Sin nombre'),
                        'category': product.get('category', 'General'),
                        'price': product.get('price', 0),
                        'source': 'd1_scraper',
                        'description': product.get('description', '')
                    })
                    print(f"✅ Insertado: {product.get('name')} - ${product.get('price', 0)}")
            
            db.session.commit()
            print(f"✅ {len(products)} productos guardados en user_products")
            
        except Exception as e:
            print(f"❌ Error guardando en user_products: {e}")
            db.session.rollback()
    # ========== FIN DE LA NUEVA FUNCIÓN ==========
    
    def close(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()
            print("\n✅ Navegador cerrado")
        self.driver = None

def parse_arguments():
    """Parsear argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description='D1 Scraper v8.0')
    parser.add_argument('--category', type=str, default='1',
                       help='Número o nombre de categoría (1-7 o nombre)')
    parser.add_argument('--mode', type=str, default='auto',
                       choices=['auto', 'manual', 'sample'],
                       help='Modo de ejecución: auto, manual, sample')
    parser.add_argument('--session', type=str, default='',
                       help='ID de sesión para seguimiento')
    parser.add_argument('--interactive', action='store_true',
                       help='Modo interactivo')
    return parser.parse_args()

def main():
    """Función principal para ejecución desde línea de comandos"""
    args = parse_arguments()
    
    print("=" * 60)
    print("🎯 D1 SCRAPER v8.0 - CAPTURA INTELIGENTE")
    print("=" * 60)
    
    if args.session:
        print(f"🎫 SESIÓN: {args.session}")
    
    scraper = None
    
    try:
        # Crear scraper
        scraper = D1ScraperV8()
        
        # Determinar categoría
        category_idx = 0
        category_name = scraper.CATEGORIES[0]
        
        if args.category.isdigit():
            idx = int(args.category) - 1
            if 0 <= idx < len(scraper.CATEGORIES):
                category_idx = idx
                category_name = scraper.CATEGORIES[idx]
        else:
            # Buscar por nombre
            for cat in scraper.CATEGORIES:
                if args.category.lower() in cat.lower():
                    category_name = cat
                    break
        
        # Modo sample - ELIMINADO (NO SE USA)
        if args.mode == 'sample':
            print(f"\n📋 Modo muestra no disponible - Usa auto o manual")
            return []
        
        # Modo auto
        elif args.mode == 'auto':
            print(f"\n🚀 Modo automático para: {category_name}")
            products = scraper.scrape_category_auto(category_name)
            return products
        
        # Modo manual
        elif args.mode == 'manual':
            print(f"\n📷 Modo manual para: {category_name}")
            products = scraper.scrape_category_manual(category_name)
            return products
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelado por usuario")
        return []
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if scraper:
            scraper.close()

def interactive_mode():
    """Modo interactivo para pruebas"""
    print("\n🔧 MODOS DE EJECUCIÓN:")
    print("  1. Scraping completo (Chrome + OCR + JavaScript)")
    print("  2. Ver capturas anteriores")
    
    try:
        choice = input("\n👉 Opción (1-2): ").strip()
        
        if choice == "1":
            # Modo auto
            args = argparse.Namespace(
                category='1',
                mode='auto',
                session=f"interactive_{int(time.time())}",
                interactive=False
            )
            return main()
        elif choice == "2":
            # Ver capturas
            screenshots_dir = Path("scraping_results_v8") / "screenshots"
            if screenshots_dir.exists():
                files = list(screenshots_dir.glob("*.png"))
                if files:
                    print(f"\n📁 {len(files)} capturas encontradas:")
                    for file in files[-5:]:
                        size = file.stat().st_size // 1024
                        age = datetime.fromtimestamp(file.stat().st_mtime)
                        age_str = age.strftime("%Y-%m-%d %H:%M")
                        print(f"   • {file.name} ({size} KB, {age_str})")
                else:
                    print("❌ No hay capturas")
            else:
                print("❌ No existe carpeta de capturas")
        
        else:
            print("❌ Opción inválida, ejecutando scraping completo...")
            args = argparse.Namespace(
                category='1',
                mode='auto',
                session=f"default_{int(time.time())}",
                interactive=False
            )
            return main()
    
    except KeyboardInterrupt:
        print("\n\n👋 Cancelado")
        return []

# Punto de entrada principal
if __name__ == "__main__":
    args = parse_arguments()
    
    if args.interactive:
        interactive_mode()
    else:
        main()