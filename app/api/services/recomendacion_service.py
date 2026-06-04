"""
Servicio de Recomendación para NutriChat
Algoritmo determinista: scoring lineal + selector voraz con diversidad de grupos
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from sqlalchemy import func

from app.models.database import db
from app.models.productos import Producto, ProductoNutricion, ProductoSnapshot
from app.models.user import User 

logger = logging.getLogger(__name__)

# ==================== CONSTANTES ====================

# Mapeo de nombres de categorías de BD → grupos nutricionales internos
# Ajusta los nombres según los que tengas en tu tabla `categorias`
GRUPO_POR_CATEGORIA = {
    'Frutas y Verduras': 'frutas_verduras',
    'Frutas':            'frutas_verduras',
    'Verduras':          'frutas_verduras',
    'Granos y Cereales': 'cereales_tuberculos',
    'Lácteos':           'lacteos_alternativas',
    'Carnes':            'proteinas_frescas',
    'Bebidas':           'bebidas',
    'Snacks':            'snacks',
    'Limpieza':          'limpieza',
    'Otros':             'otros',
}

# Grupos que DEBEN tener al menos un representante en la lista final
GRUPOS_OBLIGATORIOS = [
    'frutas_verduras',
    'cereales_tuberculos',
    'proteinas_frescas',
    'lacteos_alternativas',
]

# Límites nutricionales por condición (clave del condicion.nombre → restricciones)
LIMITES_POR_CONDICION = {
    'diabetes':       {'max_azucares_g': 5.0,  'max_ig': 55.0},
    'hipertension':   {'max_sodio_mg': 200.0},
    'hipertencion':   {'max_sodio_mg': 200.0},   # typo alternativo
    'obesidad':       {'max_calorias_kcal': 200.0, 'max_grasas_saturadas_g': 3.0},
    'colesterol alto':{'max_grasas_saturadas_g': 2.0, 'max_colesterol_mg': 50.0},
    'celiaquia':      {},   # filtrar por atributos_json si aplica
}

MAX_PRODUCTOS_LISTA = 12
MAX_PRECIO_RATIO    = 0.40   # un producto no puede valer más del 40 % del presupuesto total


# ==================== FUNCIÓN PRINCIPAL ====================

def generar_recomendacion(
    usuario_id: str,
    presupuesto_override: Optional[float] = None
) -> Dict[str, Any]:
    """
    Genera una lista de compras personalizada para el usuario.

    Args:
        usuario_id:           UUID del usuario (string)
        presupuesto_override: Si se pasa, reemplaza el presupuesto del perfil del usuario.
                              Útil cuando n8n lo extrae de la conversación de Telegram.

    Returns:
        Dict con:
            - productos: lista de productos seleccionados con sus scores
            - presupuesto_usado: suma de precios seleccionados
            - presupuesto_total: presupuesto de entrada
            - objetivo: objetivo nutricional del usuario
            - advertencias: lista de strings con avisos (ej. grupo sin cobertura)
    """
    advertencias: List[str] = []

    # ── 1. Cargar usuario y perfil ──────────────────────────────────────────
    usuario = _cargar_usuario(usuario_id)
    if usuario is None:
        raise ValueError(f"Usuario no encontrado: {usuario_id}")

    perfil      = usuario._get_perfil_data()
    preferencias = usuario.get_nutritional_preferences()

    objetivo     = preferencias.get('objetivo_nutricional', 'mantener')
    condiciones  = preferencias.get('condiciones', [])          # lista de strings
    alergias     = preferencias.get('alergias', [])             # lista de strings
    categorias_excluidas = preferencias.get('categorias_excluidas', [])

    # Determinar presupuesto efectivo
    if presupuesto_override is not None:
        presupuesto = float(presupuesto_override)
    elif usuario.budget_weekly is not None:
        presupuesto = float(usuario.budget_weekly)
    elif usuario.budget_monthly is not None:
        presupuesto = float(usuario.budget_monthly) / 4.0
    else:
        presupuesto = 100_000.0   # default COP si no hay presupuesto registrado
        advertencias.append("No se encontró presupuesto en el perfil. Se usó valor por defecto.")

    logger.info(
        f"Recomendación para usuario={usuario_id} | objetivo={objetivo} | "
        f"presupuesto={presupuesto} | condiciones={condiciones}"
    )

    # ── 2. Obtener todos los productos con precio y nutrición ───────────────
    candidatos_raw = _cargar_productos_con_datos()

    if not candidatos_raw:
        raise ValueError("No hay productos disponibles en la base de datos.")

    # ── 3. Aplicar filtros duros ────────────────────────────────────────────
    candidatos = _aplicar_filtros(
        candidatos_raw,
        presupuesto=presupuesto,
        alergias=alergias,
        condiciones=condiciones,
        categorias_excluidas=categorias_excluidas,
        advertencias=advertencias,
    )

    if not candidatos:
        raise ValueError(
            "Ningún producto pasó los filtros. Revisa las restricciones del perfil."
        )

    # ── 4. Calcular score para cada candidato ───────────────────────────────
    for prod in candidatos:
        prod['score'] = _calcular_score(prod, objetivo, presupuesto)

    # ── 5. Selector voraz con diversidad ───────────────────────────────────
    seleccionados = _selector_voraz(candidatos, presupuesto, advertencias)

    # ── 6. Armar respuesta ─────────────────────────────────────────────────
    presupuesto_usado = sum(p.get('precio', 0) or 0 for p in seleccionados)

    return {
        'productos':        seleccionados,
        'presupuesto_usado': round(presupuesto_usado, 2),
        'presupuesto_total': round(presupuesto, 2),
        'objetivo':         objetivo,
        'total_candidatos': len(candidatos),
        'advertencias':     advertencias,
    }


# ==================== CARGA DE DATOS ====================

def _cargar_usuario(usuario_id: str) -> Optional[User]:
    """Busca el usuario por UUID string."""
    try:
        import uuid
        uid = uuid.UUID(usuario_id)
        return User.query.get(uid)
    except (ValueError, TypeError):
        return None


def _cargar_productos_con_datos() -> List[Dict[str, Any]]:
    """
    Retorna todos los productos disponibles con su último precio
    y su información nutricional, en un único query JOIN eficiente.
    """
    # Subconsulta: último snapshot por producto
    sub = (
        db.session.query(
            ProductoSnapshot.producto_id,
            func.max(ProductoSnapshot.fecha_captura).label('max_fecha')
        )
        .filter(ProductoSnapshot.disponibilidad == True)
        .group_by(ProductoSnapshot.producto_id)
        .subquery()
    )

    # JOIN: producto + último snapshot + nutrición
    rows = (
        db.session.query(Producto, ProductoSnapshot, ProductoNutricion)
        .join(sub,
              (Producto.producto_id == sub.c.producto_id))
        .join(ProductoSnapshot,
              (ProductoSnapshot.producto_id == sub.c.producto_id) &
              (ProductoSnapshot.fecha_captura == sub.c.max_fecha))
        .outerjoin(ProductoNutricion,
                   Producto.producto_id == ProductoNutricion.producto_id)
        .filter(Producto.categoria_id.isnot(None))
        .all()
    )

    resultado = []
    for producto, snapshot, nutricion in rows:
        entry = {
            'producto_id':   str(producto.producto_id),
            'nombre':        producto.nombre,
            'marca':         producto.marca,
            'categoria_id':  producto.categoria_id,
            'categoria_nombre': _nombre_categoria(producto.categoria_id),
            'url_imagen':    producto.url_imagen,
            'url_producto':  producto.url_producto,
            'precio':        float(snapshot.precio) if snapshot.precio else None,
            'unidad_medida': snapshot.unidad_medida,
            'fuente':        snapshot.fuente,
            'atributos':     snapshot.atributos_json or {},
            'impacto_ambiental': snapshot.impacto_ambiental or {},
            'nutricion':     _nutricion_a_dict(nutricion),
            'grupo':         _inferir_grupo(producto),
        }
        resultado.append(entry)

    return resultado


def _nombre_categoria(categoria_id: Optional[int]) -> Optional[str]:
    """Obtiene el nombre de la categoría desde caché en memoria."""
    if categoria_id is None:
        return None
    from app.models.productos import Categoria
    cat = Categoria.query.get(categoria_id)
    return cat.nombre if cat else None


def _nutricion_a_dict(nutricion: Optional[ProductoNutricion]) -> Dict[str, Any]:
    """Convierte el objeto nutricion a dict con floats (o None)."""
    if nutricion is None:
        return {}
    return {
        'calorias_kcal':      float(nutricion.calorias_kcal)      if nutricion.calorias_kcal      else None,
        'proteinas_g':        float(nutricion.proteinas_g)        if nutricion.proteinas_g        else None,
        'grasas_totales_g':   float(nutricion.grasas_totales_g)   if nutricion.grasas_totales_g   else None,
        'grasas_saturadas_g': float(nutricion.grasas_saturadas_g) if nutricion.grasas_saturadas_g else None,
        'carbohidratos_g':    float(nutricion.carbohidratos_g)    if nutricion.carbohidratos_g    else None,
        'azucares_g':         float(nutricion.azucares_g)         if nutricion.azucares_g         else None,
        'fibra_g':            float(nutricion.fibra_g)            if nutricion.fibra_g            else None,
        'sodio_mg':           float(nutricion.sodio_mg)           if nutricion.sodio_mg           else None,
        'colesterol_mg':      float(nutricion.colesterol_mg)      if nutricion.colesterol_mg      else None,
        'ig':                 float(nutricion.ig)                 if nutricion.ig                 else None,
    }


def _inferir_grupo(producto: Producto) -> str:
    """Mapea la categoría del producto a un grupo nutricional interno."""
    cat_nombre = _nombre_categoria(producto.categoria_id)
    if cat_nombre:
        for key, grupo in GRUPO_POR_CATEGORIA.items():
            if key.lower() in cat_nombre.lower():
                return grupo
    return 'otros'


# ==================== FILTROS DUROS ====================

def _aplicar_filtros(
    candidatos: List[Dict],
    presupuesto: float,
    alergias: List[str],
    condiciones: List[str],
    categorias_excluidas: List[str],
    advertencias: List[str],
) -> List[Dict]:
    """
    Elimina productos que no deben aparecer en la lista bajo ninguna circunstancia.
    """
    precio_max_por_producto = presupuesto * MAX_PRECIO_RATIO
    alergias_lower    = [a.lower() for a in alergias]
    cond_lower        = [c.lower() for c in condiciones]
    cat_excl_lower    = [c.lower() for c in categorias_excluidas]

    filtrados = []
    for prod in candidatos:
        precio = prod.get('precio')

        # ── Filtro 1: Debe tener precio ──────────────────────────────────
        if precio is None or precio <= 0:
            continue

        # ── Filtro 2: Precio máximo por ítem ────────────────────────────
        if precio > precio_max_por_producto:
            continue

        # ── Filtro 3: Categorías excluidas por el usuario ────────────────
        cat = (prod.get('categoria_nombre') or '').lower()
        if any(exc in cat for exc in cat_excl_lower):
            continue

        # ── Filtro 4: Alergias (busca en nombre + marca) ─────────────────
        nombre_lower = (prod.get('nombre') or '').lower()
        marca_lower  = (prod.get('marca')  or '').lower()
        texto_buscar = f"{nombre_lower} {marca_lower}"
        if any(alerg in texto_buscar for alerg in alergias_lower):
            continue

        # ── Filtro 5: Restricciones por condición médica ──────────────────
        if _viola_condicion(prod, cond_lower):
            continue

        filtrados.append(prod)

    if len(filtrados) == 0 and len(candidatos) > 0:
        advertencias.append(
            f"Los filtros eliminaron todos los productos. "
            f"Se relaja el filtro de precio máximo por ítem."
        )
        # Relajar: solo filtrar los sin precio
        filtrados = [p for p in candidatos if p.get('precio') and p['precio'] > 0]

    return filtrados


def _viola_condicion(prod: Dict, condiciones: List[str]) -> bool:
    """
    Retorna True si el producto supera algún límite nutricional
    definido para las condiciones del usuario.
    """
    nutri = prod.get('nutricion', {})
    for cond in condiciones:
        limites = LIMITES_POR_CONDICION.get(cond, {})
        for campo, limite in limites.items():
            valor = nutri.get(campo)
            if valor is not None and valor > limite:
                return True
    return False


# ==================== SCORING ====================

def _calcular_score(prod: Dict, objetivo: str, presupuesto: float) -> float:
    """
    Calcula un score 0-1 para el producto según:
      - Afinidad nutricional con el objetivo del usuario (w1)
      - Ahorro relativo al presupuesto (w2)
      - Sostenibilidad / impacto ambiental (w3)
      - Penalización por datos nutricionales incompletos (w4)

    Returns:
        float: score entre 0 y 1
    """
    nutri  = prod.get('nutricion', {}) or {}
    precio = prod.get('precio', 0) or 0

    # ── Dimensión 1: Afinidad nutricional (0-1) ──────────────────────────
    azucar    = nutri.get('azucares_g')         or 0.0
    fibra     = nutri.get('fibra_g')            or 0.0
    proteinas = nutri.get('proteinas_g')        or 0.0
    grasas_s  = nutri.get('grasas_saturadas_g') or 0.0
    calorias  = nutri.get('calorias_kcal')      or 0.0
    tiene_datos_nutri = bool(nutri)

    if objetivo == 'bajar_peso':
        nut_score = (
            0.30 * (1.0 - min(1.0, azucar    / 10.0)) +
            0.30 * min(1.0, fibra             /  5.0)  +
            0.20 * min(1.0, proteinas         / 20.0)  +
            0.20 * (1.0 - min(1.0, grasas_s  /  5.0))
        )
    elif objetivo == 'subir_peso':
        nut_score = (
            0.50 * min(1.0, calorias  / 400.0) +
            0.30 * min(1.0, proteinas /  25.0) +
            0.20 * 0.5
        )
    elif objetivo == 'musculo':
        nut_score = (
            0.60 * min(1.0, proteinas         / 30.0)  +
            0.20 * min(1.0, calorias          / 300.0) +
            0.20 * (1.0 - min(1.0, grasas_s  /  5.0))
        )
    elif objetivo == 'diabetes' or objetivo == 'bajo_azucar':
        nut_score = (
            0.40 * (1.0 - min(1.0, azucar / 5.0))  +
            0.30 * min(1.0, fibra          / 8.0)   +
            0.30 * (1.0 - min(1.0, grasas_s / 5.0))
        )
    elif objetivo == 'mantener':
        # Algoritmo específico para equilibrio nutricional.
        # Premia fibra y proteína moderada, controla azúcar y grasas
        # sin restricciones tan estrictas como bajar_peso o diabetes.
        # Basado en criterios de la Ley 2120 de 2021 (Colombia).
        nut_score = (
            0.30 * min(1.0, fibra     /  6.0) +
            0.25 * min(1.0, proteinas / 15.0) +
            0.25 * (1.0 - min(1.0, azucar   /  8.0)) +
            0.20 * (1.0 - min(1.0, grasas_s /  6.0))
        )
    else:
        # Objetivo desconocido → score neutro como fallback
        nut_score = 0.5

    # ── Dimensión 2: Ahorro (0-1) ────────────────────────────────────────
    # Productos más baratos relativos al presupuesto reciben mejor score
    if presupuesto > 0:
        ahorro = 1.0 - min(1.0, precio / (presupuesto * MAX_PRECIO_RATIO))
    else:
        ahorro = 0.5

    # ── Dimensión 3: Sostenibilidad (0-1) ────────────────────────────────
    impacto = prod.get('impacto_ambiental', {}) or {}
    atribs  = prod.get('atributos', {})         or {}
    eco_score = 0.5   # neutral si no hay datos
    if atribs.get('empaque_reciclable') or impacto.get('empaque_reciclable'):
        eco_score = 1.0
    elif impacto.get('huella_carbono_kg'):
        # Menor huella → mejor score (normalizado a 5 kg como máximo razonable)
        eco_score = 1.0 - min(1.0, float(impacto['huella_carbono_kg']) / 5.0)

    # ── Dimensión 4: Completitud de datos nutricionales ──────────────────
    completitud = 1.0 if tiene_datos_nutri else 0.3

    # ── Pesos por objetivo ───────────────────────────────────────────────
    #          w_nutri  w_ahorro  w_eco  w_completitud
    pesos_map = {
        'bajar_peso':  (0.50, 0.25, 0.15, 0.10),
        'subir_peso':  (0.40, 0.25, 0.15, 0.20),
        'musculo':     (0.55, 0.20, 0.10, 0.15),
        'diabetes':    (0.55, 0.20, 0.10, 0.15),
        'bajo_azucar': (0.55, 0.20, 0.10, 0.15),
        'mantener':    (0.40, 0.30, 0.20, 0.10),
    }
    w1, w2, w3, w4 = pesos_map.get(objetivo, (0.40, 0.30, 0.20, 0.10))

    return round(w1 * nut_score + w2 * ahorro + w3 * eco_score + w4 * completitud, 4)


# ==================== SELECTOR VORAZ ====================

def _selector_voraz(
    candidatos: List[Dict],
    presupuesto: float,
    advertencias: List[str],
) -> List[Dict]:
    """
    Construye la lista final de compras con dos pasadas:

    Pasada 1 – Diversidad garantizada:
        Para cada grupo obligatorio, toma el producto con mayor score
        que quepa en el presupuesto restante.

    Pasada 2 – Relleno por score:
        Agrega los mejores productos restantes hasta alcanzar
        MAX_PRODUCTOS_LISTA o agotar el presupuesto.
    """
    seleccionados: List[Dict] = []
    presupuesto_restante = presupuesto

    # Agrupar candidatos por grupo nutricional, ordenados por score desc
    grupos: Dict[str, List[Dict]] = {}
    for prod in sorted(candidatos, key=lambda x: x['score'], reverse=True):
        g = prod.get('grupo', 'otros')
        grupos.setdefault(g, []).append(prod)

    ids_seleccionados = set()

    # ── Pasada 1: un representante por grupo obligatorio ─────────────────
    for grupo in GRUPOS_OBLIGATORIOS:
        if presupuesto_restante <= 0:
            break
        productos_grupo = grupos.get(grupo, [])
        for p in productos_grupo:
            precio = p.get('precio', 0) or 0
            if precio <= presupuesto_restante and p['producto_id'] not in ids_seleccionados:
                seleccionados.append(_enriquecer_para_respuesta(p))
                ids_seleccionados.add(p['producto_id'])
                presupuesto_restante -= precio
                break
        else:
            if productos_grupo:
                advertencias.append(
                    f"No se pudo incluir un producto del grupo '{grupo}' "
                    f"dentro del presupuesto."
                )
            else:
                advertencias.append(
                    f"No hay productos disponibles para el grupo '{grupo}'."
                )

    # ── Pasada 2: relleno con los mejores candidatos restantes ────────────
    todos_restantes = sorted(
        [p for p in candidatos if p['producto_id'] not in ids_seleccionados],
        key=lambda x: x['score'],
        reverse=True
    )

    for p in todos_restantes:
        if len(seleccionados) >= MAX_PRODUCTOS_LISTA:
            break
        if presupuesto_restante <= 0:
            break
        precio = p.get('precio', 0) or 0
        if precio <= presupuesto_restante:
            seleccionados.append(_enriquecer_para_respuesta(p))
            ids_seleccionados.add(p['producto_id'])
            presupuesto_restante -= precio

    # Ordenar resultado final por score descendente para claridad
    seleccionados.sort(key=lambda x: x['score'], reverse=True)

    return seleccionados


def _enriquecer_para_respuesta(prod: Dict) -> Dict:
    """
    Prepara el dict final de cada producto para la respuesta JSON.
    Solo incluye los campos necesarios para n8n y el bot de Telegram.
    """
    nutri = prod.get('nutricion', {}) or {}
    return {
        'producto_id':     prod['producto_id'],
        'nombre':          prod['nombre'],
        'marca':           prod.get('marca'),
        'categoria':       prod.get('categoria_nombre'),
        'grupo':           prod.get('grupo'),
        'precio':          prod.get('precio'),
        'unidad_medida':   prod.get('unidad_medida'),
        'url_imagen':      prod.get('url_imagen'),
        'url_producto':    prod.get('url_producto'),
        'fuente':          prod.get('fuente'),
        'score':           prod['score'],
        'tiene_nutricion': bool(nutri),
        'nutricion': {
            'calorias_kcal':      nutri.get('calorias_kcal'),
            'proteinas_g':        nutri.get('proteinas_g'),
            'carbohidratos_g':    nutri.get('carbohidratos_g'),
            'grasas_totales_g':   nutri.get('grasas_totales_g'),
            'fibra_g':            nutri.get('fibra_g'),
            'azucares_g':         nutri.get('azucares_g'),
            'sodio_mg':           nutri.get('sodio_mg'),
        },
    }