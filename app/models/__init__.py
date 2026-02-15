"""
Modelos de datos para NutriChat
"""

from .database import db

# NO importar nada más aquí - solo db
# Esto evita importaciones circulares

# Función para obtener modelos cuando se necesiten
def get_user_model():
    """Obtener modelo User (importación diferida)"""
    from .user import User, Rol
    return User, Rol

def get_producto_model():
    """Obtener modelo Producto (importación diferida)"""
    from .productos import Categoria, Producto, ProductoNutricion, ProductoSnapshot
    return Categoria, Producto, ProductoNutricion, ProductoSnapshot

def get_user_products_model():
    """Obtener modelos de user_products (importación diferida)"""
    from .user_products import UserProduct, ScrapingSession
    return UserProduct, ScrapingSession

# Exportar solo db inicialmente
__all__ = ['db']