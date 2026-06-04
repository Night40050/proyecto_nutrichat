"""
Rutas de usuarios: autenticación, perfil y búsqueda
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.controllers.user_controller import UserController
from app.models.user import User
from app.models.database import db
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Crear blueprint para rutas de usuarios
users_bp = Blueprint('users', __name__)


# ============================================================
# AUTENTICACIÓN
# ============================================================

@users_bp.route('/users/register', methods=['POST'])
def register_user():
    """
    Registrar nuevo usuario
    
    Body JSON:
    {
        "telegram_id": 123456789,  // REQUERIDO
        "nombre": "Juan Pérez",    // OPCIONAL
        "email": "juan@email.com", // OPCIONAL
        "telefono": "+52123456789", // OPCIONAL
        "sexo": "M",               // OPCIONAL
        "fecha_nacimiento": "1990-01-15", // OPCIONAL
        "peso_kg": 70.5,          // OPCIONAL
        "altura_cm": 175.0        // OPCIONAL
    }
    """
    return UserController.register()


@users_bp.route('/auth/login', methods=['POST'])
def login():
    """
    Login con Telegram ID (sin contraseña)
    
    Body JSON:
    {
        "telegram_id": 123456789
    }
    
    Response:
    {
        "success": true,
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "user": {...}
    }
    """
    return UserController.login()


# ============================================================
# ENDPOINTS PROTEGIDOS (Requieren autenticación JWT)
# ============================================================

@users_bp.route('/users/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    """
    Obtener perfil del usuario autenticado
    
    Headers:
    Authorization: Bearer <access_token>
    """
    return UserController.get_profile()


@users_bp.route('/users/profile', methods=['PUT'])
@jwt_required()
def update_user_profile():
    """
    Actualizar perfil del usuario autenticado
    
    Headers:
    Authorization: Bearer <access_token>
    
    Body JSON (todos opcionales):
    {
        "nombre": "Juan Carlos",
        "email": "nuevo@email.com",
        "telefono": "+52987654321",
        "sexo": "M",
        "fecha_nacimiento": "1990-01-15",
        "peso_kg": 75.0,
        "altura_cm": 180.0,
        "nutritional_preferences": {
            "diet_type": "vegetariana",
            "allergies": ["lactosa"],
            "goal": "bajar_peso"
        },
        "budget_monthly": 5000,
        "budget_weekly": 1200
    }
    """
    return UserController.update_profile()


# ============================================================
# BÚSQUEDA DE USUARIOS (Para integración con bot/N8N)
# ============================================================

@users_bp.route('/users/telegram/<int:telegram_id>', methods=['GET'])
def get_user_by_telegram_id(telegram_id):
    """
    Buscar usuario por Telegram ID
    
    Útil para que N8N verifique si un usuario existe
    
    Parámetros:
    - telegram_id: ID de Telegram del usuario
    
    Response:
    {
        "success": true,
        "user": {...}
    }
    """
    return UserController.get_user_by_telegram_id(telegram_id)


@users_bp.route('/users/search/email', methods=['POST'])
def search_user_by_email():
    """
    Buscar usuario por email
    
    Body JSON:
    {
        "email": "usuario@ejemplo.com"
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({
                'success': False,
                'message': 'Email es requerido'
            }), 400
        
        user = User.get_by_email(data['email'])
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'user': user.to_json_safe()
        }), 200
        
    except Exception as e:
        logger.error(f"Error buscando usuario por email: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500


# ============================================================
# GESTIÓN DE PREFERENCIAS NUTRICIONALES
# ============================================================

@users_bp.route('/users/profile/nutrition', methods=['PUT'])
@jwt_required()
def update_nutritional_preferences():
    """
    Actualizar preferencias nutricionales
    
    Body JSON:
    {
        "nutritional_preferences": {
            "diet_type": "vegetariana",
            "allergies": ["lactosa", "gluten"],
            "dislikes": ["brócoli"],
            "goal": "bajar_peso"
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        
        data = request.get_json()
        
        if not data or 'nutritional_preferences' not in data:
            return jsonify({
                'success': False,
                'message': 'nutritional_preferences es requerido'
            }), 400
        
        user.set_nutritional_preferences(data['nutritional_preferences'])
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Preferencias nutricionales actualizadas',
            'nutritional_preferences': user.get_nutritional_preferences()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error actualizando preferencias: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500


@users_bp.route('/users/profile/budget', methods=['PUT'])
@jwt_required()
def update_budget():
    """
    Actualizar presupuesto
    
    Body JSON:
    {
        "budget_monthly": 5000,
        "budget_weekly": 1200
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos requeridos'
            }), 400
        
        user.set_budget(
            monthly=data.get('budget_monthly'),
            weekly=data.get('budget_weekly')
        )
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Presupuesto actualizado',
            'budget': {
                'monthly': float(user.budget_monthly) if user.budget_monthly else None,
                'weekly': float(user.budget_weekly) if user.budget_weekly else None
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error actualizando presupuesto: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500


# Agrega 'PUT' a los métodos permitidos
@users_bp.route('/users/register', methods=['POST', 'PUT'])
def register_or_update_user():
    """
    Registra si no existe, actualiza si ya existe (Upsert)
    Ideal para el flujo de n8n que completa el perfil paso a paso.
    """
    return UserController.register() # Seguiremos usando el controlador, pero lo ajustaremos

@users_bp.route('/users/profile', methods=['DELETE'])
@jwt_required()
def delete_user_profile():
    return UserController.delete_user_profile()