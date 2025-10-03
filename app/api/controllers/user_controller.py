"""
Controlador para gestión de usuarios en NutriChat
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from app.models.database import db
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

class UserController:
    @staticmethod
    def register():
        """Registrar nuevo usuario"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No se enviaron datos'
                }), 400
            
            # Validar campos requeridos
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return jsonify({
                    'success': False,
                    'message': 'Email y contraseña son requeridos'
                }), 400
            
            # Verificar si el usuario ya existe
            if User.get_by_email(email):
                return jsonify({
                    'success': False,
                    'message': 'El email ya está registrado'
                }), 409
            
            # Verificar si Telegram ID ya existe (si se proporciona)
            telegram_id = data.get('telegram_id')
            if telegram_id and User.get_by_telegram_id(telegram_id):
                return jsonify({
                    'success': False,
                    'message': 'Esta cuenta de Telegram ya está vinculada'
                }), 409
            
            # Crear usuario
            user_data = {
                'email': email,
                'nombre': data.get('nombre'),
                'telefono': data.get('telefono'),
                'sexo': data.get('sexo'),
                'fecha_nacimiento': data.get('fecha_nacimiento'),
                'peso_kg': data.get('peso_kg'),
                'altura_cm': data.get('altura_cm'),
                'telegram_id': telegram_id
            }
            
            user = User.create_user(email=email, password=password, **user_data)
            
            # Guardar en base de datos
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"Usuario creado exitosamente: {email}")
            
            return jsonify({
                'success': True,
                'message': 'Usuario creado exitosamente',
                'user': user.to_json_safe()
            }), 201
            
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
            
        except IntegrityError as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': 'Error de integridad: email ya existe'
            }), 409
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear usuario: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    def login():
        """Iniciar sesión"""
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
            
            # Crear token de acceso
            access_token = create_access_token(identity=str(user.id))
            
            # Actualizar última conexión
            user.update_last_connection()
            
            return jsonify({
                'success': True,
                'message': 'Inicio de sesión exitoso',
                'access_token': access_token,
                'user': user.to_json_safe()
            }), 200
            
        except Exception as e:
            logger.error(f"Error en login: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    def get_user_by_telegram_id(telegram_id):
        """Obtener usuario por Telegram ID"""
        try:
            user = User.get_by_telegram_id(int(telegram_id))
            
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'Usuario no encontrado'
                }), 404
            
            return jsonify({
                'success': True,
                'user': user.to_json_safe()
            }), 200
            
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Telegram ID inválido'
            }), 400
            
        except Exception as e:
            logger.error(f"Error al buscar usuario por Telegram ID: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    @jwt_required()
    def get_profile():
        """Obtener perfil del usuario autenticado"""
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
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
            logger.error(f"Error al obtener perfil: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    @jwt_required()
    def update_profile():
        """Actualizar perfil del usuario autenticado"""
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
                    'message': 'No se enviaron datos'
                }), 400
            
            # Campos actualizables
            updatable_fields = [
                'nombre', 'telefono', 'sexo', 'fecha_nacimiento', 
                'peso_kg', 'altura_cm'
            ]
            
            for field in updatable_fields:
                if field in data:
                    setattr(user, field, data[field])
            
            # Actualizar preferencias nutricionales si se envían
            if 'nutritional_preferences' in data:
                user.set_nutritional_preferences(data['nutritional_preferences'])
            
            # Actualizar presupuesto si se envía
            if 'budget_monthly' in data or 'budget_weekly' in data:
                user.set_budget(
                    monthly=data.get('budget_monthly'),
                    weekly=data.get('budget_weekly')
                )
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Perfil actualizado exitosamente',
                'user': user.to_json_safe()
            }), 200
            
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al actualizar perfil: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500