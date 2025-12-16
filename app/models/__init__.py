"""
Modelos de datos para NutriChat

Este módulo expone todos los modelos de la aplicación para facilitar
las importaciones desde otras partes del código.
"""

from .database import db
from .user import User, Rol
from .productos import Categoria, Producto, ProductoNutricion, ProductoSnapshot
from .reportes import Reporte, FeedbackRecomendacion
from .listas import ListaMercado, ProductosEnLista
from .condiciones import CondicionNutricional, UsuarioCondicion
from .telegram_sesion import TelegramSesion
from .audit_log import AuditLog
from .configuracion_sistema import ConfiguracionSistema
from .scraping_cache import ScrapingCache

# Exportar todos los modelos principales
__all__ = [
    'db',
    'User',
    'Rol',
    'Categoria',
    'Producto',
    'ProductoNutricion',
    'ProductoSnapshot',
    'Reporte',
    'FeedbackRecomendacion',
    'ListaMercado',
    'ProductosEnLista',
    'CondicionNutricional',
    'UsuarioCondicion',
    'TelegramSesion',
    'AuditLog',
    'ConfiguracionSistema',
    'ScrapingCache',
]
