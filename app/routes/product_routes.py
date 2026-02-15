"""
Rutas para gestión de productos (Versión ultra simple)
"""
from flask import Blueprint, jsonify

product_bp = Blueprint('products', __name__, url_prefix='/api/v1/products')

@product_bp.route('/', methods=['GET'])
def index():
    """Endpoint raíz de productos"""
    return jsonify({
        'success': True,
        'message': 'API de productos funcionando',
        'version': '1.0'
    }), 200

@product_bp.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'products-api'
    }), 200