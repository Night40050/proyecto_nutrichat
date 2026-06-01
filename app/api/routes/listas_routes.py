"""
Rutas de listas de mercado: listas y productos en listas
"""
from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.api.controllers.listas_controller import ListasController

# Crear blueprint para rutas de listas
listas_bp = Blueprint('listas', __name__)


# ============================================================
# LISTAS DE MERCADO
# ============================================================

@listas_bp.route('/listas', methods=['POST'])
@jwt_required()
def create_lista():
    """
    Crear una nueva lista de mercado
    
    Headers:
    Authorization: Bearer <access_token>
    
    Body JSON:
    {
        "nombre": "Lista Semanal",     // OPCIONAL
        "descripcion": "..."          // OPCIONAL
    }
    
    Response:
    {
        "success": true,
        "message": "Lista creada exitosamente",
        "data": {...}
    }
    """
    return ListasController.create_lista()

@listas_bp.route('/listas/completa', methods=['POST'])
@jwt_required()
def create_lista_completa():
    return ListasController.create_lista_completa()

@listas_bp.route('/listas', methods=['GET'])
@jwt_required()
def get_listas_by_usuario():
    """
    Obtener listas del usuario autenticado
    
    Headers:
    Authorization: Bearer <access_token>
    
    Response:
    {
        "success": true,
        "data": [...],
        "count": 5
    }
    """
    return ListasController.get_listas_by_usuario()


@listas_bp.route('/listas/search', methods=['GET'])
@jwt_required()
def search_listas_by_nombre():
    """
    Buscar listas por nombre (búsqueda parcial)
    
    Headers:
    Authorization: Bearer <access_token>
    
    Query params:
    - nombre: Nombre a buscar (requerido)
    
    Response:
    {
        "success": true,
        "data": [...],
        "count": 2
    }
    """
    return ListasController.search_listas_by_nombre()


@listas_bp.route('/listas/<lista_id>', methods=['GET'])
@jwt_required()
def get_lista_by_id(lista_id):
    """
    Obtener lista por ID (solo si pertenece al usuario autenticado)
    
    Headers:
    Authorization: Bearer <access_token>
    
    Parámetros:
    - lista_id: ID de la lista (UUID)
    
    Response:
    {
        "success": true,
        "data": {...}
    }
    """
    return ListasController.get_lista_by_id(lista_id)


@listas_bp.route('/listas/<lista_id>', methods=['PUT'])
@jwt_required()
def update_lista(lista_id):
    """
    Actualizar lista de mercado
    
    Headers:
    Authorization: Bearer <access_token>
    
    Parámetros:
    - lista_id: ID de la lista (UUID)
    
    Body JSON (todos opcionales):
    {
        "nombre": "...",
        "descripcion": "..."
    }
    
    Response:
    {
        "success": true,
        "message": "Lista actualizada exitosamente",
        "data": {...}
    }
    """
    return ListasController.update_lista(lista_id)


@listas_bp.route('/listas/<lista_id>', methods=['DELETE'])
@jwt_required()
def delete_lista(lista_id):
    """
    Eliminar lista de mercado
    
    Headers:
    Authorization: Bearer <access_token>
    
    Parámetros:
    - lista_id: ID de la lista (UUID)
    
    Response:
    {
        "success": true,
        "message": "Lista eliminada exitosamente"
    }
    """
    return ListasController.delete_lista(lista_id)


# ============================================================
# PRODUCTOS EN LISTA
# ============================================================

@listas_bp.route('/listas/<lista_id>/productos', methods=['POST'])
@jwt_required()
def add_producto_to_lista(lista_id):
    """
    Agregar producto a una lista
    
    Headers:
    Authorization: Bearer <access_token>
    
    Parámetros:
    - lista_id: ID de la lista (UUID)
    
    Body JSON:
    {
        "producto_id": "uuid",        // REQUERIDO
        "cantidad": 2.5,              // OPCIONAL (default: 1)
        "unidad_medida": "kg",        // OPCIONAL
        "precio_unitario": 25.50,     // OPCIONAL
        "notas": "..."               // OPCIONAL
    }
    
    Response:
    {
        "success": true,
        "message": "Producto agregado a la lista exitosamente",
        "data": {...}
    }
    """
    return ListasController.add_producto_to_lista(lista_id)


@listas_bp.route('/listas/<lista_id>/productos', methods=['GET'])
@jwt_required()
def get_productos_by_lista(lista_id):
    """
    Obtener productos de una lista
    
    Headers:
    Authorization: Bearer <access_token>
    
    Parámetros:
    - lista_id: ID de la lista (UUID)
    
    Response:
    {
        "success": true,
        "data": [...],
        "count": 10
    }
    """
    return ListasController.get_productos_by_lista(lista_id)


@listas_bp.route('/listas/<lista_id>/productos/<producto_id>', methods=['PUT'])
@jwt_required()
def update_producto_in_lista(lista_id, producto_id):
    """
    Actualizar producto en lista
    
    Headers:
    Authorization: Bearer <access_token>
    
    Parámetros:
    - lista_id: ID de la lista (UUID)
    - producto_id: ID del producto (UUID)
    
    Body JSON (todos opcionales):
    {
        "cantidad": 3.0,
        "unidad_medida": "kg",
        "precio_unitario": 30.00,
        "notas": "..."
    }
    
    Response:
    {
        "success": true,
        "message": "Producto actualizado exitosamente",
        "data": {...}
    }
    """
    return ListasController.update_producto_in_lista(lista_id, producto_id)


@listas_bp.route('/listas/<lista_id>/productos/<producto_id>', methods=['DELETE'])
@jwt_required()
def remove_producto_from_lista(lista_id, producto_id):
    """
    Eliminar producto de una lista
    
    Headers:
    Authorization: Bearer <access_token>
    
    Parámetros:
    - lista_id: ID de la lista (UUID)
    - producto_id: ID del producto (UUID)
    
    Response:
    {
        "success": true,
        "message": "Producto eliminado de la lista exitosamente"
    }
    """
    return ListasController.remove_producto_from_lista(lista_id, producto_id)

