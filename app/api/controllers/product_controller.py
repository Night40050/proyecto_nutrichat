"""
Controlador para gestión de productos
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.database import db
from app.models.productos import Producto, Categoria
from app.models.user import User
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

class ProductController:
    @staticmethod
    @jwt_required()
    def get_products():
        """Obtener todos los productos del usuario"""
        try:
            user_id = get_jwt_identity()
            
            # Paginación
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            
            query = Producto.query.filter_by(user_id=user_id)
            
            # Filtros
            name = request.args.get('name')
            if name:
                query = query.filter(Producto.nombre.ilike(f'%{name}%'))
            
            category = request.args.get('category')
            if category:
                query = query.filter_by(categoria=category)
            
            products = query.paginate(page=page, per_page=per_page, error_out=False)
            
            return jsonify({
                'success': True,
                'products': [product.to_dict() for product in products.items],
                'pagination': {
                    'page': products.page,
                    'per_page': products.per_page,
                    'total': products.total,
                    'pages': products.pages
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error al obtener productos: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    @jwt_required()
    def create_product():
        """Crear nuevo producto"""
        try:
            user_id = get_jwt_identity()
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No se enviaron datos'
                }), 400
            
            # Validar campos requeridos
            required_fields = ['nombre', 'supermercado']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'success': False,
                        'message': f'{field} es requerido'
                    }), 400
            
            # Crear producto
            product = Producto(
                user_id=user_id,
                nombre=data['nombre'],
                supermercado=data['supermercado'],
                precio=data.get('precio'),
                descripcion=data.get('descripcion')
            )
            
            db.session.add(product)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Producto creado exitosamente',
                'product': product.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear producto: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error interno del servidor: {str(e)}'
            }), 500