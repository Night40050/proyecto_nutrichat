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
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No se enviaron datos'
                }), 400
            
            #  SOLO telegram_id es requerido
            telegram_id = data.get('telegram_id')
            
            if not telegram_id:
                return jsonify({
                    'success': False,
                    'message': 'telegram_id es requerido'
                }), 400
            
            # Validar que telegram_id sea un número entero
            try:
                telegram_id = int(telegram_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'telegram_id debe ser un número entero'
                }), 400

            user = User.get_by_telegram_id(telegram_id)
            # Verificar si el usuario ya existe
            if user:
                # 2. Si existe, ACTUALIZAMOS los campos que vengan en el JSON
                if 'nombre' in data: user.nombre = data['nombre']
                if 'peso_kg' in data: user.peso_kg = data['peso_kg']
                if 'altura_cm' in data: user.altura_cm = data['altura_cm']
                if 'objetivo_nutricional' in data: user.objetivo_nutricional = data['objetivo_nutricional']
        
                # Para campos complejos como alergias/condiciones
                if 'alergias' in data or 'condiciones' in data:
                    prefs = user.get_nutritional_preferences() or {}
                    if 'alergias' in data: prefs['allergies'] = data['alergias']
                    if 'condiciones' in data: prefs['conditions'] = data['condiciones']
                    user.set_nutritional_preferences(prefs)

                db.session.commit()
                return jsonify({
                    'success': True, 
                    'message': 'Usuario actualizado exitosamente',
                    'user': user.to_json_safe()
                }), 200
            
            # Verificar email si se proporciona
            email = data.get('email')
            if email and User.get_by_email(email):
                return jsonify({
                    'success': False,
                    'message': 'El email ya está registrado'
                }), 409
            
            #  Crear usuario con telegram_id 
            user = User.create_user(
                telegram_id=telegram_id,
                nombre=data.get('nombre'),
                email=email,
                telefono=data.get('telefono'),
                sexo=data.get('sexo'),
                fecha_nacimiento=data.get('fecha_nacimiento'),
                peso_kg=data.get('peso_kg'),
                altura_cm=data.get('altura_cm')
            )
            
            # Guardar en base de datos
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"Usuario creado exitosamente - Telegram ID: {telegram_id}")
            
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
            logger.error(f"Error de integridad: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error de integridad: telegram_id o email duplicado'
            }), 409
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear usuario: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error interno del servidor: {str(e)}'
            }), 500
    
    @staticmethod
    def login():
        """
        Iniciar sesión SOLO con telegram_id (sin contraseña)
        Body JSON:
        {
            "telegram_id": 123456789
        }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No se enviaron datos'
                }), 400
            
            telegram_id = data.get('telegram_id')
            
            if not telegram_id:
                return jsonify({
                    'success': False,
                    'message': 'telegram_id es requerido'
                }), 400
            
            # Validar que sea entero
            try:
                telegram_id = int(telegram_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'telegram_id debe ser un número entero'
                }), 400
            
            # Buscar usuario por telegram_id
            user = User.get_by_telegram_id(telegram_id)
            
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
            
            # Crear token de acceso usando el UUID del usuario
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
                'message': f'Error interno del servidor: {str(e)}'
            }), 500
    
    @staticmethod
    def get_user_by_telegram_id(telegram_id):
        """Obtener usuario por Telegram ID"""
        try:
            user = User.get_by_telegram_id(int(telegram_id))
            
            if user:
                # ACTUALIZACIÓN: Si el usuario ya existe, solo llenamos lo nuevo
                if 'nombre' in data: user.nombre = data['nombre']
                if 'email' in data and data['email']: user.email = data['email'] # <--- CRÍTICO
                if 'peso_kg' in data: user.peso_kg = data['peso_kg']
                if 'altura_cm' in data: user.altura_cm = data['altura_cm']
                if 'objetivo_nutricional' in data: user.objetivo_nutricional = data['objetivo_nutricional']
    
                # Manejo de preferencias nutricionales
                prefs = user.get_nutritional_preferences() or {}
                if 'alergias' in data: prefs['allergies'] = data['alergias']
                if 'condiciones' in data: prefs['conditions'] = data['condiciones']
                user.set_nutritional_preferences(prefs)

                db.session.commit()
                return jsonify({
                    'success': True, 
                    'message': 'Usuario actualizado exitosamente',
                    'user': user.to_json_safe()
                }), 200


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
                'peso_kg', 'altura_cm', 'email'
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