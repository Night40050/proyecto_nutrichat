"""
Rutas principales de la API NutriChat
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.controllers.user_controller import UserController
from app.api.controllers.auth_controller import AuthController
from app.api.controllers.profile_controller import ProfileController
from app.api.middleware.auth_middleware import (
	require_role, require_admin, require_nutritionist, 
	require_user_or_higher, require_own_resource_or_admin,
	api_key_required, rate_limit_by_user
)
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear blueprint para la API
api_bp = Blueprint('api', __name__)

@api_bp.route('/status', methods=['GET'])
def status():
	"""Endpoint para verificar el estado de la API"""
	return jsonify({
		'success': True,
		'message': 'API NutriChat funcionando correctamente',
		'version': '1.0.0'
	}), 200

# === RUTAS DE AUTENTICACIÓN ===

@api_bp.route('/auth/login', methods=['POST'])
def login():
	"""
	Inicio de sesión con tokens de acceso y refresh
	Método: POST
	Payload: {
		"email": "string",
		"password": "string"
	}
	"""
	return AuthController.login()

@api_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
	"""
	Renovar token de acceso usando refresh token
	Método: POST
	Headers: Authorization: Bearer <refresh_token>
	"""
	return AuthController.refresh()

@api_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
	"""
	Cerrar sesión (invalidar tokens)
	Método: POST
	Headers: Authorization: Bearer <access_token>
	"""
	return AuthController.logout()

@api_bp.route('/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
	"""
	Verificar validez del token actual
	Método: GET
	Headers: Authorization: Bearer <access_token>
	"""
	return AuthController.verify_token()

# === RUTAS DE USUARIOS ===

@api_bp.route('/users/register', methods=['POST'])
def register_user():
	"""
	Registro de nuevo usuario
	Método: POST
	Payload: {
		"email": "string",
		"password": "string", 
		"nombre": "string" (opcional),
		"telefono": "string" (opcional),
		"telegram_id": int (opcional)
	}
	"""
	return UserController.register()

@api_bp.route('/users/telegram/<telegram_id>', methods=['GET'])
@api_key_required
def get_user_by_telegram_id(telegram_id):
	"""
	Obtener usuario por Telegram ID (para el bot)
	Método: GET
	Headers: X-API-Key: <api_key>
	"""
	return UserController.get_user_by_telegram_id(telegram_id)

# === RUTAS DE PERFIL ===

@api_bp.route('/users/profile', methods=['GET'])
@require_user_or_higher
def get_user_profile(**kwargs):
	"""
	Obtener perfil del usuario autenticado
	Método: GET
	Headers: Authorization: Bearer <access_token>
	"""
	return ProfileController.get_profile()

@api_bp.route('/users/profile/basic', methods=['PUT'])
@require_user_or_higher
@rate_limit_by_user(max_requests=20, window_minutes=60)
def update_basic_info(**kwargs):
	"""
	Actualizar información básica del perfil
	Método: PUT
	Headers: Authorization: Bearer <access_token>
	Payload: {
		"nombre": "string" (opcional),
		"telefono": "string" (opcional),
		"sexo": "M|F" (opcional),
		"fecha_nacimiento": "YYYY-MM-DD" (opcional),
		"peso_kg": float (opcional),
		"altura_cm": float (opcional)
	}
	"""
	return ProfileController.update_basic_info()

@api_bp.route('/users/profile/medical-conditions', methods=['GET'])
@require_user_or_higher
def get_medical_conditions(**kwargs):
	"""
	Obtener condiciones médicas del usuario
	Método: GET
	Headers: Authorization: Bearer <access_token>
	"""
	return ProfileController.get_medical_conditions()

@api_bp.route('/users/profile/medical-conditions', methods=['POST'])
@require_user_or_higher
@rate_limit_by_user(max_requests=10, window_minutes=60)
def add_medical_condition(**kwargs):
	"""
	Agregar nueva condición médica
	Método: POST
	Headers: Authorization: Bearer <access_token>
	Payload: {
		"name": "string",
		"severity": "low|medium|high",
		"description": "string" (opcional),
		"dietary_restrictions": ["string"] (opcional)
	}
	"""
	return ProfileController.add_medical_condition()

@api_bp.route('/users/profile/medical-conditions/<condition_id>', methods=['PUT'])
@require_user_or_higher
def update_medical_condition(condition_id, **kwargs):
	"""
	Actualizar condición médica específica
	Método: PUT
	Headers: Authorization: Bearer <access_token>
	"""
	return ProfileController.update_medical_condition(condition_id)

@api_bp.route('/users/profile/medical-conditions/<condition_id>', methods=['DELETE'])
@require_user_or_higher
def delete_medical_condition(condition_id, **kwargs):
	"""
	Eliminar condición médica
	Método: DELETE
	Headers: Authorization: Bearer <access_token>
	"""
	return ProfileController.delete_medical_condition(condition_id)

@api_bp.route('/users/profile/nutrition', methods=['PUT'])
@require_user_or_higher
@rate_limit_by_user(max_requests=15, window_minutes=60)
def update_nutritional_preferences(**kwargs):
	"""
	Actualizar preferencias nutricionales
	Método: PUT
	Headers: Authorization: Bearer <access_token>
	Payload: {
		"dietary_type": "omnivore|vegetarian|vegan|keto|paleo|mediterranean" (opcional),
		"allergies": ["string"] (opcional),
		"dislikes": ["string"] (opcional),
		"objectives": ["weight_loss", "weight_gain", "muscle_gain", "maintenance"] (opcional),
		"meal_frequency": int (opcional),
		"cooking_time_preference": "quick|moderate|elaborate" (opcional),
		"budget_preference": "low|medium|high" (opcional)
	}
	"""
	return ProfileController.update_nutritional_preferences()

@api_bp.route('/users/profile/budget', methods=['PUT'])
@require_user_or_higher
def update_budget(**kwargs):
	"""
	Actualizar presupuesto nutricional
	Método: PUT
	Headers: Authorization: Bearer <access_token>
	Payload: {
		"monthly_budget": float (opcional),
		"weekly_budget": float (opcional)
	}
	"""
	return ProfileController.update_budget()

@api_bp.route('/users/profile/recommendations', methods=['GET'])
@require_user_or_higher
def get_nutrition_recommendations(**kwargs):
	"""
	Obtener recomendaciones nutricionales personalizadas
	Método: GET
	Headers: Authorization: Bearer <access_token>
	"""
	return ProfileController.get_nutrition_recommendations()

# === RUTAS ADMINISTRATIVAS ===

@api_bp.route('/users/<user_id>/profile', methods=['GET'])
@require_admin
def get_user_profile_by_id(user_id, **kwargs):
	"""
	Obtener perfil de usuario específico (solo administradores)
	Método: GET
	Headers: Authorization: Bearer <access_token>
	"""
	return ProfileController.get_profile(user_id)

@api_bp.route('/users/<user_id>/profile', methods=['PUT'])
@require_own_resource_or_admin
def update_user_profile_by_id(user_id, **kwargs):
	"""
	Actualizar perfil de usuario específico
	Método: PUT
	Headers: Authorization: Bearer <access_token>
	"""
	return ProfileController.update_basic_info(user_id)

# === RUTAS DE INFORMACIÓN ===

@api_bp.route('/info', methods=['GET'])
def get_api_info():
	"""
	Información general de la API
	"""
	return jsonify({
		'success': True,
		'data': {
			'name': 'NutriChat API',
			'version': '1.0.0',
			'description': 'API para gestión de perfiles nutricionales y recomendaciones',
			'endpoints': {
				'auth': [
					'POST /api/auth/login',
					'POST /api/auth/refresh',
					'POST /api/auth/logout',
					'GET /api/auth/verify'
				],
				'users': [
					'POST /api/users/register',
					'GET /api/users/telegram/<telegram_id>'
				],
				'profile': [
					'GET /api/users/profile',
					'PUT /api/users/profile/basic',
					'GET /api/users/profile/medical-conditions',
					'POST /api/users/profile/medical-conditions',
					'PUT /api/users/profile/medical-conditions/<id>',
					'DELETE /api/users/profile/medical-conditions/<id>',
					'PUT /api/users/profile/nutrition',
					'PUT /api/users/profile/budget',
					'GET /api/users/profile/recommendations'
				],
				'admin': [
					'GET /api/users/<user_id>/profile',
					'PUT /api/users/<user_id>/profile'
				]
			}
		}
	}), 200

# === MANEJADORES DE ERRORES ===

@api_bp.errorhandler(404)
def not_found(error):
	return jsonify({
		'success': False,
		'message': 'Endpoint no encontrado'
	}), 404

@api_bp.errorhandler(405)
def method_not_allowed(error):
	return jsonify({
		'success': False,
		'message': 'Método no permitido'
	}), 405

@api_bp.errorhandler(500)
def internal_error(error):
	logger.error(f"Error interno del servidor: {str(error)}")
	return jsonify({
		'success': False,
		'message': 'Error interno del servidor'
	}), 500