"""
Rutas para gestión de condiciones nutricionales
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.condiciones import CondicionNutricional
from app.models.database import db
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
condition_bp = Blueprint('conditions', __name__, url_prefix='/api/v1/conditions')

@condition_bp.route('/', methods=['GET'])
@jwt_required()
def get_conditions():
    """Obtener todas las condiciones del usuario"""
    user_id = get_jwt_identity()
    
    conditions = CondicionNutricional.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'success': True,
        'conditions': [condition.to_dict() for condition in conditions]
    }), 200

@condition_bp.route('/<uuid:condition_id>', methods=['GET'])
@jwt_required()
def get_condition(condition_id):
    """Obtener condición por ID"""
    user_id = get_jwt_identity()
    condition = CondicionNutricional.query.get(condition_id)
    
    if not condition:
        return jsonify({'success': False, 'message': 'Condición no encontrada'}), 404
    
    if str(condition.user_id) != user_id:
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    
    return jsonify({
        'success': True,
        'condition': condition.to_dict()
    }), 200

@condition_bp.route('/', methods=['POST'])
@jwt_required()
def create_condition():
    """Crear nueva condición nutricional"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No se enviaron datos'}), 400
    
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'success': False, 'message': 'Nombre es requerido'}), 400
    
    try:
        condition = CondicionNutricional(
            user_id=user_id,
            nombre=nombre,
            descripcion=data.get('descripcion'),
            tipo=data.get('tipo'),
            severidad=data.get('severidad'),
            fecha_diagnostico=data.get('fecha_diagnostico'),
            restricciones=data.get('restricciones', []),
            recomendaciones=data.get('recomendaciones', []),
            notas=data.get('notas')
        )
        
        db.session.add(condition)
        db.session.commit()
        
        logger.info(f"Condición creada: {condition.id} para usuario {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Condición creada exitosamente',
            'condition': condition.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear condición: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al crear condición: {str(e)}'
        }), 500

@condition_bp.route('/<uuid:condition_id>', methods=['PUT'])
@jwt_required()
def update_condition(condition_id):
    """Actualizar condición nutricional"""
    user_id = get_jwt_identity()
    condition = CondicionNutricional.query.get(condition_id)
    
    if not condition:
        return jsonify({'success': False, 'message': 'Condición no encontrada'}), 404
    
    if str(condition.user_id) != user_id:
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No se enviaron datos'}), 400
    
    # Campos actualizables
    updatable_fields = [
        'nombre', 'descripcion', 'tipo', 'severidad',
        'fecha_diagnostico', 'restricciones', 'recomendaciones', 'notas'
    ]
    
    for field in updatable_fields:
        if field in data:
            setattr(condition, field, data[field])
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Condición actualizada exitosamente',
            'condition': condition.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar condición: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al actualizar condición: {str(e)}'
        }), 500

@condition_bp.route('/<uuid:condition_id>', methods=['DELETE'])
@jwt_required()
def delete_condition(condition_id):
    """Eliminar condición nutricional"""
    user_id = get_jwt_identity()
    condition = CondicionNutricional.query.get(condition_id)
    
    if not condition:
        return jsonify({'success': False, 'message': 'Condición no encontrada'}), 404
    
    if str(condition.user_id) != user_id:
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    
    try:
        db.session.delete(condition)
        db.session.commit()
        
        logger.info(f"Condición eliminada: {condition_id} por usuario {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Condición eliminada exitosamente'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al eliminar condición: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al eliminar condición: {str(e)}'
        }), 500

@condition_bp.route('/check-products', methods=['POST'])
@jwt_required()
def check_products_against_conditions():
    """Verificar productos contra condiciones del usuario"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'product_ids' not in data:
        return jsonify({
            'success': False,
            'message': 'product_ids es requerido (array de IDs)'
        }), 400
    
    product_ids = data['product_ids']
    
    # Obtener condiciones del usuario
    conditions = CondicionNutricional.query.filter_by(user_id=user_id).all()
    
    if not conditions:
        return jsonify({
            'success': True,
            'message': 'Usuario no tiene condiciones configuradas',
            'results': []
        }), 200
    
    # Obtener productos
    from app.models.productos import Producto
    products = Producto.query.filter(
        Producto.id.in_(product_ids),
        Producto.user_id == user_id
    ).all()
    
    results = []
    
    for product in products:
        product_result = {
            'product_id': str(product.id),
            'product_name': product.nombre,
            'warnings': [],
            'safe': True
        }
        
        for condition in conditions:
            warnings = condition.check_product_compatibility(product)
            if warnings:
                product_result['warnings'].extend(warnings)
                product_result['safe'] = False
        
        results.append(product_result)
    
    return jsonify({
        'success': True,
        'results': results
    }), 200

@condition_bp.route('/types', methods=['GET'])
def get_condition_types():
    """Obtener tipos de condiciones disponibles"""
    types = CondicionNutricional.get_available_types()
    
    return jsonify({
        'success': True,
        'types': types
    }), 200

@condition_bp.route('/severities', methods=['GET'])
def get_severity_levels():
    """Obtener niveles de severidad disponibles"""
    severities = CondicionNutricional.get_severity_levels()
    
    return jsonify({
        'success': True,
        'severities': severities
    }), 200