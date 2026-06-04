"""
Servicio de Recomendación para NutriChat
Algoritmo determinista: scoring lineal + selector voraz con diversidad de grupos
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import func

from app.models.database import db
from app.models.productos import Producto, ProductoNutricion, ProductoSnapshot, Categoria
from app.models.user import User # Asegúrate de que este modelo exista

logger = logging.getLogger(__name__)

# ==================== CONSTANTES ====================

# Mapeo completo de categorías reales (nombre exacto o subcadena) a grupo nutricional
# Basado en las categorías insertadas en tu DB
GRUPO_POR_CATEGORIA = {
    # -------------------- Lácteos (ID 1) --------------------
    'Lácteos':           'lacteos_alternativas',
    'Leches':            'lacteos_alternativas',
    'Quesos':            'lacteos_alternativas',
    'Yogures':           'lacteos_alternativas',
    'Otros lácteos':     'lacteos_alternativas',
    'Bebidas vegetales': 'lacteos_alternativas',  # alternativa a lácteos
    # -------------------- Carnes frescas y congeladas --------------------
    'Carnes':            'proteinas_frescas',
    'Carnes frescas':    'proteinas_frescas',
    'Carne de res y cerdo (congelado)': 'proteinas_frescas',
    'Pollo congelado':   'proteinas_frescas',
    'Pescado y mariscos':'proteinas_frescas',
    # -------------------- Huevos --------------------
    'Huevos':            'proteinas_frescas',
    # -------------------- Embutidos y preparados --------------------
    'Carnes frías':      'proteinas_preparados',
    'Platos preparados': 'proteinas_preparados',
    'Comidas listas congeladas': 'proteinas_preparados',
    'Pre-fritos y pasabocas': 'proteinas_preparados',
    'Enlatados y envasados': 'proteinas_preparados',
    'Caldos, sopas y bases': 'proteinas_preparados',
    # -------------------- Frutas y verduras --------------------
    'Frutas y Verduras': 'frutas_verduras',
    'Frutas y verduras congeladas': 'frutas_verduras',
    'Verduras y frutas frescas': 'frutas_verduras',
    # -------------------- Granos y cereales --------------------
    'Granos y Cereales': 'cereales_tuberculos',
    'Granos, azúcar y panela': 'cereales_tuberculos',
    'Harinas y premezclas': 'cereales_tuberculos',
    'Pasta':              'cereales_tuberculos',
    'Cereales y avenas':  'cereales_tuberculos',
    'Arepas':             'cereales_tuberculos',
    # -------------------- Aceites y grasas --------------------
    'Margarinas y aceites': 'grasas_aliños',
    'Salsas y aderezos':    'grasas_aliños',
    'Condimentos':          'grasas_aliños',
    # -------------------- Bebidas --------------------
    'Bebidas':            'bebidas',
    'Aguas':              'bebidas',
    'Gaseosas e isotónicas': 'bebidas',
    'Jugos, refrescos y néctares': 'bebidas',
    'Infusiones, té y café': 'bebidas',
    'Modificadores':      'bebidas',
    # -------------------- Snacks y dulces --------------------
    'Snacks':             'aperitivos',
    'Snacks y pasabocas': 'aperitivos',
    'Helados y postres congelados': 'aperitivos',
    'Postres listos':     'aperitivos',
    # -------------------- Alimentos sin clasificar (genéricos) --------------------
    'Alimentos y Despensa': 'otros',
    'Congelados':         'otros',   # se refina según subcategoría, pero si no hay match, cae en otros
    'Otros':              'otros',
    # -------------------- No alimentos (se excluyen) --------------------
    'Limpieza':           'no_alimento',
    'Aseo Hogar':         'no_alimento',
    'Aseo y Cuidado Personal': 'no_alimento',
    'Accesorios de limpieza': 'no_alimento',
    'Cuidado de la ropa': 'no_alimento',
    'Cuidado de superficies': 'no_alimento',
    'Cuidado del aire':   'no_alimento',
    'Desechables hogar':  'no_alimento',
    'Pilas y bombillos':  'no_alimento',
    'Cuidado capilar':    'no_alimento',
    'Cuidado corporal':   'no_alimento',
    'Cuidado oral':       'no_alimento',
    'Jabonería':          'no_alimento',
    'Desodorantes':       'no_alimento',
    'Papel higiénico':    'no_alimento',
    'Protección femenina':'no_alimento',
    'Afeitado':           'no_alimento',
    'Botiquín':           'no_alimento',
    'Cosmética y maquillaje': 'no_alimento',
    'Cuidado solar':      'no_alimento',
}

# Grupos que DEBEN tener al menos un representante en la lista final
# (solo alimentos, excluyendo 'no_alimento' y 'otros')
GRUPOS_OBLIGATORIOS = [
    'frutas_verduras',
    'cereales_tuberculos',
    'proteinas_frescas',
    'lacteos_alternativas',
]

# Límites nutricionales por condición (clave: nombre de condición → restricciones)
LIMITES_POR_CONDICION = {
    'diabetes':       {'max_azucares_g': 5.0,  'max_ig': 55.0},
    'hipertension':   {'max_sodio_mg': 200.0},
    'hipertencion':   {'max_sodio_mg': 200.0},   # posible typo
    'obesidad':       {'max_calorias_kcal': 200.0, 'max_grasas_saturadas_g': 3.0},
    'colesterol alto':{'max_grasas_saturadas_g': 2.0, 'max_colesterol_mg': 50.0},
    'celiaquia':      {},   # manejo vía atributos o categorías
}

MAX_PRODUCTOS_LISTA = 12
MAX_PRECIO_RATIO    = 0.40   # un producto no puede costar más del 40% del presupuesto total


# ==================== FUNCIÓN PRINCIPAL ====================

def generar_recomendacion(
    usuario_id: str,
    presupuesto_override: Optional[float] = None
) -> Dict[str, Any]:
    """
    Genera una lista de compras personalizada para el usuario.

    Args:
        usuario_id: UUID del usuario (string)
        presupuesto_override: Si se pasa, reemplaza el presupuesto del perfil.
    Returns:
        Dict con productos seleccionados, presupuesto usado, etc.
    """
    advertencias: List[str] = []

    # ── 1. Cargar usuario y perfil ──────────────────────────────────────────
    usuario = _cargar_usuario(usuario_id)
    if usuario is None:
        raise ValueError(f"Usuario no encontrado: {usuario_id}")

    # Extraer datos del perfil JSON
    perfil = usuario.perfil_json or {}
    preferencias = perfil.get('nutritional_preferences', {})
    objetivo     = preferencias.get('objetivo_nutricional', 'mantener')
    condiciones  = preferencias.get('condiciones', [])
    alergias     = preferencias.get('alergias', [])
    categorias_excluidas = preferencias.get('categorias_excluidas', [])

    # Presupuesto: override > perfil_json.weekly > perfil_json.monthly/4 > default
    if presupuesto_override is not None:
        presupuesto = float(presupuesto_override)
    elif perfil.get('budget_weekly') is not None:
        presupuesto = float(perfil['budget_weekly'])
    elif perfil.get('budget_monthly') is not None:
        presupuesto = float(perfil['budget_monthly']) / 4.0
    else:
        presupuesto = 100_000.0
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

    # JOIN: producto + último snapshot + nutrición + categoría
    rows = (
        db.session.query(Producto, ProductoSnapshot, ProductoNutricion, Categoria)
        .join(sub, Producto.producto_id == sub.c.producto_id)
        .join(ProductoSnapshot,
              (ProductoSnapshot.producto_id == sub.c.producto_id) &
              (ProductoSnapshot.fecha_captura == sub.c.max_fecha))
        .outerjoin(ProductoNutricion,
                   Producto.producto_id == ProductoNutricion.producto_id)
        .outerjoin(Categoria, Producto.categoria_id == Categoria.categoria_id)
        .filter(Producto.categoria_id.isnot(None))
        .all()
    )

    resultado = []
    for producto, snapshot, nutricion, categoria in rows:
        entry = {
            'producto_id':   str(producto.producto_id),
            'nombre':        producto.nombre,
            'marca':         producto.marca,
            'categoria_id':  producto.categoria_id,
            'categoria_nombre': categoria.nombre if categoria else None,
            'url_imagen':    producto.url_imagen,
            'url_producto':  producto.url_producto,
            'precio':        float(snapshot.precio) if snapshot.precio else None,
            'unidad_medida': snapshot.unidad_medida,
            'fuente':        snapshot.fuente,
            'atributos':     snapshot.atributos_json or {},
            'impacto_ambiental': snapshot.impacto_ambiental or {},
            'nutricion':     _nutricion_a_dict(nutricion),
            'grupo':         _inferir_grupo(categoria.nombre if categoria else ''),
        }
        resultado.append(entry)

    return resultado


def _nutricion_a_dict(nutricion: Optional[ProductoNutricion]) -> Dict[str, Any]:
    """Convierte el objeto nutricion a dict con floats (o None)."""
    if nutricion is None:
        return {}
    return {
        'calorias_kcal':      float(nutricion.calorias_kcal)      if nutricion.calorias_kcal      is not None else None,
        'proteinas_g':        float(nutricion.proteinas_g)        if nutricion.proteinas_g        is not None else None,
        'grasas_totales_g':   float(nutricion.grasas_totales_g)   if nutricion.grasas_totales_g   is not None else None,
        'grasas_saturadas_g': float(nutricion.grasas_saturadas_g) if nutricion.grasas_saturadas_g is not None else None,
        'carbohidratos_g':    float(nutricion.carbohidratos_g)    if nutricion.carbohidratos_g    is not None else None,
        'azucares_g':         float(nutricion.azucares_g)         if nutricion.azucares_g         is not None else None,
        'fibra_g':            float(nutricion.fibra_g)            if nutricion.fibra_g            is not None else None,
        'sodio_mg':           float(nutricion.sodio_mg)           if nutricion.sodio_mg           is not None else None,
        'colesterol_mg':      float(nutricion.colesterol_mg)      if nutricion.colesterol_mg      is not None else None,
        'ig':                 float(nutricion.ig)                 if nutricion.ig                 is not None else None,
    }


def _inferir_grupo(categoria_nombre: Optional[str]) -> str:
    """Mapea el nombre de la categoría a un grupo nutricional."""
    if not categoria_nombre:
        return 'otros'
    # Primero, coincidencia exacta
    if categoria_nombre in GRUPO_POR_CATEGORIA:
        return GRUPO_POR_CATEGORIA[categoria_nombre]
    # Luego, coincidencia por subcadena (insensible a mayúsculas)
    cat_lower = categoria_nombre.lower()
    for key, grupo in GRUPO_POR_CATEGORIA.items():
        if key.lower() in cat_lower:
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

        # ── Filtro 3: Categorías excluidas explícitamente ────────────────
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
            "Los filtros eliminaron todos los productos. Se relaja el filtro de precio máximo."
        )
        # Relajar: solo filtrar los sin precio
        filtrados = [p for p in candidatos if p.get('precio') and p['precio'] > 0]

    return filtrados


def _viola_condicion(prod: Dict, condiciones: List[str]) -> bool:
    """Retorna True si el producto supera algún límite nutricional de las condiciones."""
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
    """Calcula un score 0-1 para el producto según afinidad nutricional, ahorro, sostenibilidad y completitud."""
    nutri  = prod.get('nutricion', {}) or {}
    precio = prod.get('precio', 0) or 0

    azucar    = nutri.get('azucares_g')         or 0.0
    fibra     = nutri.get('fibra_g')            or 0.0
    proteinas = nutri.get('proteinas_g')        or 0.0
    grasas_s  = nutri.get('grasas_saturadas_g') or 0.0
    calorias  = nutri.get('calorias_kcal')      or 0.0
    tiene_datos_nutri = bool(nutri)

    # Afinidad nutricional
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
    elif objetivo in ('diabetes', 'bajo_azucar'):
        nut_score = (
            0.40 * (1.0 - min(1.0, azucar / 5.0))  +
            0.30 * min(1.0, fibra          / 8.0)   +
            0.30 * (1.0 - min(1.0, grasas_s / 5.0))
        )
    else:   # mantener
        nut_score = (
            0.25 * min(1.0, fibra     /  5.0) +
            0.25 * min(1.0, proteinas / 15.0) +
            0.25 * (1.0 - min(1.0, azucar   / 10.0)) +
            0.25 * (1.0 - min(1.0, grasas_s /  5.0))
        )

    # Ahorro
    if presupuesto > 0:
        ahorro = 1.0 - min(1.0, precio / (presupuesto * MAX_PRECIO_RATIO))
    else:
        ahorro = 0.5

    # Sostenibilidad
    impacto = prod.get('impacto_ambiental', {}) or {}
    atribs  = prod.get('atributos', {})         or {}
    eco_score = 0.5
    if atribs.get('empaque_reciclable') or impacto.get('empaque_reciclable'):
        eco_score = 1.0
    elif impacto.get('huella_carbono_kg'):
        eco_score = 1.0 - min(1.0, float(impacto['huella_carbono_kg']) / 5.0)

    # Completitud
    completitud = 1.0 if tiene_datos_nutri else 0.3

    # Pesos por objetivo
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
    Construye la lista final de compras con diversidad garantizada.
    """
    seleccionados: List[Dict] = []
    presupuesto_restante = presupuesto

    # Agrupar candidatos por grupo nutricional, ordenados por score descendente
    grupos: Dict[str, List[Dict]] = {}
    for prod in sorted(candidatos, key=lambda x: x['score'], reverse=True):
        g = prod.get('grupo', 'otros')
        grupos.setdefault(g, []).append(prod)

    ids_seleccionados = set()

    # Pasada 1: un representante de cada grupo obligatorio
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
                    f"No se pudo incluir un producto del grupo '{grupo}' dentro del presupuesto."
                )
            else:
                advertencias.append(
                    f"No hay productos disponibles para el grupo '{grupo}'."
                )

    # Pasada 2: relleno con los mejores restantes
    todos_restantes = sorted(
        [p for p in candidatos if p['producto_id'] not in ids_seleccionados],
        key=lambda x: x['score'],
        reverse=True
    )

    for p in todos_restantes:
        if len(seleccionados) >= MAX_PRODUCTOS_LISTA or presupuesto_restante <= 0:
            break
        precio = p.get('precio', 0) or 0
        if precio <= presupuesto_restante:
            seleccionados.append(_enriquecer_para_respuesta(p))
            ids_seleccionados.add(p['producto_id'])
            presupuesto_restante -= precio

    seleccionados.sort(key=lambda x: x['score'], reverse=True)
    return seleccionados


def _enriquecer_para_respuesta(prod: Dict) -> Dict:
    """Prepara el dict final de cada producto para la respuesta JSON."""
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