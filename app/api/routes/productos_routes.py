"""
Rutas de productos: categorías, productos, nutrición y snapshots
"""
from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.api.controllers.productos_controller import ProductosController

# Crear blueprint para rutas de productos
productos_bp = Blueprint('productos', __name__)


# ============================================================
# PRODUCTOS Y CATEGORIAS
# ============================================================

@productos_bp.route('/categorias', methods=['POST'])
def create_categoria():
    """
    Crear una nueva categoría
    
    Body JSON:
    {
        "nombre": "Verduras",      // REQUERIDO
        "descripcion": "..."      // OPCIONAL
    }
    
    Response:
    {
        "success": true,
        "message": "Categoría creada exitosamente",
        "data": {...}
    }
    """
    return ProductosController.create_categoria()


@productos_bp.route('/categorias', methods=['GET'])
def get_all_categorias():
    """
    Obtener todas las categorías
    
    Response:
    {
        "success": true,
        "data": [...],
        "count": 10
    }
    """
    return ProductosController.get_all_categorias()


@productos_bp.route('/categorias/<int:categoria_id>', methods=['GET'])
def get_categoria_by_id(categoria_id):
    """
    Obtener categoría por ID
    
    Parámetros:
    - categoria_id: ID de la categoría
    
    Response:
    {
        "success": true,
        "data": {...}
    }
    """
    return ProductosController.get_categoria_by_id(categoria_id)


@productos_bp.route('/productos', methods=['POST'])
def create_producto():
    """
    Crear un nuevo producto
    
    Body JSON:
    {
        "nombre": "Tomate",           // REQUERIDO
        "marca": "Marca X",          // OPCIONAL
        "categoria_id": 1,          // OPCIONAL
        "descripcion": "...",        // OPCIONAL
        "url_producto": "...",       // OPCIONAL
        "url_imagen": "...",         // OPCIONAL
        "codigo_fuente": "...",      // OPCIONAL
        "producto_hash": "..."       // OPCIONAL
    }
    
    Response:
    {
        "success": true,
        "message": "Producto creado exitosamente",
        "data": {...}
    }
    """
    return ProductosController.create_producto()

@productos_bp.route('/productos', methods=['GET'])
def get_all_productos():
    """
    Obtener todos los productos (Soporta el parámetro ?limit= en n8n)
    """
    return ProductosController.get_all_productos()

@productos_bp.route('/productos/<producto_id>', methods=['GET'])
def get_producto_by_id(producto_id):
    """
    Obtener producto por ID
    
    Parámetros:
    - producto_id: ID del producto (UUID)
    
    Response:
    {
        "success": true,
        "data": {...}
    }
    """
    return ProductosController.get_producto_by_id(producto_id)


@productos_bp.route('/productos/<producto_id>', methods=['PUT'])
@jwt_required()
def update_producto(producto_id):
    """
    Actualizar producto
    
    Headers:
    Authorization: Bearer <access_token>
    
    Parámetros:
    - producto_id: ID del producto (UUID)
    
    Body JSON (todos opcionales):
    {
        "nombre": "...",
        "marca": "...",
        "categoria_id": 1,
        "descripcion": "...",
        "url_producto": "...",
        "url_imagen": "..."
    }
    
    Response:
    {
        "success": true,
        "message": "Producto actualizado exitosamente",
        "data": {...}
    }
    """
    return ProductosController.update_producto(producto_id)


@productos_bp.route('/productos/search', methods=['GET'])
def search_productos_by_nombre():
    """
    Buscar productos por nombre (búsqueda parcial)
    
    Query params:
    - nombre: Nombre a buscar (requerido)
    
    Response:
    {
        "success": true,
        "data": [...],
        "count": 5
    }
    """
    return ProductosController.search_productos_by_nombre()


@productos_bp.route('/productos/categoria/<int:categoria_id>', methods=['GET'])
def get_productos_by_categoria(categoria_id):
    """
    Obtener productos por categoría
    
    Parámetros:
    - categoria_id: ID de la categoría
    
    Response:
    {
        "success": true,
        "data": [...],
        "count": 15
    }
    """
    return ProductosController.get_productos_by_categoria(categoria_id)


@productos_bp.route('/productos/hash', methods=['GET'])
def get_producto_by_hash():
    """
    Obtener producto por hash
    
    Query params:
    - hash: Hash del producto (requerido)
    
    Response:
    {
        "success": true,
        "data": {...}
    }
    """
    return ProductosController.get_producto_by_hash()


@productos_bp.route('/productos/nutricion', methods=['POST'])
def create_nutricion():
    """
    Crear información nutricional para un producto
    
    Body JSON:
    {
        "producto_id": "uuid",          // REQUERIDO
        "porcion_g": 100.0,            // OPCIONAL
        "calorias_kcal": 250.5,        // OPCIONAL
        "proteinas_g": 10.0,           // OPCIONAL
        "grasas_totales_g": 5.0,       // OPCIONAL
        "grasas_saturadas_g": 2.0,     // OPCIONAL
        "carbohidratos_g": 30.0,       // OPCIONAL
        "azucares_g": 15.0,            // OPCIONAL
        "fibra_g": 3.0,                // OPCIONAL
        "sodio_mg": 500.0,             // OPCIONAL
        "colesterol_mg": 0.0,          // OPCIONAL
        "micronutrientes": {...},      // OPCIONAL
        "ig": 50.0,                    // OPCIONAL
        "carga_glucemica": 25.0,       // OPCIONAL
        "fuente": "..."                // OPCIONAL
    }
    
    Response:
    {
        "success": true,
        "message": "Información nutricional creada exitosamente",
        "data": {...}
    }
    """
    return ProductosController.create_nutricion()


@productos_bp.route('/productos/<producto_id>/nutricion', methods=['GET'])
def get_nutricion_by_producto(producto_id):
    """
    Obtener información nutricional por producto
    
    Parámetros:
    - producto_id: ID del producto (UUID)
    
    Response:
    {
        "success": true,
        "data": {...}
    }
    """
    return ProductosController.get_nutricion_by_producto(producto_id)


@productos_bp.route('/productos/snapshot', methods=['POST'])
def create_snapshot():
    """
    Crear un snapshot de producto (precio, disponibilidad, etc.)
    
    Body JSON:
    {
        "producto_id": "uuid",         // REQUERIDO
        "precio": 25.50,               // OPCIONAL
        "unidad_medida": "kg",         // OPCIONAL
        "disponibilidad": true,        // OPCIONAL
        "fuente": "...",               // OPCIONAL
        "impacto_ambiental": {...},   // OPCIONAL
        "atributos_json": {...}        // OPCIONAL
    }
    
    Response:
    {
        "success": true,
        "message": "Snapshot creado exitosamente",
        "data": {...}
    }
    """
    return ProductosController.create_snapshot()


@productos_bp.route('/productos/<producto_id>/snapshots', methods=['GET'])
def get_snapshots_by_producto(producto_id):
    """
    Obtener snapshots por producto
    
    Parámetros:
    - producto_id: ID del producto (UUID)
    
    Query params:
    - limit: Número máximo de resultados (opcional)
    
    Response:
    {
        "success": true,
        "data": [...],
        "count": 10
    }
    """
    return ProductosController.get_snapshots_by_producto(producto_id)


@productos_bp.route('/productos/<producto_id>/snapshot/latest', methods=['GET'])
def get_latest_snapshot_by_producto(producto_id):
    """
    Obtener el snapshot más reciente de un producto
    
    Parámetros:
    - producto_id: ID del producto (UUID)
    
    Response:
    {
        "success": true,
        "data": {...}
    }
    """
    return ProductosController.get_latest_snapshot_by_producto(producto_id)


@productos_bp.route('/productos/snapshots/latest-bulk', methods=['GET'])
def get_latest_snapshots_bulk():
    # SELECT DISTINCT ON (producto_id) producto_id, precio, disponibilidad
    # FROM producto_snapshot ORDER BY producto_id, fecha_captura DESC
    return ProductosController.get_latest_snapshots_bulk()