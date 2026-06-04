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

            # SOLO telegram_id es requerido
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

            # ── Si el usuario ya existe, ACTUALIZAMOS sus datos ────────────
            if user:
                if 'nombre' in data: user.nombre = data['nombre']
                if 'peso_kg' in data: user.peso_kg = data['peso_kg']
                if 'altura_cm' in data: user.altura_cm = data['altura_cm']

                # Preferencias nutricionales (objetivo, alergias, condiciones, etc.)
                prefs = user.get_nutritional_preferences() or {}
                if 'objetivo_nutricional' in data:
                    prefs['objetivo_nutricional'] = data['objetivo_nutricional']
                if 'alergias' in data:
                    prefs['allergies'] = data['alergias']
                if 'condiciones' in data:
                    prefs['conditions'] = data['condiciones']
                if 'preferencias' in data:
                    prefs['preferencias'] = data['preferencias']
                if prefs:
                    user.set_nutritional_preferences(prefs)

                # Presupuestos
                if 'budget_monthly' in data or 'budget_weekly' in data:
                    perfil_actual = user.perfil_json or {}
                    nuevo_mensual = data.get('budget_monthly') if 'budget_monthly' in data else perfil_actual.get('budget_monthly')
                    nuevo_semanal = data.get('budget_weekly') if 'budget_weekly' in data else perfil_actual.get('budget_weekly')
                    user.set_budget(monthly=nuevo_mensual, weekly=nuevo_semanal)

                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Usuario actualizado exitosamente',
                    'user': user.to_json_safe()
                }), 200

            # ── Si no existe, CREAMOS un usuario nuevo ─────────────────────
            # Verificar email si se proporciona
            email = data.get('email')
            if email and User.get_by_email(email):
                return jsonify({
                    'success': False,
                    'message': 'El email ya está registrado'
                }), 409

            # Crear usuario con los campos planos
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

            # Guardar preferencias nutricionales (objetivo, alergias, condiciones, etc.)
            prefs = {}
            if 'objetivo_nutricional' in data:
                prefs['objetivo_nutricional'] = data['objetivo_nutricional']
            if 'alergias' in data:
                prefs['allergies'] = data['alergias']
            if 'condiciones' in data:
                prefs['conditions'] = data['condiciones']
            if 'preferencias' in data:
                prefs['preferencias'] = data['preferencias']
            if prefs:
                user.set_nutritional_preferences(prefs)

            # Guardar presupuestos
            if 'budget_monthly' in data or 'budget_weekly' in data:
                user.set_budget(
                    monthly=data.get('budget_monthly'),
                    weekly=data.get('budget_weekly')
                )

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
        """
        Obtiene el usuario para verificar su existencia. 
   
        """
        try:
            # 1. Buscar al usuario
            user = User.get_by_telegram_id(int(telegram_id))

            # 2. Si no existe, devolver 404 (n8n entenderá que es nuevo)
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'Usuario no encontrado'
                }), 404

            # 3. Si existe, devolver sus datos (n8n irá por la ruta de bienvenida)
            return jsonify({
                'success': True,
                'user': user.to_json_safe()
            }), 200
            
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'ID de Telegram inválido'}), 400
        except Exception as e:
            logger.error(f"Error crítico en búsqueda: {str(e)}")
            return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


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

            # 1. Campos planos tradicionales de la tabla (Quitamos los presupuestos de aquí)
            updatable_fields = [
                'nombre', 'telefono', 'sexo', 'fecha_nacimiento', 
                'peso_kg', 'altura_cm', 'email'
            ]

            for field in updatable_fields:
                if field in data:
                    setattr(user, field, data[field])

            # 2. CORRECCIÓN PARA EDAD (age): Calcular año estimado y guardar en fecha_nacimiento
            if 'age' in data:
                try:
                    edad_años = int(data['age'])
                    año_estimado = datetime.now().year - edad_años
                    user.fecha_nacimiento = datetime.strptime(f"{año_estimado}-01-01", "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'message': 'El formato de edad debe ser un número entero'}), 400

            # 3. Actualizar preferencias nutricionales si se envían
            if 'nutritional_preferences' in data:
                user.set_nutritional_preferences(data['nutritional_preferences'])

            # 4. PROCESAMIENTO PARA PRESUPUESTOS (Leyendo del JSON interno del usuario)
            if 'budget_monthly' in data or 'budget_weekly' in data:
                perfil_actual = user.perfil_json or {}
                
                # Si n8n no envía el campo, lo rescatamos de lo que ya hay en el perfil_json actual
                nuevo_mensual = data.get('budget_monthly') if 'budget_monthly' in data else perfil_actual.get('budget_monthly')
                nuevo_semanal = data.get('budget_weekly') if 'budget_weekly' in data else perfil_actual.get('budget_weekly')

                user.set_budget(
                    monthly=nuevo_mensual,
                    weekly=nuevo_semanal
                )

            db.session.commit()
            db.session.refresh(user) # Forzamos a SQLAlchemy a releer el objeto actualizado

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

    @staticmethod
    def delete_user_profile():
        """Elimina definitivamente la cuenta del usuario autenticado y todos sus datos asociados."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify(success=False, message="Usuario no encontrado"), 404
        try:
            db.session.delete(user)
            db.session.commit()
            return jsonify(success=True, message="Cuenta eliminada exitosamente"), 200
        except Exception as e:
            db.session.rollback()
            return jsonify(success=False, message="Error al eliminar la cuenta"), 500