# app/routes/__init__.py
"""
Configuración de rutas de la aplicación
"""
from flask import Flask
from .user_routes import user_bp
from .product_routes import product_bp
from .list_routes import list_bp
from .condition_routes import condition_bp
from .system_routes import system_bp

def register_routes(app: Flask):
    """
    Registrar todos los blueprints de la aplicación
    """
    app.register_blueprint(user_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(list_bp)
    app.register_blueprint(condition_bp)
    app.register_blueprint(system_bp)
    
    # Ruta principal de la API
    @app.route('/')
    def root():
        return {
            'api': 'NutriChat API',
            'version': '1.0',
            'endpoints': {
                'users': '/api/v1/users',
                'products': '/api/v1/products',
                'lists': '/api/v1/lists',
                'conditions': '/api/v1/conditions',
                'system': '/api/v1/system',
                'health': '/api/v1/health'
            }
        }