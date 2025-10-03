"""
Controlador de autenticación para NutriChat
Maneja login, logout, refresh tokens y validaciones de autenticación
"""
from flask import request, jsonify
from flask_jwt_extended import (
	jwt_required, create_access_token, create_refresh_token, 
	get_jwt_identity, get_jwt
)
from app.models.database import db
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

class AuthController:
	@staticmethod
	def login():
		"""
		Iniciar sesión con email y contraseña
		Retorna access_token y refresh_token
		"""
		try:
			data = request.get_json()
			
			if not data:
				return jsonify({
					'success': False,
					'message': 'No se enviaron datos'
				}), 400
			
			email = data.get('email')
			password = data.get('password')
			
			if not email or not password:
				return jsonify({
					'success': False,
					'message': 'Email y contraseña son requeridos'
				}), 400
			
			# Buscar usuario
			user = User.get_by_email(email)
			
			if not user or not user.check_password(password):
				return jsonify({
					'success': False,
					'message': 'Credenciales inválidas'
				}), 401
			
			if not user.is_active:
				return jsonify({
					'success': False,
					'message': 'Cuenta desactivada'
				}), 403
			
			# Crear tokens
			access_token = create_access_token(identity=str(user.id))
			refresh_token = create_refresh_token(identity=str(user.id))
			
			# Actualizar última conexión
			user.update_last_connection()
			
			logger.info(f"Login exitoso para usuario: {email}")
			
			return jsonify({
				'success': True,
				'message': 'Inicio de sesión exitoso',
				'access_token': access_token,
				'refresh_token': refresh_token,
				'user': user.to_json_safe()
			}), 200
			
		except Exception as e:
			logger.error(f"Error en login: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required(refresh=True)
	def refresh():
		"""
		Renovar access token usando refresh token
		"""
		try:
			current_user_id = get_jwt_identity()
			
			# Verificar que el usuario existe y está activo
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
			
			# Crear nuevo access token
			new_access_token = create_access_token(identity=str(user.id))
			
			logger.info(f"Token renovado para usuario: {user.email}")
			
			return jsonify({
				'success': True,
				'message': 'Token renovado exitosamente',
				'access_token': new_access_token
			}), 200
			
		except Exception as e:
			logger.error(f"Error al renovar token: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def logout():
		"""
		Cerrar sesión (invalidar token)
		Nota: En una implementación completa, se mantendría una blacklist de tokens
		"""
		try:
			current_user_id = get_jwt_identity()
			jti = get_jwt()['jti']  # JWT ID único
			
			# En una implementación completa, aquí se agregaría el token a una blacklist
			# Por ahora, solo registramos el logout
			
			user = User.query.get(current_user_id)
			if user:
				logger.info(f"Logout para usuario: {user.email}")
			
			return jsonify({
				'success': True,
				'message': 'Sesión cerrada exitosamente'
			}), 200
			
		except Exception as e:
			logger.error(f"Error en logout: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def verify_token():
		"""
		Verificar si el token actual es válido
		"""
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
			
			return jsonify({
				'success': True,
				'message': 'Token válido',
				'user': user.to_json_safe()
			}), 200
			
		except Exception as e:
			logger.error(f"Error al verificar token: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500