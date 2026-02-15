import sys
import os

# Agregar el directorio raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importar del archivo REAL que existe
from app.scraping.scraping_api import scrape

# Probar con el usuario Julia Test
user_id = "2618902a-4722-4b61-9245-366da6ef8962"
print("🧪 TEST DE SCRAPING - VERSIÓN CORREGIDA")
print("="*60)
result = scrape(category_id=1, mode='auto', user_id=user_id)
print("\n" + "="*60)
print("RESULTADO DEL TEST:")
print(f"✅ Success: {result['success']}")
print(f"📝 Mensaje: {result['message']}")
print(f"📦 Productos: {result['total_products']}")
print(f"💰 Valor total: ${result.get('total_value', 0):,}")
print("="*60)

# Verificar en la base de datos
import sqlite3
conn = sqlite3.connect('nutrichat.db')
c = conn.cursor()

# Contar productos
c.execute('SELECT COUNT(*) FROM user_products WHERE user_id=?', (user_id,))
total = c.fetchone()[0]
print(f"\n📊 Productos totales en BD: {total}")

if total > 0:
    # Mostrar últimos 5 productos
    c.execute('''
        SELECT name, price, category, description, created_at 
        FROM user_products 
        WHERE user_id=? 
        ORDER BY id DESC 
        LIMIT 5
    ''', (user_id,))
    
    print("\n📋 ÚLTIMOS 5 PRODUCTOS:")
    for row in c.fetchall():
        name, price, category, description, created_at = row
        print(f"  • {name} (${price:,}) - {category}")
        if description:
            print(f"    📝 {description}")
        if created_at:
            print(f"    📅 {created_at[:19]}")
        print()

conn.close()