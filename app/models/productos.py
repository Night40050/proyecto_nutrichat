"""
Modelos relacionados con Productos para NutriChat
Incluye: Categoria, Producto, ProductoNutricion, ProductoSnapshot
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import Column, Text, Integer, Boolean, DateTime, Numeric, BigInteger, ForeignKey
from sqlalchemy import UniqueConstraint, CheckConstraint, func
from sqlalchemy import JSON
from sqlalchemy.orm import validates, relationship

from .database import db
# Cambiar la importación para usar db_types si existe, o usar el GUID directamente
try:
    from app.db_types import GUID
except ImportError:
    from app.db_types import GUID
    from sqlalchemy.types import TypeDecorator, String
    
    class GUID(TypeDecorator):
        """
        UUID compatible con PostgreSQL y SQLite
        """
        impl = String(36)
        cache_ok = True

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(uuid.UUID(value))

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            return uuid.UUID(value)


# ==================== CATEGORIA ====================

class Categoria(db.Model):
    """
    Modelo de Categoria para PostgreSQL (Supabase)
    Representa una categoría de productos
    """

    __tablename__ = 'categorias'

    # Campos principales
    categoria_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(Text, nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_categoria(cls, nombre: str, descripcion: str = None) -> 'Categoria':
        """
        Crear una nueva categoría

        Args:
            nombre: Nombre de la categoría (requerido, único)
            descripcion: Descripción de la categoría

        Returns:
            Categoria: Instancia de la categoría creada

        Raises:
            ValueError: Si nombre no es válido
        """
        if not nombre or not nombre.strip():
            raise ValueError("nombre es requerido")

        categoria = cls(
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else None
        )

        return categoria

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> int:
        """Obtener ID de la categoría"""
        return self.categoria_id

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir categoría a diccionario"""
        return {
            'id': self.categoria_id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_nombre(cls, nombre: str) -> Optional['Categoria']:
        """Buscar categoría por nombre"""
        if not nombre:
            return None
        return cls.query.filter_by(nombre=nombre).first()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        return f"<Categoria categoria_id={self.categoria_id} - {self.nombre}>"

    def __str__(self) -> str:
        return self.nombre


# ==================== PRODUCTO ====================

class Producto(db.Model):
    """
    Modelo de Producto para PostgreSQL (Supabase)
    Representa un producto canónico del sistema
    """

    __tablename__ = 'productos'

    # Campos principales
    producto_id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Información básica
    nombre = Column(Text, nullable=False)
    marca = Column(Text, nullable=True)
    categoria_id = Column(Integer, ForeignKey('categorias.categoria_id'), nullable=True)
    descripcion = Column(Text, nullable=True)

    # URLs y referencias
    url_producto = Column(Text, nullable=True)
    url_imagen = Column(Text, nullable=True)
    codigo_fuente = Column(Text, nullable=True)
    producto_hash = Column(Text, nullable=True)

    # Fechas
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=True)

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_producto(cls, nombre: str, marca: str = None, categoria_id: int = None,
                        descripcion: str = None, **kwargs) -> 'Producto':
        """
        Crear un nuevo producto

        Args:
            nombre: Nombre del producto (requerido)
            marca: Marca del producto
            categoria_id: ID de la categoría
            descripcion: Descripción del producto
            **kwargs: Campos adicionales opcionales

        Returns:
            Producto: Instancia del producto creado

        Raises:
            ValueError: Si nombre no es válido
        """
        if not nombre or not nombre.strip():
            raise ValueError("nombre es requerido")

        producto = cls(
            nombre=nombre.strip(),
            marca=marca.strip() if marca else None,
            categoria_id=categoria_id,
            descripcion=descripcion.strip() if descripcion else None,
            **kwargs
        )

        return producto

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> uuid.UUID:
        """Obtener ID del producto"""
        return self.producto_id

    @property
    def created_at(self) -> datetime:
        """Obtener fecha de creación"""
        return self.creado_en

    @property
    def updated_at(self) -> Optional[datetime]:
        """Obtener fecha de actualización"""
        return self.actualizado_en

    def update_timestamp(self) -> None:
        """Actualizar timestamp de modificación"""
        self.actualizado_en = datetime.now(timezone.utc)

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir producto a diccionario"""
        return {
            'id': str(self.producto_id),
            'nombre': self.nombre,
            'marca': self.marca,
            'categoria_id': self.categoria_id,
            'descripcion': self.descripcion,
            'url_producto': self.url_producto,
            'url_imagen': self.url_imagen,
            'codigo_fuente': self.codigo_fuente,
            'producto_hash': self.producto_hash,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
            'actualizado_en': self.actualizado_en.isoformat() if self.actualizado_en else None,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_hash(cls, producto_hash: str) -> Optional['Producto']:
        """Buscar producto por hash"""
        if not producto_hash:
            return None
        return cls.query.filter_by(producto_hash=producto_hash).first()

    @classmethod
    def get_by_categoria(cls, categoria_id: int) -> list:
        """Buscar productos por categoría"""
        return cls.query.filter_by(categoria_id=categoria_id).all()

    @classmethod
    def get_by_nombre(cls, nombre: str) -> list:
        """Buscar productos por nombre (búsqueda parcial)"""
        if not nombre:
            return []
        return cls.query.filter(cls.nombre.ilike(f'%{nombre}%')).all()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        return f"<Producto producto_id={self.producto_id} - {self.nombre}>"

    def __str__(self) -> str:
        marca_str = f" ({self.marca})" if self.marca else ""
        return f"{self.nombre}{marca_str}"


# ==================== PRODUCTO NUTRICION ====================

class ProductoNutricion(db.Model):
    """
    Modelo de ProductoNutricion para PostgreSQL (Supabase)
    Representa la información nutricional de un producto
    """

    __tablename__ = 'producto_nutricion'

    __table_args__ = (
        CheckConstraint('calorias_kcal >= 0', name='ck_calorias_kcal'),
        CheckConstraint('proteinas_g >= 0', name='ck_proteinas_g'),
        CheckConstraint('grasas_totales_g >= 0', name='ck_grasas_totales_g'),
        CheckConstraint('grasas_saturadas_g >= 0', name='ck_grasas_saturadas_g'),
        CheckConstraint('carbohidratos_g >= 0', name='ck_carbohidratos_g'),
        CheckConstraint('azucares_g >= 0', name='ck_azucares_g'),
        CheckConstraint('fibra_g >= 0', name='ck_fibra_g'),
        CheckConstraint('sodio_mg >= 0', name='ck_sodio_mg'),
        CheckConstraint('colesterol_mg >= 0', name='ck_colesterol_mg'),
    )

    # Campos principales
    nutricion_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Relación con producto
    producto_id = Column(GUID, ForeignKey('productos.producto_id', ondelete='CASCADE'), nullable=False)

    # Información de porción
    porcion_g = Column(Numeric(8, 3), nullable=True)

    # Macronutrientes principales
    calorias_kcal = Column(Numeric(8, 2), nullable=True)
    proteinas_g = Column(Numeric(8, 3), nullable=True)
    grasas_totales_g = Column(Numeric(8, 3), nullable=True)
    grasas_saturadas_g = Column(Numeric(8, 3), nullable=True)
    carbohidratos_g = Column(Numeric(8, 3), nullable=True)
    azucares_g = Column(Numeric(8, 3), nullable=True)
    fibra_g = Column(Numeric(8, 3), nullable=True)

    # Minerales y otros
    sodio_mg = Column(Numeric(10, 2), nullable=True)
    colesterol_mg = Column(Numeric(10, 2), nullable=True)

    # Datos adicionales
    micronutrientes = Column(JSON, nullable=True)
    ig = Column(Numeric(5, 2), nullable=True)
    carga_glucemica = Column(Numeric(6, 2), nullable=True)
    fuente = Column(Text, nullable=True)

    # Fecha de registro
    fecha_registro = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # ==================== VALIDACIONES ====================

    @validates('calorias_kcal')
    def validate_calorias(self, key, calorias):
        """Validar que las calorías sean no negativas"""
        if calorias is not None and calorias < 0:
            raise ValueError("Las calorías no pueden ser negativas")
        return calorias

    @validates('proteinas_g')
    def validate_proteinas(self, key, proteinas):
        """Validar que las proteínas sean no negativas"""
        if proteinas is not None and proteinas < 0:
            raise ValueError("Las proteínas no pueden ser negativas")
        return proteinas

    @validates('grasas_totales_g')
    def validate_grasas_totales(self, key, grasas):
        """Validar que las grasas totales sean no negativas"""
        if grasas is not None and grasas < 0:
            raise ValueError("Las grasas totales no pueden ser negativas")
        return grasas

    @validates('grasas_saturadas_g')
    def validate_grasas_saturadas(self, key, grasas):
        """Validar que las grasas saturadas sean no negativas"""
        if grasas is not None and grasas < 0:
            raise ValueError("Las grasas saturadas no pueden ser negativas")
        return grasas

    @validates('carbohidratos_g')
    def validate_carbohidratos(self, key, carbohidratos):
        """Validar que los carbohidratos sean no negativos"""
        if carbohidratos is not None and carbohidratos < 0:
            raise ValueError("Los carbohidratos no pueden ser negativos")
        return carbohidratos

    @validates('azucares_g')
    def validate_azucares(self, key, azucares):
        """Validar que los azúcares sean no negativos"""
        if azucares is not None and azucares < 0:
            raise ValueError("Los azúcares no pueden ser negativos")
        return azucares

    @validates('fibra_g')
    def validate_fibra(self, key, fibra):
        """Validar que la fibra sea no negativa"""
        if fibra is not None and fibra < 0:
            raise ValueError("La fibra no puede ser negativa")
        return fibra

    @validates('sodio_mg')
    def validate_sodio(self, key, sodio):
        """Validar que el sodio sea no negativo"""
        if sodio is not None and sodio < 0:
            raise ValueError("El sodio no puede ser negativo")
        return sodio

    @validates('colesterol_mg')
    def validate_colesterol(self, key, colesterol):
        """Validar que el colesterol sea no negativo"""
        if colesterol is not None and colesterol < 0:
            raise ValueError("El colesterol no puede ser negativo")
        return colesterol

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_nutricion(cls, producto_id: uuid.UUID, calorias_kcal: Optional[Decimal] = None,
                        proteinas_g: Optional[Decimal] = None, **kwargs) -> 'ProductoNutricion':
        """
        Crear un nuevo registro de nutrición para un producto

        Args:
            producto_id: ID del producto (requerido)
            calorias_kcal: Calorías por porción
            proteinas_g: Proteínas en gramos
            **kwargs: Campos adicionales opcionales

        Returns:
            ProductoNutricion: Instancia del registro de nutrición creado

        Raises:
            ValueError: Si producto_id no es válido o valores negativos
        """
        if not producto_id:
            raise ValueError("producto_id es requerido")

        nutricion = cls(
            producto_id=producto_id,
            calorias_kcal=calorias_kcal,
            proteinas_g=proteinas_g,
            **kwargs
        )

        return nutricion

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> int:
        """Obtener ID del registro de nutrición"""
        return self.nutricion_id

    @property
    def registered_at(self) -> datetime:
        """Obtener fecha de registro"""
        return self.fecha_registro

    def get_micronutrientes(self) -> Dict[str, Any]:
        """Obtener micronutrientes"""
        return self.micronutrientes if self.micronutrientes else {}

    def set_micronutrientes(self, data: Dict[str, Any]) -> None:
        """Establecer micronutrientes"""
        self.micronutrientes = data

    def calcular_calorias_totales(self, porciones: Decimal = Decimal('1')) -> Optional[Decimal]:
        """
        Calcular calorías totales para múltiples porciones

        Args:
            porciones: Número de porciones

        Returns:
            Decimal: Calorías totales o None si no hay datos
        """
        if self.calorias_kcal:
            return self.calorias_kcal * porciones
        return None

    def calcular_proteinas_totales(self, porciones: Decimal = Decimal('1')) -> Optional[Decimal]:
        """
        Calcular proteínas totales para múltiples porciones

        Args:
            porciones: Número de porciones

        Returns:
            Decimal: Proteínas totales o None si no hay datos
        """
        if self.proteinas_g:
            return self.proteinas_g * porciones
        return None

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir registro de nutrición a diccionario"""
        return {
            'id': self.nutricion_id,
            'producto_id': str(self.producto_id),
            'porcion_g': float(self.porcion_g) if self.porcion_g else None,
            'calorias_kcal': float(self.calorias_kcal) if self.calorias_kcal else None,
            'proteinas_g': float(self.proteinas_g) if self.proteinas_g else None,
            'grasas_totales_g': float(self.grasas_totales_g) if self.grasas_totales_g else None,
            'grasas_saturadas_g': float(self.grasas_saturadas_g) if self.grasas_saturadas_g else None,
            'carbohidratos_g': float(self.carbohidratos_g) if self.carbohidratos_g else None,
            'azucares_g': float(self.azucares_g) if self.azucares_g else None,
            'fibra_g': float(self.fibra_g) if self.fibra_g else None,
            'sodio_mg': float(self.sodio_mg) if self.sodio_mg else None,
            'colesterol_mg': float(self.colesterol_mg) if self.colesterol_mg else None,
            'micronutrientes': self.get_micronutrientes(),
            'ig': float(self.ig) if self.ig else None,
            'carga_glucemica': float(self.carga_glucemica) if self.carga_glucemica else None,
            'fuente': self.fuente,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_producto(cls, producto_id: uuid.UUID) -> Optional['ProductoNutricion']:
        """Buscar información nutricional por producto"""
        return cls.query.filter_by(producto_id=producto_id).first()

    @classmethod
    def get_by_fuente(cls, fuente: str) -> list:
        """Buscar registros nutricionales por fuente"""
        if not fuente:
            return []
        return cls.query.filter_by(fuente=fuente).all()

    @classmethod
    def get_by_rango_calorias(cls, calorias_min: Decimal, calorias_max: Decimal) -> list:
        """Buscar productos por rango de calorías"""
        return cls.query.filter(
            cls.calorias_kcal >= calorias_min,
            cls.calorias_kcal <= calorias_max
        ).all()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        calorias_str = f" - {self.calorias_kcal} kcal" if self.calorias_kcal else ""
        return f"<ProductoNutricion nutricion_id={self.nutricion_id} producto_id={self.producto_id}{calorias_str}>"

    def __str__(self) -> str:
        calorias_str = f"{self.calorias_kcal} kcal" if self.calorias_kcal else "Sin datos"
        return f"Nutrición {self.nutricion_id}: {calorias_str}"


# ==================== PRODUCTO SNAPSHOT ====================

class ProductoSnapshot(db.Model):
    """
    Modelo de ProductoSnapshot para PostgreSQL (Supabase)
    Representa un snapshot histórico de un producto (precio, disponibilidad, etc.)
    """

    __tablename__ = 'producto_snapshot'

    __table_args__ = (
        UniqueConstraint('producto_id', 'fecha_captura', name='uq_producto_fecha_captura'),
    )

    # Campos principales
    snapshot_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Relación con producto
    producto_id = Column(GUID, ForeignKey('productos.producto_id', ondelete='CASCADE'), nullable=False)

    # Fecha de captura
    fecha_captura = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Información del producto
    precio = Column(Numeric(12, 2), nullable=True)
    unidad_medida = Column(Text, nullable=True)
    disponibilidad = Column(Boolean, default=True)
    fuente = Column(Text, nullable=True)

    # Datos adicionales
    impacto_ambiental = Column(JSON, nullable=True)
    atributos_json = Column(JSON, nullable=True)

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_snapshot(cls, producto_id: uuid.UUID, precio: Optional[Decimal] = None,
                       fecha_captura: Optional[datetime] = None, **kwargs) -> 'ProductoSnapshot':
        """
        Crear un nuevo snapshot de producto

        Args:
            producto_id: ID del producto (requerido)
            precio: Precio del producto
            fecha_captura: Fecha de captura (default: now())
            **kwargs: Campos adicionales opcionales

        Returns:
            ProductoSnapshot: Instancia del snapshot creado

        Raises:
            ValueError: Si producto_id no es válido
        """
        if not producto_id:
            raise ValueError("producto_id es requerido")

        if fecha_captura is None:
            fecha_captura = datetime.now(timezone.utc)

        snapshot = cls(
            producto_id=producto_id,
            precio=precio,
            fecha_captura=fecha_captura,
            **kwargs
        )

        return snapshot

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> int:
        """Obtener ID del snapshot"""
        return self.snapshot_id

    @property
    def captured_at(self) -> datetime:
        """Obtener fecha de captura"""
        return self.fecha_captura

    @property
    def is_available(self) -> bool:
        """Verificar si el producto está disponible"""
        return self.disponibilidad if self.disponibilidad is not None else True

    def get_impacto_ambiental(self) -> Dict[str, Any]:
        """Obtener datos de impacto ambiental"""
        return self.impacto_ambiental if self.impacto_ambiental else {}

    def set_impacto_ambiental(self, data: Dict[str, Any]) -> None:
        """Establecer datos de impacto ambiental"""
        self.impacto_ambiental = data

    def get_atributos_json(self) -> Dict[str, Any]:
        """Obtener atributos adicionales"""
        return self.atributos_json if self.atributos_json else {}

    def set_atributos_json(self, data: Dict[str, Any]) -> None:
        """Establecer atributos adicionales"""
        self.atributos_json = data

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir snapshot a diccionario"""
        return {
            'id': self.snapshot_id,
            'producto_id': str(self.producto_id),
            'fecha_captura': self.fecha_captura.isoformat() if self.fecha_captura else None,
            'precio': float(self.precio) if self.precio else None,
            'unidad_medida': self.unidad_medida,
            'disponibilidad': self.disponibilidad,
            'fuente': self.fuente,
            'impacto_ambiental': self.get_impacto_ambiental(),
            'atributos_json': self.get_atributos_json(),
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_producto(cls, producto_id: uuid.UUID, limit: Optional[int] = None) -> list:
        """Buscar snapshots por producto"""
        query = cls.query.filter_by(producto_id=producto_id).order_by(cls.fecha_captura.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_latest_by_producto(cls, producto_id: uuid.UUID) -> Optional['ProductoSnapshot']:
        """Obtener el snapshot más reciente de un producto"""
        return cls.query.filter_by(producto_id=producto_id).order_by(cls.fecha_captura.desc()).first()

    @classmethod
    def get_by_fecha_range(cls, producto_id: uuid.UUID, fecha_inicio: datetime,
                          fecha_fin: datetime) -> list:
        """Buscar snapshots por rango de fechas"""
        return cls.query.filter(
            cls.producto_id == producto_id,
            cls.fecha_captura >= fecha_inicio,
            cls.fecha_captura <= fecha_fin
        ).order_by(cls.fecha_captura.desc()).all()

    @classmethod
    def get_by_fuente(cls, fuente: str) -> list:
        """Buscar snapshots por fuente"""
        if not fuente:
            return []
        return cls.query.filter_by(fuente=fuente).order_by(cls.fecha_captura.desc()).all()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        precio_str = f" - ${self.precio}" if self.precio else ""
        return f"<ProductoSnapshot snapshot_id={self.snapshot_id} producto_id={self.producto_id}{precio_str}>"

    def __str__(self) -> str:
        precio_str = f"${self.precio}" if self.precio else "Sin precio"
        fecha_str = self.fecha_captura.strftime('%Y-%m-%d %H:%M') if self.fecha_captura else "Sin fecha"
        return f"Snapshot {self.snapshot_id}: {precio_str} - {fecha_str}"