"""
Tipos de datos personalizados para SQLAlchemy
"""
import uuid
from sqlalchemy.types import TypeDecorator, String, JSON

class GUID(TypeDecorator):
    """
    UUID compatible con PostgreSQL y SQLite
    """
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(value)

# Para SQLite y otros sistemas que no tienen JSONB nativo
class JSONB(JSON):
    """
    JSONB compatible con PostgreSQL, JSON para otros sistemas
    """
    cache_ok = True

# Exportar
__all__ = ['GUID', 'JSONB']