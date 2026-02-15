"""
Rutas para gestión de listas de compras
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.listas import ListaMercado, ProductosEnLista  # ¡CAMBIA ESTO!
from app.models.database import db
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)
list_bp = Blueprint('lists', __name__, url_prefix='/api/v1/lists')

# ==================== LISTAS ====================

@list_bp.route('/', methods=['GET'])
@jwt_required()
def get_lists():
    """Obtener todas las listas del usuario"""
    try:
        user_id = get_jwt_identity()
        
        # Obtener listas del usuario
        lists = ListaMercado.get_by_usuario(uuid.UUID(user_id))
        
        return jsonify({
            'success': True,
            'lists': [lista.to_dict() for lista in lists]
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo listas: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error obteniendo listas: {str(e)}'
        }), 500

@list_bp.route('/<uuid:list_id>', methods=['GET'])
@jwt_required()
def get_list(list_id):
    """Obtener lista por ID con sus productos"""
    try:
        user_id = get_jwt_identity()
        
        # Buscar lista
        lista = ListaMercado.query.get(list_id)
        
        if not lista:
            return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
        
        # Verificar que pertenezca al usuario
        if str(lista.usuario_id) != user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Obtener productos de la lista
        productos = ProductosEnLista.get_by_lista(list_id)
        
        lista_dict = lista.to_dict()
        lista_dict['productos'] = [p.to_dict() for p in productos]
        
        return jsonify({
            'success': True,
            'list': lista_dict
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo lista: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error obteniendo lista: {str(e)}'
        }), 500

@list_bp.route('/', methods=['POST'])
@jwt_required()
def create_list():
    """Crear nueva lista de compras"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No se enviaron datos'}), 400
        
        nombre = data.get('nombre')
        descripcion = data.get('descripcion', '')
        
        if not nombre:
            return jsonify({'success': False, 'message': 'Nombre es requerido'}), 400
        
        # Crear lista
        lista = ListaMercado.create_lista(
            usuario_id=uuid.UUID(user_id),
            nombre=nombre,
            descripcion=descripcion
        )
        
        db.session.add(lista)
        db.session.commit()
        
        logger.info(f"Lista creada: {lista.lista_id} para usuario {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Lista creada exitosamente',
            'list': lista.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear lista: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al crear lista: {str(e)}'
        }), 500

@list_bp.route('/<uuid:list_id>', methods=['PUT'])
@jwt_required()
def update_list(list_id):
    """Actualizar lista de compras"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No se enviaron datos'}), 400
        
        lista = ListaMercado.query.get(list_id)
        
        if not lista:
            return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
        
        # Verificar que pertenezca al usuario
        if str(lista.usuario_id) != user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Actualizar campos
        if 'nombre' in data:
            lista.nombre = data['nombre']
        
        if 'descripcion' in data:
            lista.descripcion = data['descripcion']
        
        lista.update_timestamp()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Lista actualizada exitosamente',
            'list': lista.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar lista: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al actualizar lista: {str(e)}'
        }), 500

@list_bp.route('/<uuid:list_id>', methods=['DELETE'])
@jwt_required()
def delete_list(list_id):
    """Eliminar lista de compras"""
    try:
        user_id = get_jwt_identity()
        
        lista = ListaMercado.query.get(list_id)
        
        if not lista:
            return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
        
        # Verificar que pertenezca al usuario
        if str(lista.usuario_id) != user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Eliminar primero los productos de la lista
        ProductosEnLista.query.filter_by(lista_id=list_id).delete()
        
        # Eliminar la lista
        db.session.delete(lista)
        db.session.commit()
        
        logger.info(f"Lista eliminada: {list_id} por usuario {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Lista eliminada exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al eliminar lista: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al eliminar lista: {str(e)}'
        }), 500

# ==================== PRODUCTOS EN LISTAS ====================

@list_bp.route('/<uuid:list_id>/products', methods=['POST'])
@jwt_required()
def add_product_to_list(list_id):
    """Añadir producto a lista"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'product_id' not in data:
            return jsonify({'success': False, 'message': 'product_id es requerido'}), 400
        
        # Verificar que la lista existe y pertenece al usuario
        lista = ListaMercado.query.get(list_id)
        
        if not lista:
            return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
        
        if str(lista.usuario_id) != user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        product_id = uuid.UUID(data['product_id'])
        cantidad = data.get('cantidad', 1.0)
        notas = data.get('notas', '')
        
        # Verificar si el producto ya está en la lista
        existing = ProductosEnLista.query.filter_by(
            lista_id=list_id,
            producto_id=product_id
        ).first()
        
        if existing:
            # Actualizar si ya existe
            existing.cantidad = cantidad
            existing.notas = notas
            message = 'Producto actualizado en la lista'
        else:
            # Crear nuevo
            producto_lista = ProductosEnLista.create_item_lista(
                lista_id=list_id,
                producto_id=product_id,
                cantidad=cantidad,
                notas=notas
            )
            db.session.add(producto_lista)
            message = 'Producto añadido a la lista'
        
        # Actualizar timestamp de la lista
        lista.update_timestamp()
        
        db.session.commit()
        
        # Obtener lista actualizada con productos
        productos = ProductosEnLista.get_by_lista(list_id)
        lista_dict = lista.to_dict()
        lista_dict['productos'] = [p.to_dict() for p in productos]
        
        return jsonify({
            'success': True,
            'message': message,
            'list': lista_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al añadir producto a lista: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al añadir producto a lista: {str(e)}'
        }), 500

@list_bp.route('/<uuid:list_id>/products/<uuid:product_id>', methods=['DELETE'])
@jwt_required()
def remove_product_from_list(list_id, product_id):
    """Remover producto de lista"""
    try:
        user_id = get_jwt_identity()
        
        # Verificar que la lista existe y pertenece al usuario
        lista = ListaMercado.query.get(list_id)
        
        if not lista:
            return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
        
        if str(lista.usuario_id) != user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Buscar el producto en la lista
        producto_lista = ProductosEnLista.query.filter_by(
            lista_id=list_id,
            producto_id=product_id
        ).first()
        
        if not producto_lista:
            return jsonify({'success': False, 'message': 'Producto no encontrado en la lista'}), 404
        
        # Eliminar
        db.session.delete(producto_lista)
        
        # Actualizar timestamp de la lista
        lista.update_timestamp()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Producto removido de la lista exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al remover producto de lista: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al remover producto de lista: {str(e)}'
        }), 500

@list_bp.route('/<uuid:list_id>/products/<uuid:product_id>', methods=['PUT'])
@jwt_required()
def update_product_in_list(list_id, product_id):
    """Actualizar producto en lista (cantidad, notas)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verificar que la lista existe y pertenece al usuario
        lista = ListaMercado.query.get(list_id)
        
        if not lista:
            return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
        
        if str(lista.usuario_id) != user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Buscar el producto en la lista
        producto_lista = ProductosEnLista.query.filter_by(
            lista_id=list_id,
            producto_id=product_id
        ).first()
        
        if not producto_lista:
            return jsonify({'success': False, 'message': 'Producto no encontrado en la lista'}), 404
        
        # Actualizar campos
        if 'cantidad' in data:
            producto_lista.cantidad = data['cantidad']
        
        if 'unidad_medida' in data:
            producto_lista.unidad_medida = data['unidad_medida']
        
        if 'precio_unitario' in data:
            producto_lista.precio_unitario = data['precio_unitario']
        
        if 'notas' in data:
            producto_lista.notas = data['notas']
        
        # Actualizar timestamp de la lista
        lista.update_timestamp()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Producto actualizado en la lista'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar producto en lista: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al actualizar producto en lista: {str(e)}'
        }), 500

@list_bp.route('/<uuid:list_id>/calculate', methods=['GET'])
@jwt_required()
def calculate_list_total(list_id):
    """Calcular total de la lista"""
    try:
        user_id = get_jwt_identity()
        
        # Verificar que la lista existe y pertenece al usuario
        lista = ListaMercado.query.get(list_id)
        
        if not lista:
            return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
        
        if str(lista.usuario_id) != user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Obtener productos de la lista
        productos = ProductosEnLista.get_by_lista(list_id)
        
        # Calcular total
        total = 0.0
        for producto in productos:
            if producto.precio_unitario and producto.cantidad:
                total += float(producto.precio_unitario) * float(producto.cantidad)
        
        return jsonify({
            'success': True,
            'total': total,
            'currency': 'COP'  # Pesos colombianos por defecto
        }), 200
        
    except Exception as e:
        logger.error(f"Error al calcular total de lista: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al calcular total: {str(e)}'
        }), 500