import os
import uuid
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def crear_usuario():
    """Crear un usuario de prueba en PostgreSQL"""
    try:
        # Conectar a PostgreSQL
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Datos del usuario
        telegram_id = 123456789  # Cámbialo por tu ID de Telegram
        user_id = str(uuid.uuid4())
        nombre = "Usuario Prueba"
        email = "test@example.com"
        telefono = "3001234567"
        
        # Verificar si ya existe
        cur.execute("SELECT usuario_id FROM usuarios WHERE telegram_id = %s", (telegram_id,))
        if cur.fetchone():
            print(f"❌ El usuario con telegram_id {telegram_id} ya existe")
            return
        
        # Insertar usuario
        cur.execute("""
            INSERT INTO usuarios (
                usuario_id, nombre, email, telefono, rol_id, 
                telegram_id, activo, fecha_registro
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            user_id, nombre, email, telefono, 2,
            telegram_id, True, datetime.now()
        ))
        
        conn.commit()
        print(f"✅ Usuario creado exitosamente!")
        print(f"   ID: {user_id}")
        print(f"   Nombre: {nombre}")
        print(f"   Telegram ID: {telegram_id}")
        print(f"   Email: {email}")
        
        cur.close()
        conn.close()
        
        return user_id
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def listar_usuarios():
    """Listar todos los usuarios"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        cur.execute("""
            SELECT usuario_id, nombre, email, telegram_id, activo, fecha_registro 
            FROM usuarios 
            ORDER BY fecha_registro DESC
        """)
        
        usuarios = cur.fetchall()
        
        print("\n📋 USUARIOS REGISTRADOS:")
        print("-" * 80)
        for u in usuarios:
            print(f"ID: {u[0][:8]}... | Nombre: {u[1]} | Telegram: {u[3]} | Activo: {u[4]} | Fecha: {u[5]}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error listando usuarios: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("👤 CREAR USUARIO DE PRUEBA")
    print("=" * 50)
    
    # Crear usuario
    crear_usuario()
    
    # Listar usuarios
    listar_usuarios()