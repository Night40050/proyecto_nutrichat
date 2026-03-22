"""
Rutas de Telegram: webhook y sesiones
"""
from flask import Blueprint, jsonify, request
from app.api.controllers.telegram_sesion_controller import TelegramSesionController
from app.models.user import User
from app.models.database import db
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Crear blueprint para rutas de Telegram
telegram_bp = Blueprint('telegram', __name__)


# ============================================================
# WEBHOOK PARA N8N/TELEGRAM
# ============================================================

@telegram_bp.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """
    Webhook para recibir mensajes de Telegram vía N8N
    
    Body JSON (ejemplo de lo que N8N enviará):
    {
        "telegram_id": 123456789,
        "message": "Texto del mensaje",
        "first_name": "Juan",
        "username": "juanperez"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos JSON requeridos'
            }), 400
        
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({
                'success': False,
                'message': 'telegram_id es requerido'
            }), 400
        
        # Buscar o crear usuario
        user = User.get_by_telegram_id(telegram_id)
        
        if not user:
            # Auto-registrar usuario desde Telegram
            user = User.create_user(
                telegram_id=telegram_id,
                nombre=data.get('first_name')
            )
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"Usuario auto-registrado desde Telegram: {telegram_id}")
        
        # Actualizar última conexión
        user.update_last_connection()
        
        return jsonify({
            'success': True,
            'message': 'Webhook procesado',
            'user': user.to_json_safe(),
            'new_user': user.fecha_registro == user.ultima_conexion
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error en webhook de Telegram: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error procesando webhook'
        }), 500


# ============================================================
# TELEGRAM SESIONES (Webhook / Bot)
# ============================================================

@telegram_bp.route('/telegram/sesion', methods=['POST'])
def get_or_create_sesion():
    """
    Obtener o crear sesión activa (UPSERT lógico)
    
    Body JSON:
    {
        "telegram_id": 123456789  // REQUERIDO
    }
    
    Response:
    {
        "success": true,
        "message": "Sesión obtenida/creada exitosamente",
        "data": {...}
    }
    """
    return TelegramSesionController.get_or_create_sesion()


@telegram_bp.route('/telegram/sesion/estado', methods=['PUT'])
def update_estado():
    """
    Actualizar estado de conversación
    
    Body JSON:
    {
        "telegram_id": 123456789,  // REQUERIDO
        "estado_conversacion": "esperando_presupuesto"  // REQUERIDO
    }
    
    Response:
    {
        "success": true,
        "message": "Estado actualizado exitosamente",
        "data": {...}
    }
    """
    return TelegramSesionController.update_estado()


@telegram_bp.route('/telegram/sesion/contexto', methods=['PUT'])
def update_contexto():
    """
    Actualizar contexto conversacional (JSONB)
    
    Body JSON:
    {
        "telegram_id": 123456789,  // REQUERIDO
        "contexto": {              // REQUERIDO
            "paso": 2,
            "categoria": "verduras"
        }
    }
    
    Response:
    {
        "success": true,
        "message": "Contexto actualizado exitosamente",
        "data": {...}
    }
    """
    return TelegramSesionController.update_contexto()


@telegram_bp.route('/telegram/sesion', methods=['DELETE'])
def clear_sesion():
    """
    Limpiar sesión (reset conversacional)
    
    Body JSON:
    {
        "telegram_id": 123456789  // REQUERIDO
    }
    
    Response:
    {
        "success": true,
        "message": "Sesión limpiada exitosamente",
        "data": {...}
    }
    """
    return TelegramSesionController.clear_sesion()



@telegram_bp.route('/telegram/sesion/<int:telegram_id>', methods=['GET'])
def get_sesion_by_telegram_id(telegram_id):
    return TelegramSesionController.get_sesion_by_telegram_id(telegram_id)
