"""
Middleware de autorización para NutriChat
Maneja validaciones de roles y permisos
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

# Definición de roles
ROLES = {
	1: 'admin',
	2: 'user',
	3: 'nutritionist',
	4: 'bot'
}

def require_role(*allowed_roles):
	"""
	Decorador para requerir roles específicos
	
	Args:
		*allowed_roles: Lista de roles permitidos ('admin', 'user', 'nutritionist', 'bot')
	
	Usage:
		@require_role('admin', 'nutritionist')
		def admin_only_endpoint():
			pass
	"""
	def decorator(f):
		@wraps(f)
		@jwt_required()
		def decorated_function(*args, **kwargs):
			try:
				current_user_id = get_jwt_identity()
				user = User.query.get(current_user_id)
				
				if not user:
					return jsonify({
						'success': False,
						'message': 'Usuario no encontrado'
					}), 404
				
				if not user.is_active:
					return jsonify({
						'success': False,
						'message': 'Cuenta desactivada'
					}), 403
				
				user_role = ROLES.get(user.rol_id, 'unknown')
				
				if user_role not in allowed_roles:
					logger.warning(f"Acceso denegado para usuario {user.email} con rol {user_role}")
					return jsonify({
						'success': False,
						'message': 'No tienes permisos para acceder a este recurso'
					}), 403
				
				# Agregar información del usuario al contexto
				kwargs['current_user'] = user
				kwargs['current_role'] = user_role
				
				return f(*args, **kwargs)
				
			except Exception as e:
				logger.error(f"Error en middleware de autorización: {str(e)}")
				return jsonify({
					'success': False,
					'message': 'Error interno del servidor'
				}), 500
		
		return decorated_function
	return decorator

def require_admin(f):
	"""Decorador para requerir rol de administrador"""
	return require_role('admin')(f)

def require_nutritionist(f):
	"""Decorador para requerir rol de nutricionista o administrador"""
	return require_role('admin', 'nutritionist')(f)

def require_user_or_higher(f):
	"""Decorador para requerir cualquier rol de usuario autenticado"""
	return require_role('admin', 'nutritionist', 'user', 'bot')(f)

def require_own_resource_or_admin(f):
	"""
	Decorador para permitir acceso solo al propio recurso o a administradores
	Requiere que la función tenga un parámetro 'user_id'
	"""
	@wraps(f)
	@jwt_required()
	def decorated_function(*args, **kwargs):
		try:
			current_user_id = get_jwt_identity()
			current_user = User.query.get(current_user_id)
			
			if not current_user:
				return jsonify({
					'success': False,
					'message': 'Usuario no encontrado'
				}), 404
			
			if not current_user.is_active:
				return jsonify({
					'success': False,
					'message': 'Cuenta desactivada'
				}), 403
			
			# Obtener el user_id del recurso solicitado
			resource_user_id = kwargs.get('user_id')
			
			# Los administradores pueden acceder a cualquier recurso
			if current_user.rol_id == 1:  # admin
				kwargs['current_user'] = current_user
				kwargs['current_role'] = 'admin'
				return f(*args, **kwargs)
			
			# Los usuarios solo pueden acceder a sus propios recursos
			if str(current_user.usuario_id) != str(resource_user_id):
				logger.warning(f"Usuario {current_user.email} intentó acceder al recurso de otro usuario")
				return jsonify({
					'success': False,
					'message': 'Solo puedes acceder a tus propios recursos'
				}), 403
			
			kwargs['current_user'] = current_user
			kwargs['current_role'] = ROLES.get(current_user.rol_id, 'user')
			
			return f(*args, **kwargs)
			
		except Exception as e:
			logger.error(f"Error en middleware de recurso propio: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	return decorated_function

def api_key_required(f):
	"""
	Decorador para requerir API Key (para integraciones externas como el bot)
	"""
	@wraps(f)
	def decorated_function(*args, **kwargs):
		from flask import request
		import os
		
		try:
			api_key = request.headers.get('X-API-Key')
			expected_api_key = os.getenv('API_KEY')
			
			if not expected_api_key:
				# Si no hay API key configurada, permitir acceso
				return f(*args, **kwargs)
			
			if not api_key or api_key != expected_api_key:
				logger.warning("Intento de acceso con API key inválida")
				return jsonify({
					'success': False,
					'message': 'API Key requerida o inválida'
				}), 401
			
			return f(*args, **kwargs)
			
		except Exception as e:
			logger.error(f"Error en middleware de API key: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	return decorated_function

def rate_limit_by_user(max_requests=100, window_minutes=60):
	"""
	Decorador para limitar la tasa de requests por usuario
	Implementación básica en memoria (en producción usar Redis)
	"""
	from datetime import datetime, timedelta
	from collections import defaultdict
	
	# Almacén en memoria (en producción usar Redis)
	request_counts = defaultdict(list)
	
	def decorator(f):
		@wraps(f)
		@jwt_required()
		def decorated_function(*args, **kwargs):
			try:
				current_user_id = get_jwt_identity()
				now = datetime.utcnow()
				window_start = now - timedelta(minutes=window_minutes)
				
				# Limpiar requests antiguos
				request_counts[current_user_id] = [
					req_time for req_time in request_counts[current_user_id]
					if req_time > window_start
				]
				
				# Verificar límite
				if len(request_counts[current_user_id]) >= max_requests:
					return jsonify({
						'success': False,
						'message': f'Límite de {max_requests} requests por {window_minutes} minutos excedido'
					}), 429
				
				# Registrar request actual
				request_counts[current_user_id].append(now)
				
				return f(*args, **kwargs)
				
			except Exception as e:
				logger.error(f"Error en middleware de rate limiting: {str(e)}")
				return jsonify({
					'success': False,
					'message': 'Error interno del servidor'
				}), 500
		
		return decorated_function
	return decorator