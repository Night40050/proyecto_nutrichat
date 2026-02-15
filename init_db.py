"""
Script para verificar conexión a Neon en Render
Ubicación: /proyecto_nutrichat/init_db.py
"""

import os
import logging
from app import create_app
from app.models.database import db
from sqlalchemy import text, inspect

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Verificar conexión a la base de datos"""
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Verificar conexión
            logger.info("🔍 Verificando conexión a Neon...")
            result = db.session.execute(text("SELECT version()"))
            version = result.fetchone()
            logger.info(f"✅ Conectado a PostgreSQL: {version[0][:60]}...")
            
            # 2. Verificar tablas existentes
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"📊 Tablas disponibles: {tables}")
            
            # 3. Contar registros en tablas principales
            tablas_importantes = ['usuarios', 'user_products', 'scraping_sessions']
            for tabla in tablas_importantes:
                if tabla in tables:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                    count = result.scalar()
                    logger.info(f"   • {tabla}: {count} registros")
            
            # 4. Verificar usuario de prueba (opcional)
            telegram_id = os.getenv('TEST_TELEGRAM_ID')
            if telegram_id:
                result = db.session.execute(
                    text("SELECT usuario_id, nombre FROM usuarios WHERE telegram_id = :tid"),
                    {'tid': int(telegram_id)}
                )
                user = result.fetchone()
                if user:
                    logger.info(f"✅ Usuario encontrado: {user[1]} (ID: {user[0]})")
                else:
                    logger.warning(f"⚠️ Usuario con telegram_id {telegram_id} no encontrado")
            
            logger.info("✅ Verificación completada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Neon: {e}")
            return False

if __name__ == "__main__":
    init_db()