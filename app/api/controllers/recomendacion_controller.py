"""
Controlador para el endpoint de recomendación de productos en NutriChat
"""
from flask import request, jsonify
import logging

from app.models.usuarios import User
from app.services.recomendacion_service import generar_recomendacion

logger = logging.getLogger(__name__)


class RecomendacionController:

    @staticmethod
    def get_recomendacion():
        """
        Genera una lista de compras personalizada para el usuario.

        Consumido principalmente por n8n.

        Query params:
        - usuario_id  : UUID del usuario  (REQUERIDO si no se usa telegram_id)
        - telegram_id : Telegram ID       (REQUERIDO si no se usa usuario_id)
        - presupuesto : float en COP      (OPCIONAL — sobreescribe el del perfil)

        Ejemplos de llamada desde n8n:
          GET /api/productos/recomendacion?telegram_id=123456789&presupuesto=80000
          GET /api/productos/recomendacion?usuario_id=<uuid>&presupuesto=80000

        Response 200:
        {
            "success": true,
            "data": {
                "productos": [...],
                "presupuesto_usado": 65200.0,
                "presupuesto_total": 80000.0,
                "objetivo": "mantener",
                "total_candidatos": 142,
                "advertencias": []
            },
            "meta": {
                "usuario_id": "...",
                "telegram_id": 123456789
            }
        }
        """
        try:
            # ── Resolver usuario ────────────────────────────────────────────
            usuario_id_param  = request.args.get('usuario_id')
            telegram_id_param = request.args.get('telegram_id')
            presupuesto_param = request.args.get('presupuesto')

            if not usuario_id_param and not telegram_id_param:
                return jsonify({
                    'success': False,
                    'message': 'Se requiere usuario_id o telegram_id como query parameter'
                }), 400

            usuario_id_resuelto = usuario_id_param
            telegram_id_resuelto = None

            if not usuario_id_resuelto and telegram_id_param:
                try:
                    tid = int(telegram_id_param)
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': 'telegram_id debe ser un número entero'
                    }), 400

                usuario = User.get_by_telegram_id(tid)   # Asegúrate de que este método exista en tu modelo User
                if not usuario:
                    return jsonify({
                        'success': False,
                        'message': f'No se encontró usuario con telegram_id={telegram_id_param}'
                    }), 404

                usuario_id_resuelto  = str(usuario.usuario_id)
                telegram_id_resuelto = tid

            # Validar presupuesto override si se pasó
            presupuesto_override = None
            if presupuesto_param is not None:
                try:
                    presupuesto_override = float(presupuesto_param)
                    if presupuesto_override <= 0:
                        raise ValueError()
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': 'presupuesto debe ser un número mayor a 0'
                    }), 400

            # ── Ejecutar algoritmo ──────────────────────────────────────────
            resultado = generar_recomendacion(
                usuario_id=usuario_id_resuelto,
                presupuesto_override=presupuesto_override,
            )

            logger.info(
                f"Recomendación generada — usuario={usuario_id_resuelto} | "
                f"productos={len(resultado['productos'])} | "
                f"presupuesto_usado={resultado['presupuesto_usado']}"
            )

            return jsonify({
                'success': True,
                'data': resultado,
                'meta': {
                    'usuario_id':   usuario_id_resuelto,
                    'telegram_id':  telegram_id_resuelto or telegram_id_param,
                }
            }), 200

        except ValueError as e:
            logger.warning(f"Error de validación en recomendación: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400

        except Exception as e:
            logger.error(f"Error inesperado en recomendación: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500