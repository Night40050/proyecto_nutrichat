"""
Rutas para gestión de usuarios
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.controllers.user_controller import UserController

user_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')

@user_bp.route('/register', methods=['POST'])
def register():
    """Registrar nuevo usuario"""
    return UserController.register()

@user_bp.route('/login', methods=['POST'])
def login():
    """Iniciar sesión con Telegram ID"""
    return UserController.login()

@user_bp.route('/telegram/<int:telegram_id>', methods=['GET'])
def get_by_telegram(telegram_id):
    """Obtener usuario por Telegram ID"""
    return UserController.get_user_by_telegram_id(telegram_id)

@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Obtener perfil del usuario autenticado"""
    return UserController.get_profile()

@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Actualizar perfil del usuario"""
    return UserController.update_profile()

@user_bp.route('/', methods=['GET'])
def index():
    """Información del endpoint de usuarios"""
    return jsonify({
        'success': True,
        'message': 'API de usuarios de NutriChat',
        'endpoints': {
            'register': 'POST /api/v1/users/register',
            'login': 'POST /api/v1/users/login',
            'profile': 'GET /api/v1/users/profile (requiere JWT)',
            'get_by_telegram': 'GET /api/v1/users/telegram/<telegram_id>',
            'update_profile': 'PUT /api/v1/users/profile (requiere JWT)'
        }
    }), 200