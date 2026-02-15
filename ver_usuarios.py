# ver_usuarios.py
import sqlite3
import json
from datetime import datetime
from pathlib import Path

def ver_usuarios():
    """Ver todos los usuarios de la base de datos"""
    db_path = Path('nutrichat.db')
    
    if not db_path.exists():
        print("❌ Base de datos no encontrada")
        return
    
    conn = sqlite3.connect('nutrichat.db')
    conn.row_factory = sqlite3.Row  # Para acceso por nombre de columna
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("👥 USUARIOS REGISTRADOS - NUTRICHAT")
    print("="*80)
    
    # 1. Verificar que existe la tabla usuarios
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
    if not cursor.fetchone():
        print("❌ La tabla 'usuarios' no existe")
        conn.close()
        return
    
    # 2. Contar usuarios
    cursor.execute("SELECT COUNT(*) as total FROM usuarios")
    total = cursor.fetchone()['total']
    print(f"📊 Total de usuarios: {total}")
    
    # 3. Ver usuarios activos
    cursor.execute("SELECT COUNT(*) as activos FROM usuarios WHERE activo = 1")
    activos = cursor.fetchone()['activos']
    print(f"✅ Usuarios activos: {activos}")
    
    print("\n" + "="*80)
    print("📋 LISTA DETALLADA DE USUARIOS:")
    print("="*80)
    
    # 4. Obtener todos los usuarios con detalles
    cursor.execute("""
        SELECT 
            usuario_id,
            nombre,
            email,
            telefono,
            telegram_id,
            rol_id,
            activo,
            fecha_registro
        FROM usuarios 
        ORDER BY fecha_registro DESC
    """)
    
    usuarios = cursor.fetchall()
    
    if not usuarios:
        print("No hay usuarios registrados")
    else:
        print(f"\n{'ID':<36} {'Nombre':<20} {'Email':<25} {'Telegram':<12} {'Estado':<10} {'Registro':<20}")
        print("-"*125)
        
        for usuario in usuarios:
            usuario_id = usuario['usuario_id']
            nombre = usuario['nombre'] or 'Sin nombre'
            email = usuario['email'] or 'Sin email'
            telefono = usuario['telefono'] or 'Sin teléfono'
            telegram_id = usuario['telegram_id'] or 'Sin Telegram'
            rol = 'Admin' if usuario['rol_id'] == 1 else 'Usuario'
            estado = '✅ Activo' if usuario['activo'] == 1 else '❌ Inactivo'
            
            # Formatear fecha
            fecha = usuario['fecha_registro']
            if fecha:
                try:
                    fecha_str = fecha[:19].replace('T', ' ') if 'T' in str(fecha) else str(fecha)[:19]
                except:
                    fecha_str = str(fecha)
            else:
                fecha_str = 'Sin fecha'
            
            print(f"{usuario_id:<36} {nombre:<20} {email[:24]:<25} {telegram_id:<12} {estado:<10} {fecha_str:<20}")
    
    print("\n" + "="*80)
    print("📊 ESTADÍSTICAS ADICIONALES:")
    print("="*80)
    
    # 5. Productos por usuario
    print("\n📦 PRODUCTOS POR USUARIO:")
    cursor.execute("""
        SELECT 
            u.nombre,
            COUNT(p.id) as total_productos,
            SUM(p.price) as valor_total
        FROM usuarios u
        LEFT JOIN user_products p ON u.usuario_id = p.user_id
        GROUP BY u.usuario_id
        ORDER BY total_productos DESC
    """)
    
    for row in cursor.fetchall():
        nombre = row['nombre'] or 'Usuario'
        productos = row['total_productos'] or 0
        valor = row['valor_total'] or 0
        if productos > 0:
            print(f"  • {nombre}: {productos} productos (${valor:,.0f})")
        else:
            print(f"  • {nombre}: {productos} productos")
    
    # 6. Sesiones de scraping por usuario
    print("\n🔄 SESIONES DE SCRAPING POR USUARIO:")
    cursor.execute("""
        SELECT 
            u.nombre,
            COUNT(s.id) as total_sesiones,
            SUM(s.new_products) as productos_totales
        FROM usuarios u
        LEFT JOIN scraping_sessions s ON u.usuario_id = s.user_id
        GROUP BY u.usuario_id
        ORDER BY total_sesiones DESC
    """)
    
    for row in cursor.fetchall():
        nombre = row['nombre'] or 'Usuario'
        sesiones = row['total_sesiones'] or 0
        productos = row['productos_totales'] or 0
        if sesiones > 0:
            print(f"  • {nombre}: {sesiones} sesiones ({productos} productos)")
        else:
            print(f"  • {nombre}: {sesiones} sesiones")
    
    # 7. Mostrar el último usuario registrado
    print("\n" + "="*80)
    print("👤 ÚLTIMO USUARIO REGISTRADO:")
    cursor.execute("""
        SELECT 
            usuario_id,
            nombre,
            email,
            telegram_id,
            fecha_registro
        FROM usuarios 
        ORDER BY fecha_registro DESC 
        LIMIT 1
    """)
    
    ultimo = cursor.fetchone()
    if ultimo:
        print(f"  ID: {ultimo['usuario_id']}")
        print(f"  Nombre: {ultimo['nombre']}")
        print(f"  Email: {ultimo['email'] or 'No tiene'}")
        print(f"  Telegram ID: {ultimo['telegram_id']}")
        print(f"  Fecha registro: {ultimo['fecha_registro']}")
    
    conn.close()
    
    # 8. Exportar a JSON si quieres
    exportar = input("\n¿Exportar a JSON? (s/n): ")
    if exportar.lower() == 's':
        usuarios_list = []
        conn = sqlite3.connect('nutrichat.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM usuarios")
        usuarios = cursor.fetchall()
        
        for usuario in usuarios:
            usuario_dict = dict(usuario)
            usuarios_list.append(usuario_dict)
        
        with open('usuarios_nutrichat.json', 'w', encoding='utf-8') as f:
            json.dump(usuarios_list, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ Usuarios exportados a 'usuarios_nutrichat.json'")
        conn.close()

if __name__ == "__main__":
    ver_usuarios()