"""
Módulo de rutas modularizadas de la API NutriChat

Este módulo registra todos los blueprints de rutas por dominio.
"""
from flask import Flask, jsonify
import logging
from .system_routes import system_bp
from .users_routes import users_bp
from .telegram_routes import telegram_bp
from .productos_routes import productos_bp
from .reportes_routes import reportes_bp
from .scraping_routes import scraping_bp
from .listas_routes import listas_bp
from .condiciones_routes import condiciones_bp
from .audit_log_routes import audit_log_bp

from .recomendacion_routes import recomendacion_bp

# Configurar logging
logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask):
    """
    Registrar manejadores de errores a nivel de aplicación
    
    Args:
        app: Instancia de la aplicación Flask
    """
    @app.errorhandler(404)
    def not_found(error):
        """Endpoint no encontrado"""
        return jsonify({
            'success': False,
            'message': 'Endpoint no encontrado',
            'error': 'NOT_FOUND'
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Método HTTP no permitido"""
        return jsonify({
            'success': False,
            'message': 'Método no permitido',
            'error': 'METHOD_NOT_ALLOWED'
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        """Error interno del servidor"""
        logger.error(f"Error interno: {str(error)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor',
            'error': 'INTERNAL_SERVER_ERROR'
        }), 500

    @app.errorhandler(401)
    def unauthorized(error):
        """No autorizado"""
        return jsonify({
            'success': False,
            'message': 'Autenticación requerida',
            'error': 'UNAUTHORIZED'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        """Acceso prohibido"""
        return jsonify({
            'success': False,
            'message': 'Acceso prohibido',
            'error': 'FORBIDDEN'
        }), 403


def register_routes(app: Flask):
    """
    Registrar todos los blueprints de rutas con el prefijo '/api'
    y los manejadores de errores
    
    Args:
        app: Instancia de la aplicación Flask
    """
    # Registrar blueprints
    app.register_blueprint(system_bp, url_prefix='/api')
    app.register_blueprint(users_bp, url_prefix='/api')
    app.register_blueprint(telegram_bp, url_prefix='/api')
    app.register_blueprint(productos_bp, url_prefix='/api')
    app.register_blueprint(reportes_bp, url_prefix='/api')
    app.register_blueprint(scraping_bp, url_prefix='/api')
    app.register_blueprint(listas_bp, url_prefix='/api')
    app.register_blueprint(condiciones_bp, url_prefix='/api')
    app.register_blueprint(audit_log_bp, url_prefix='/api')
    
    # ... oalgoritmo implementacion
    app.register_blueprint(recomendacion_bp, url_prefix='/api')

    # Registrar manejadores de errores a nivel de aplicación
    register_error_handlers(app)

