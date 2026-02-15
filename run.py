"""
NutriChat - Punto de entrada principal
Versión: 2.0 Professional con PostgreSQL
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar variables de entorno
os.environ.setdefault('FLASK_APP', 'run.py')
os.environ.setdefault('FLASK_ENV', os.getenv('FLASK_ENV', 'development'))
os.environ.setdefault('SECRET_KEY', os.getenv('SECRET_KEY', 'dev-secret-key'))
os.environ.setdefault('JWT_SECRET_KEY', os.getenv('JWT_SECRET_KEY', 'jwt-secret-key'))
os.environ.setdefault('JWT_ACCESS_TOKEN_EXPIRES', os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '86400'))

# Agregar directorio al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Determinar tipo de base de datos
    db_type = "PostgreSQL (Neon)" if 'postgresql' in os.getenv('DATABASE_URL', '') else "SQLite"
    
    print("=" * 60)
    print("🚀 NUTRICHAT - ASISTENTE NUTRICIONAL INTELIGENTE")
    print("=" * 60)
    print(f"✨ Versión: 2.0 Professional")
    print(f"🌐 Frontend: http://127.0.0.1:5000")
    print(f"📚 API REST: http://127.0.0.1:5000/api/v1/")
    print(f"🔧 Modo: {os.getenv('FLASK_ENV', 'development').upper()}")
    print(f"💾 Database: {db_type}")
    print("=" * 60)
    print("✅ Sistema listo para recibir conexiones...")
    print("=" * 60)
    
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=os.getenv('FLASK_ENV') == 'development'
    )