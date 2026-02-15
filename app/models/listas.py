"""
Modelos relacionados con Listas de Mercado para NutriChat
Incluye: ListaMercado, ProductosEnLista
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import Column, Text, Numeric, BigInteger, ForeignKey, DateTime, func
from app.db_types import GUID

from .database import db


# ==================== LISTA MERCADO ====================

class ListaMercado(db.Model):
    """
    Modelo de ListaMercado para PostgreSQL (Supabase)
    Representa una lista de compras/market del usuario
    """

    __tablename__ = 'listas_mercado'

    # Campos principales
    lista_id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Relación con usuario
    usuario_id = Column(GUID(), ForeignKey('usuarios.usuario_id'), nullable=False)

    # Información de la lista
    nombre = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)

    # Fechas
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=True)

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_lista(cls, usuario_id: uuid.UUID, nombre: str = None,
                    descripcion: str = None, **kwargs) -> 'ListaMercado':
        """
        Crear una nueva lista de mercado

        Args:
            usuario_id: ID del usuario (requerido)
            nombre: Nombre de la lista
            descripcion: Descripción de la lista
            **kwargs: Campos adicionales opcionales

        Returns:
            ListaMercado: Instancia de la lista creada

        Raises:
            ValueError: Si usuario_id no es válido
        """
        if not usuario_id:
            raise ValueError("usuario_id es requerido")

        lista = cls(
            usuario_id=usuario_id,
            nombre=nombre.strip() if nombre else None,
            descripcion=descripcion.strip() if descripcion else None,
            **kwargs
        )

        return lista

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> uuid.UUID:
        """Obtener ID de la lista"""
        return self.lista_id

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
        """Convertir lista a diccionario"""
        return {
            'id': str(self.lista_id),
            'usuario_id': str(self.usuario_id),
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
            'actualizado_en': self.actualizado_en.isoformat() if self.actualizado_en else None,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_usuario(cls, usuario_id: uuid.UUID) -> list:
        """Buscar listas por usuario"""
        return cls.query.filter_by(usuario_id=usuario_id).order_by(cls.creado_en.desc()).all()

    @classmethod
    def get_by_nombre(cls, usuario_id: uuid.UUID, nombre: str) -> list:
        """Buscar listas por nombre (búsqueda parcial)"""
        if not nombre:
            return []
        return cls.query.filter(
            cls.usuario_id == usuario_id,
            cls.nombre.ilike(f'%{nombre}%')
        ).order_by(cls.creado_en.desc()).all()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        nombre_str = f" - {self.nombre}" if self.nombre else ""
        return f"<ListaMercado lista_id={self.lista_id}{nombre_str}>"

    def __str__(self) -> str:
        nombre_str = self.nombre if self.nombre else "Lista sin nombre"
        return f"{nombre_str}"


# ==================== PRODUCTOS EN LISTA ====================

class ProductosEnLista(db.Model):
    """
    Modelo de ProductosEnLista para PostgreSQL (Supabase)
    Representa un producto dentro de una lista de mercado
    """

    __tablename__ = 'productos_en_lista'

    # Campos principales
    producto_lista_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Relaciones
    lista_id = Column(GUID(), ForeignKey('listas_mercado.lista_id', ondelete='CASCADE'), nullable=False)
    producto_id = Column(GUID(), ForeignKey('productos.producto_id'), nullable=False)

    # Información del producto en la lista
    cantidad = Column(Numeric(8, 3), nullable=False, default=Decimal('1'))
    unidad_medida = Column(Text, nullable=True)
    precio_unitario = Column(Numeric(12, 2), nullable=True)
    notas = Column(Text, nullable=True)

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_item_lista(cls, lista_id: uuid.UUID, producto_id: uuid.UUID,
                         cantidad: Optional[Decimal] = None, **kwargs) -> 'ProductosEnLista':
        """
        Crear un nuevo item de producto en una lista

        Args:
            lista_id: ID de la lista de mercado (requerido)
            producto_id: ID del producto (requerido)
            cantidad: Cantidad del producto (default: 1)
            **kwargs: Campos adicionales opcionales

        Returns:
            ProductosEnLista: Instancia del item creado

        Raises:
            ValueError: Si lista_id o producto_id no son válidos
        """
        if not lista_id:
            raise ValueError("lista_id es requerido")

        if not producto_id:
            raise ValueError("producto_id es requerido")

        if cantidad is None:
            cantidad = Decimal('1')

        item = cls(
            lista_id=lista_id,
            producto_id=producto_id,
            cantidad=cantidad,
            **kwargs
        )

        return item

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> int:
        """Obtener ID del item"""
        return self.producto_lista_id

    @property
    def precio_total(self) -> Optional[Decimal]:
        """Calcular precio total (cantidad * precio_unitario)"""
        if self.precio_unitario and self.cantidad:
            return self.precio_unitario * self.cantidad
        return None

    def actualizar_cantidad(self, nueva_cantidad: Decimal) -> None:
        """
        Actualizar la cantidad del producto

        Args:
            nueva_cantidad: Nueva cantidad del producto

        Raises:
            ValueError: Si la cantidad es negativa o cero
        """
        if nueva_cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")
        self.cantidad = nueva_cantidad

    def establecer_precio(self, precio: Decimal) -> None:
        """
        Establecer precio unitario del producto

        Args:
            precio: Precio unitario del producto

        Raises:
            ValueError: Si el precio es negativo
        """
        if precio < 0:
            raise ValueError("El precio no puede ser negativo")
        self.precio_unitario = precio

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir item de lista a diccionario"""
        return {
            'id': self.producto_lista_id,
            'lista_id': str(self.lista_id),
            'producto_id': str(self.producto_id),
            'cantidad': float(self.cantidad) if self.cantidad else None,
            'unidad_medida': self.unidad_medida,
            'precio_unitario': float(self.precio_unitario) if self.precio_unitario else None,
            'precio_total': float(self.precio_total) if self.precio_total else None,
            'notas': self.notas,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_lista(cls, lista_id: uuid.UUID) -> list:
        """Buscar todos los productos en una lista"""
        return cls.query.filter_by(lista_id=lista_id).all()

    @classmethod
    def get_by_producto(cls, producto_id: uuid.UUID) -> list:
        """Buscar todas las listas que contienen un producto"""
        return cls.query.filter_by(producto_id=producto_id).all()

    @classmethod
    def get_item(cls, lista_id: uuid.UUID, producto_id: uuid.UUID) -> Optional['ProductosEnLista']:
        """Buscar un item específico por lista y producto"""
        return cls.query.filter_by(lista_id=lista_id, producto_id=producto_id).first()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        cantidad_str = f"{self.cantidad}" if self.cantidad else "1"
        return f"<ProductosEnLista producto_lista_id={self.producto_lista_id} lista_id={self.lista_id} cantidad={cantidad_str}>"

    def __str__(self) -> str:
        cantidad_str = f"{self.cantidad}"
        if self.unidad_medida:
            cantidad_str += f" {self.unidad_medida}"
        precio_str = f" - ${self.precio_unitario}" if self.precio_unitario else ""
        return f"Producto {self.producto_id}: {cantidad_str}{precio_str}"

