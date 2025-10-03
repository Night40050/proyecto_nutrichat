"""
Controlador de perfil nutricional para NutriChat
Maneja condiciones médicas, preferencias nutricionales y recomendaciones
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.database import db
from app.models.user import User
from decimal import Decimal
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class ProfileController:
	@staticmethod
	@jwt_required()
	def get_profile():
		"""Obtener perfil completo del usuario autenticado"""
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
				'profile': user.to_json_safe()
			}), 200
			
		except Exception as e:
			logger.error(f"Error al obtener perfil: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def update_basic_info():
		"""Actualizar información básica del perfil"""
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
			
			# Campos actualizables básicos
			updatable_fields = [
				'nombre', 'telefono', 'sexo', 'fecha_nacimiento', 
				'peso_kg', 'altura_cm'
			]
			
			# Validaciones específicas
			if 'peso_kg' in data:
				peso = data['peso_kg']
				if peso is not None and (peso <= 0 or peso > 500):
					return jsonify({
						'success': False,
						'message': 'El peso debe estar entre 1 y 500 kg'
					}), 400
			
			if 'altura_cm' in data:
				altura = data['altura_cm']
				if altura is not None and (altura <= 0 or altura > 300):
					return jsonify({
						'success': False,
						'message': 'La altura debe estar entre 1 y 300 cm'
					}), 400
			
			# Actualizar campos
			for field in updatable_fields:
				if field in data:
					setattr(user, field, data[field])
			
			db.session.commit()
			
			return jsonify({
				'success': True,
				'message': 'Información básica actualizada exitosamente',
				'profile': user.to_json_safe()
			}), 200
			
		except Exception as e:
			db.session.rollback()
			logger.error(f"Error al actualizar información básica: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def get_medical_conditions():
		"""Obtener condiciones médicas del usuario"""
		try:
			user_id = get_jwt_identity()
			user = User.query.get(user_id)
			
			if not user:
				return jsonify({
					'success': False,
					'message': 'Usuario no encontrado'
				}), 404
			
			perfil_data = user._get_perfil_data()
			conditions = perfil_data.get('medical_conditions', [])
			
			return jsonify({
				'success': True,
				'medical_conditions': conditions
			}), 200
			
		except Exception as e:
			logger.error(f"Error al obtener condiciones médicas: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def add_medical_condition():
		"""Agregar nueva condición médica"""
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
			
			# Validar campos requeridos
			required_fields = ['name', 'severity']
			for field in required_fields:
				if field not in data or not data[field]:
					return jsonify({
						'success': False,
						'message': f'El campo {field} es requerido'
					}), 400
			
			# Validar severidad
			valid_severities = ['leve', 'moderada', 'severa']
			if data['severity'] not in valid_severities:
				return jsonify({
					'success': False,
					'message': f'Severidad debe ser una de: {", ".join(valid_severities)}'
				}), 400
			
			# Crear nueva condición
			new_condition = {
				'id': str(uuid.uuid4()),
				'name': data['name'],
				'severity': data['severity'],
				'description': data.get('description', ''),
				'dietary_restrictions': data.get('dietary_restrictions', []),
				'created_at': datetime.utcnow().isoformat(),
				'active': True
			}
			
			# Obtener condiciones existentes
			perfil_data = user._get_perfil_data()
			conditions = perfil_data.get('medical_conditions', [])
			
			# Verificar si ya existe una condición con el mismo nombre
			existing_condition = next((c for c in conditions if c['name'].lower() == data['name'].lower()), None)
			if existing_condition:
				return jsonify({
					'success': False,
					'message': 'Ya existe una condición médica con ese nombre'
				}), 409
			
			# Agregar nueva condición
			conditions.append(new_condition)
			perfil_data['medical_conditions'] = conditions
			user._set_perfil_data(perfil_data)
			
			db.session.commit()
			
			return jsonify({
				'success': True,
				'message': 'Condición médica agregada exitosamente',
				'condition': new_condition
			}), 201
			
		except Exception as e:
			db.session.rollback()
			logger.error(f"Error al agregar condición médica: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def update_medical_condition(condition_id):
		"""Actualizar condición médica específica"""
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
			
			# Obtener condiciones existentes
			perfil_data = user._get_perfil_data()
			conditions = perfil_data.get('medical_conditions', [])
			
			# Buscar la condición a actualizar
			condition_index = next((i for i, c in enumerate(conditions) if c['id'] == condition_id), None)
			if condition_index is None:
				return jsonify({
					'success': False,
					'message': 'Condición médica no encontrada'
				}), 404
			
			# Validar severidad si se proporciona
			if 'severity' in data:
				valid_severities = ['leve', 'moderada', 'severa']
				if data['severity'] not in valid_severities:
					return jsonify({
						'success': False,
						'message': f'Severidad debe ser una de: {", ".join(valid_severities)}'
					}), 400
			
			# Actualizar campos
			updatable_fields = ['name', 'severity', 'description', 'dietary_restrictions', 'active']
			for field in updatable_fields:
				if field in data:
					conditions[condition_index][field] = data[field]
			
			conditions[condition_index]['updated_at'] = datetime.utcnow().isoformat()
			
			perfil_data['medical_conditions'] = conditions
			user._set_perfil_data(perfil_data)
			
			db.session.commit()
			
			return jsonify({
				'success': True,
				'message': 'Condición médica actualizada exitosamente',
				'condition': conditions[condition_index]
			}), 200
			
		except Exception as e:
			db.session.rollback()
			logger.error(f"Error al actualizar condición médica: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def delete_medical_condition(condition_id):
		"""Eliminar condición médica"""
		try:
			user_id = get_jwt_identity()
			user = User.query.get(user_id)
			
			if not user:
				return jsonify({
					'success': False,
					'message': 'Usuario no encontrado'
				}), 404
			
			# Obtener condiciones existentes
			perfil_data = user._get_perfil_data()
			conditions = perfil_data.get('medical_conditions', [])
			
			# Buscar y eliminar la condición
			original_count = len(conditions)
			conditions = [c for c in conditions if c['id'] != condition_id]
			
			if len(conditions) == original_count:
				return jsonify({
					'success': False,
					'message': 'Condición médica no encontrada'
				}), 404
			
			perfil_data['medical_conditions'] = conditions
			user._set_perfil_data(perfil_data)
			
			db.session.commit()
			
			return jsonify({
				'success': True,
				'message': 'Condición médica eliminada exitosamente'
			}), 200
			
		except Exception as e:
			db.session.rollback()
			logger.error(f"Error al eliminar condición médica: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def update_nutritional_preferences():
		"""Actualizar preferencias nutricionales"""
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
			
			# Validar estructura de preferencias
			valid_preferences = {
				'dietary_type': ['omnivoro', 'vegetariano', 'vegano', 'pescetariano'],
				'allergies': list,  # Lista de alergias
				'dislikes': list,   # Lista de alimentos que no le gustan
				'objectives': ['perder_peso', 'mantener_peso', 'ganar_peso', 'ganar_musculo', 'mejorar_salud'],
				'meal_frequency': int,  # Número de comidas por día
				'cooking_time': ['poco', 'moderado', 'mucho'],  # Tiempo disponible para cocinar
				'budget_preference': ['economico', 'moderado', 'premium']
			}
			
			preferences = {}
			
			# Validar cada preferencia
			for key, value in data.items():
				if key in valid_preferences:
					expected_type = valid_preferences[key]
					
					if isinstance(expected_type, list) and isinstance(value, str):
						# Validar opciones específicas
						if value not in expected_type:
							return jsonify({
								'success': False,
								'message': f'{key} debe ser una de: {", ".join(expected_type)}'
							}), 400
						preferences[key] = value
					elif expected_type == list and isinstance(value, list):
						# Listas (alergias, dislikes)
						preferences[key] = value
					elif expected_type == int and isinstance(value, int):
						# Validar meal_frequency
						if key == 'meal_frequency' and (value < 1 or value > 8):
							return jsonify({
								'success': False,
								'message': 'meal_frequency debe estar entre 1 y 8'
							}), 400
						preferences[key] = value
					else:
						preferences[key] = value
			
			# Actualizar preferencias
			user.set_nutritional_preferences(preferences)
			db.session.commit()
			
			return jsonify({
				'success': True,
				'message': 'Preferencias nutricionales actualizadas exitosamente',
				'preferences': user.get_nutritional_preferences()
			}), 200
			
		except Exception as e:
			db.session.rollback()
			logger.error(f"Error al actualizar preferencias nutricionales: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def update_budget():
		"""Actualizar presupuesto del usuario"""
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
			
			monthly = data.get('monthly')
			weekly = data.get('weekly')
			
			# Validar valores
			if monthly is not None:
				if not isinstance(monthly, (int, float)) or monthly < 0:
					return jsonify({
						'success': False,
						'message': 'El presupuesto mensual debe ser un número positivo'
					}), 400
				monthly = Decimal(str(monthly))
			
			if weekly is not None:
				if not isinstance(weekly, (int, float)) or weekly < 0:
					return jsonify({
						'success': False,
						'message': 'El presupuesto semanal debe ser un número positivo'
					}), 400
				weekly = Decimal(str(weekly))
			
			# Actualizar presupuesto
			user.set_budget(monthly=monthly, weekly=weekly)
			db.session.commit()
			
			return jsonify({
				'success': True,
				'message': 'Presupuesto actualizado exitosamente',
				'budget': {
					'monthly': float(user.budget_monthly) if user.budget_monthly else None,
					'weekly': float(user.budget_weekly) if user.budget_weekly else None
				}
			}), 200
			
		except Exception as e:
			db.session.rollback()
			logger.error(f"Error al actualizar presupuesto: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500
	
	@staticmethod
	@jwt_required()
	def get_nutrition_recommendations():
		"""Obtener recomendaciones nutricionales basadas en el perfil del usuario"""
		try:
			user_id = get_jwt_identity()
			user = User.query.get(user_id)
			
			if not user:
				return jsonify({
					'success': False,
					'message': 'Usuario no encontrado'
				}), 404
			
			# Obtener datos del perfil
			preferences = user.get_nutritional_preferences()
			perfil_data = user._get_perfil_data()
			medical_conditions = perfil_data.get('medical_conditions', [])
			
			# Generar recomendaciones básicas
			recommendations = {
				'general': [],
				'dietary': [],
				'medical': [],
				'budget': [],
				'caloric_needs': None
			}
			
			# Recomendaciones generales basadas en objetivos
			objective = preferences.get('objectives')
			if objective == 'perder_peso':
				recommendations['general'].append('Mantén un déficit calórico moderado de 300-500 calorías')
				recommendations['general'].append('Prioriza proteínas magras y vegetales')
			elif objective == 'ganar_peso':
				recommendations['general'].append('Mantén un superávit calórico de 300-500 calorías')
				recommendations['general'].append('Incluye grasas saludables y carbohidratos complejos')
			elif objective == 'ganar_musculo':
				recommendations['general'].append('Consume 1.6-2.2g de proteína por kg de peso corporal')
				recommendations['general'].append('Incluye ejercicio de resistencia en tu rutina')
			
			# Recomendaciones dietéticas
			dietary_type = preferences.get('dietary_type')
			if dietary_type == 'vegetariano':
				recommendations['dietary'].append('Asegúrate de obtener suficiente vitamina B12')
				recommendations['dietary'].append('Combina legumbres con cereales para proteína completa')
			elif dietary_type == 'vegano':
				recommendations['dietary'].append('Suplementa vitamina B12, D3 y omega-3')
				recommendations['dietary'].append('Incluye fuentes de hierro con vitamina C')
			
			# Recomendaciones médicas
			active_conditions = [c for c in medical_conditions if c.get('active', True)]
			for condition in active_conditions:
				if 'diabetes' in condition['name'].lower():
					recommendations['medical'].append('Controla el índice glucémico de tus comidas')
					recommendations['medical'].append('Distribuye los carbohidratos a lo largo del día')
				elif 'hipertension' in condition['name'].lower():
					recommendations['medical'].append('Reduce el consumo de sodio')
					recommendations['medical'].append('Aumenta el consumo de potasio (frutas y verduras)')
				elif 'colesterol' in condition['name'].lower():
					recommendations['medical'].append('Limita las grasas saturadas y trans')
					recommendations['medical'].append('Incluye fibra soluble (avena, legumbres)')
			
			# Recomendaciones de presupuesto
			budget_pref = preferences.get('budget_preference', 'moderado')
			if budget_pref == 'economico':
				recommendations['budget'].append('Prioriza legumbres, huevos y pollo como fuentes de proteína')
				recommendations['budget'].append('Compra frutas y verduras de temporada')
			elif budget_pref == 'premium':
				recommendations['budget'].append('Considera superalimentos como quinoa, chía y arándanos')
				recommendations['budget'].append('Incluye pescados grasos y frutos secos')
			
			# Calcular necesidades calóricas básicas (fórmula Harris-Benedict simplificada)
			if user.peso_kg and user.altura_cm and user.age and user.sexo:
				peso = float(user.peso_kg)
				altura = float(user.altura_cm)
				edad = user.age
				
				if user.sexo.lower() == 'masculino':
					bmr = 88.362 + (13.397 * peso) + (4.799 * altura) - (5.677 * edad)
				else:
					bmr = 447.593 + (9.247 * peso) + (3.098 * altura) - (4.330 * edad)
				
				# Factor de actividad moderado (1.55)
				recommendations['caloric_needs'] = round(bmr * 1.55)
			
			return jsonify({
				'success': True,
				'recommendations': recommendations,
				'profile_summary': {
					'bmi': user.bmi,
					'age': user.age,
					'dietary_type': preferences.get('dietary_type'),
					'objectives': preferences.get('objectives'),
					'active_conditions': len(active_conditions)
				}
			}), 200
			
		except Exception as e:
			logger.error(f"Error al generar recomendaciones: {str(e)}")
			return jsonify({
				'success': False,
				'message': 'Error interno del servidor'
			}), 500