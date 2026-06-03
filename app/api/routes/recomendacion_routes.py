"""
Rutas del módulo de recomendación de productos — NutriChat
"""
from flask import Blueprint
from app.api.controllers.recomendacion_controller import RecomendacionController

recomendacion_bp = Blueprint('recomendacion', __name__)

# ─────────────────────────────────────────────────────────────────────────────
# GET /api/productos/recomendacion
#   ?usuario_id=<uuid>        ← opción A
#   ?telegram_id=<int>        ← opción B (usada por n8n/bot de Telegram)
#   &presupuesto=<float>      ← opcional, sobreescribe el del perfil
# ─────────────────────────────────────────────────────────────────────────────
@recomendacion_bp.route('/productos/recomendacion', methods=['GET'])
def get_recomendacion():
    """
    Endpoint de recomendación personalizada de productos.
    Sin autenticación JWT para facilitar consumo desde n8n.
    """
    return RecomendacionController.get_recomendacion()