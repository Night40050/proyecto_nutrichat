"""
Rutas para gestión del sistema
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.models.configuracion_sistema import ConfiguracionSistema
from app.models.scraping_cache import ScrapingCache
from app.models.audit_log import AuditLog
from app.models.reportes import Reporte
from app.models.database import db
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
system_bp = Blueprint('system', __name__, url_prefix='/api/v1/system')

@system_bp.route('/config', methods=['GET'])
@jwt_required()
def get_config():
    """Obtener configuración del sistema"""
    configs = ConfiguracionSistema.query.all()
    
    config_dict = {}
    for config in configs:
        config_dict[config.clave] = config.get_value()
    
    return jsonify({
        'success': True,
        'config': config_dict
    }), 200

@system_bp.route('/config/<string:key>', methods=['GET'])
@jwt_required()
def get_config_value(key):
    """Obtener valor de configuración específico"""
    config = ConfiguracionSistema.query.filter_by(clave=key).first()
    
    if not config:
        return jsonify({
            'success': False,
            'message': f'Configuración {key} no encontrada'
        }), 404
    
    return jsonify({
        'success': True,
        'key': config.clave,
        'value': config.get_value(),
        'type': config.tipo,
        'description': config.descripcion
    }), 200

@system_bp.route('/config/<string:key>', methods=['PUT'])
@jwt_required()
def update_config(key):
    """Actualizar configuración del sistema (solo admin)"""
    # Verificar si el usuario es admin
    # Aquí deberías agregar lógica de verificación de roles
    
    config = ConfiguracionSistema.query.filter_by(clave=key).first()
    
    if not config:
        return jsonify({
            'success': False,
            'message': f'Configuración {key} no encontrada'
        }), 404
    
    data = request.get_json()
    if not data or 'value' not in data:
        return jsonify({
            'success': False,
            'message': 'Value es requerido'
        }), 400
    
    try:
        config.set_value(data['value'])
        db.session.commit()
        
        logger.info(f"Configuración actualizada: {key} = {data['value']}")
        
        return jsonify({
            'success': True,
            'message': 'Configuración actualizada exitosamente',
            'config': {
                'key': config.clave,
                'value': config.get_value(),
                'type': config.tipo
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar configuración: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al actualizar configuración: {str(e)}'
        }), 500

@system_bp.route('/cache/stats', methods=['GET'])
@jwt_required()
def get_cache_stats():
    """Obtener estadísticas de cache"""
    total_entries = ScrapingCache.query.count()
    expired_entries = ScrapingCache.query.filter(
        ScrapingCache.expires_at < datetime.utcnow()
    ).count()
    
    # Entradas por supermercado
    by_supermarket = db.session.query(
        ScrapingCache.supermercado,
        db.func.count(ScrapingCache.id)
    ).group_by(ScrapingCache.supermercado).all()
    
    # Tamaño total aproximado
    size_query = db.session.query(
        db.func.sum(
            db.func.length(ScrapingCache.data) +
            db.func.length(ScrapingCache.url)
        )
    ).scalar()
    
    total_size_kb = (size_query or 0) / 1024 if size_query else 0
    
    return jsonify({
        'success': True,
        'stats': {
            'total_entries': total_entries,
            'expired_entries': expired_entries,
            'valid_entries': total_entries - expired_entries,
            'by_supermarket': dict(by_supermarket),
            'estimated_size_kb': round(total_size_kb, 2)
        }
    }), 200

@system_bp.route('/cache/clear-expired', methods=['POST'])
@jwt_required()
def clear_expired_cache():
    """Limpiar cache expirado"""
    try:
        deleted = ScrapingCache.clear_expired()
        
        return jsonify({
            'success': True,
            'message': f'Se eliminaron {deleted} entradas expiradas del cache'
        }), 200
        
    except Exception as e:
        logger.error(f"Error al limpiar cache: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al limpiar cache: {str(e)}'
        }), 500

@system_bp.route('/logs', methods=['GET'])
@jwt_required()
def get_logs():
    """Obtener logs del sistema"""
    # Paginación
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Filtros
    query = AuditLog.query
    
    level = request.args.get('level')
    if level:
        query = query.filter_by(nivel=level)
    
    user_id = request.args.get('user_id')
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    action = request.args.get('action')
    if action:
        query = query.filter_by(accion=action)
    
    start_date = request.args.get('start_date')
    if start_date:
        try:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at >= start_date)
        except ValueError:
            pass
    
    end_date = request.args.get('end_date')
    if end_date:
        try:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at <= end_date)
        except ValueError:
            pass
    
    # Ordenar por fecha más reciente primero
    query = query.order_by(AuditLog.created_at.desc())
    
    logs = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in logs.items],
        'pagination': {
            'page': logs.page,
            'per_page': logs.per_page,
            'total': logs.total,
            'pages': logs.pages
        }
    }), 200

@system_bp.route('/reports', methods=['GET'])
@jwt_required()
def get_reports():
    """Obtener reportes del sistema"""
    user_id = get_jwt_identity()
    
    # Solo reportes del usuario
    reports = Reporte.query.filter_by(user_id=user_id).order_by(
        Reporte.created_at.desc()
    ).all()
    
    return jsonify({
        'success': True,
        'reports': [report.to_dict() for report in reports]
    }), 200

@system_bp.route('/reports/<uuid:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    """Obtener reporte específico"""
    user_id = get_jwt_identity()
    report = Reporte.query.get(report_id)
    
    if not report:
        return jsonify({'success': False, 'message': 'Reporte no encontrado'}), 404
    
    if str(report.user_id) != user_id:
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    
    return jsonify({
        'success': True,
        'report': report.to_dict()
    }), 200

@system_bp.route('/reports/generate', methods=['POST'])
@jwt_required()
def generate_report():
    """Generar nuevo reporte"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No se enviaron datos'}), 400
    
    report_type = data.get('type')
    if not report_type:
        return jsonify({'success': False, 'message': 'Tipo de reporte es requerido'}), 400
    
    try:
        report = Reporte.generar_reporte(
            user_id=user_id,
            tipo=report_type,
            parametros=data.get('parameters', {}),
            formato=data.get('format', 'json')
        )
        
        return jsonify({
            'success': True,
            'message': 'Reporte generado exitosamente',
            'report': report.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error al generar reporte: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al generar reporte: {str(e)}'
        }), 500

@system_bp.route('/health', methods=['GET'])
def health_check():
    """Verificar estado del sistema"""
    from app.models.database import db
    from sqlalchemy import text
    
    try:
        # Verificar conexión a la base de datos
        db.session.execute(text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        db_status = 'unhealthy'
        db_error = str(e)
    
    # Obtener estadísticas básicas
    from app.models.user import User
    from app.models.productos import Producto
    
    try:
        user_count = User.query.count()
        product_count = Producto.query.count()
    except:
        user_count = product_count = 'N/A'
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'database': db_status,
            'api': 'healthy'
        },
        'statistics': {
            'total_users': user_count,
            'total_products': product_count
        }
    }), 200

@system_bp.route('/metrics', methods=['GET'])
@jwt_required()
def get_metrics():
    """Obtener métricas del sistema"""
    # Solo para administradores
    # Aquí deberías agregar verificación de roles
    
    from datetime import datetime, timedelta
    
    # Métricas de usuarios
    total_users = db.session.query(db.func.count(User.id)).scalar()
    
    # Usuarios activos en los últimos 30 días
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = db.session.query(db.func.count(User.id)).filter(
        User.ultima_conexion >= thirty_days_ago
    ).scalar()
    
    # Métricas de productos
    total_products = db.session.query(db.func.count(Producto.id)).scalar()
    
    # Productos por supermercado
    from app.models.productos import Producto
    products_by_market = db.session.query(
        Producto.supermercado,
        db.func.count(Producto.id)
    ).group_by(Producto.supermercado).all()
    
    # Métricas de listas
    from app.models.listas import ListaMercado
    total_lists = db.session.query(db.func.count(ListaMercado.id)).scalar()
    
    # Métricas de cache
    from app.models.scraping_cache import ScrapingCache
    cache_hits = db.session.query(db.func.sum(ScrapingCache.hits)).scalar() or 0
    
    return jsonify({
        'success': True,
        'metrics': {
            'users': {
                'total': total_users,
                'active_last_30_days': active_users,
                'active_percentage': round((active_users / total_users * 100) if total_users > 0 else 0, 2)
            },
            'products': {
                'total': total_products,
                'by_supermarket': dict(products_by_market)
            },
            'lists': {
                'total': total_lists
            },
            'cache': {
                'total_hits': cache_hits
            }
        }
    }), 200