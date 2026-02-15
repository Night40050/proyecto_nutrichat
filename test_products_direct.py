# test_products_direct.py
import sqlite3

def test_direct_query():
    """Prueba directa de la consulta SQL"""
    print("🧪 PRUEBA DIRECTA DE CONSULTA SQL")
    print("="*60)
    
    conn = sqlite3.connect('nutrichat.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # User ID de Julia Test
    user_id = "2618902a-4722-4b61-9245-366da6ef8962"
    
    print(f"🔍 User ID: {user_id}")
    
    # Primero verificar que el usuario existe
    c.execute("SELECT usuario_id, nombre FROM usuarios WHERE usuario_id = ?", (user_id,))
    user = c.fetchone()
    
    if not user:
        print("❌ Usuario no encontrado")
        return
    
    print(f"✅ Usuario encontrado: {user['nombre']}")
    
    # Intentar la misma consulta que la API
    query = """
        SELECT 
            id,
            name,
            category,
            price,
            COALESCE(
                description,
                notes,
                ''
            ) as description,
            source,
            COALESCE(
                added_date,
                created_at,
                '2000-01-01'
            ) as created_at,
            COALESCE(
                last_updated,
                updated_at,
                '2000-01-01'
            ) as updated_at
        FROM user_products 
        WHERE user_id = ?
        ORDER BY 
            COALESCE(added_date, created_at, '2000-01-01') DESC
    """
    
    print(f"\n🔍 Ejecutando consulta...")
    print(f"SQL: {query[:100]}...")
    
    try:
        c.execute(query, (user_id,))
        results = c.fetchall()
        
        print(f"✅ Consulta exitosa")
        print(f"📊 Resultados: {len(results)} filas")
        
        if results:
            print("\n📋 PRIMEROS 3 PRODUCTOS:")
            for i, row in enumerate(results[:3]):
                print(f"\n{i+1}. {row['name']} (${row['price']})")
                print(f"   Categoría: {row['category']}")
                print(f"   Descripción: {row['description'][:50]}...")
                print(f"   Fuente: {row['source']}")
                print(f"   Creado: {row['created_at']}")
        else:
            print("⚠️ No se encontraron productos para este usuario")
            
    except Exception as e:
        print(f"❌ Error en consulta: {e}")
        import traceback
        traceback.print_exc()
    
    conn.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    test_direct_query()