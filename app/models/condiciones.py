"""
Modelos relacionados con Condiciones Nutricionales para NutriChat
Incluye: CondicionNutricional, UsuarioCondicion
"""

import uuid
from typing import Optional, Dict, Any

from sqlalchemy import Column, Text, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .database import db


# ==================== CONDICION NUTRICIONAL ====================

class CondicionNutricional(db.Model):
    """
    Modelo de CondicionNutricional para PostgreSQL (Supabase)
    Representa una condición nutricional del sistema (ej: diabetes, hipertensión)
    """

    __tablename__ = 'condiciones_nutricionales'

    # Campos principales
    condicion_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(Text, nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    parametros = Column(JSONB, nullable=True)

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_condicion(cls, nombre: str, descripcion: str = None,
                        parametros: Dict[str, Any] = None) -> 'CondicionNutricional':
        """
        Crear una nueva condición nutricional

        Args:
            nombre: Nombre de la condición (requerido, único)
            descripcion: Descripción de la condición
            parametros: Parámetros en formato diccionario (límites recomendados)

        Returns:
            CondicionNutricional: Instancia de la condición creada

        Raises:
            ValueError: Si nombre no es válido
        """
        if not nombre or not nombre.strip():
            raise ValueError("nombre es requerido")

        condicion = cls(
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else None,
            parametros=parametros
        )

        return condicion

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> int:
        """Obtener ID de la condición"""
        return self.condicion_id

    def get_parametros(self) -> Dict[str, Any]:
        """Obtener parámetros de la condición"""
        return self.parametros if self.parametros else {}

    def set_parametros(self, data: Dict[str, Any]) -> None:
        """Establecer parámetros de la condición"""
        self.parametros = data

    def get_limite(self, parametro: str) -> Optional[float]:
        """
        Obtener el límite de un parámetro específico

        Args:
            parametro: Nombre del parámetro (ej: 'max_azucar_g', 'max_sodio_mg')

        Returns:
            float: Valor del límite o None si no existe
        """
        parametros = self.get_parametros()
        return parametros.get(parametro)

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir condición a diccionario"""
        return {
            'id': self.condicion_id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'parametros': self.get_parametros(),
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_nombre(cls, nombre: str) -> Optional['CondicionNutricional']:
        """Buscar condición por nombre"""
        if not nombre:
            return None
        return cls.query.filter_by(nombre=nombre).first()

    @classmethod
    def get_by_id(cls, condicion_id: int) -> Optional['CondicionNutricional']:
        """Buscar condición por ID"""
        return cls.query.filter_by(condicion_id=condicion_id).first()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        return f"<CondicionNutricional condicion_id={self.condicion_id} - {self.nombre}>"

    def __str__(self) -> str:
        return self.nombre


# ==================== USUARIO CONDICION ====================

class UsuarioCondicion(db.Model):
    """
    Modelo de UsuarioCondicion para PostgreSQL (Supabase)
    Representa la relación muchos-a-muchos entre usuarios y condiciones nutricionales
    """

    __tablename__ = 'usuario_condiciones'

    __table_args__ = (
        PrimaryKeyConstraint('usuario_id', 'condicion_id'),
    )

    # Relaciones (Primary Key compuesta)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey('usuarios.usuario_id', ondelete='CASCADE'), nullable=False)
    condicion_id = Column(Integer, ForeignKey('condiciones_nutricionales.condicion_id'), nullable=False)

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_usuario_condicion(cls, usuario_id: uuid.UUID, condicion_id: int) -> 'UsuarioCondicion':
        """
        Crear una nueva relación usuario-condición

        Args:
            usuario_id: ID del usuario (requerido)
            condicion_id: ID de la condición (requerido)

        Returns:
            UsuarioCondicion: Instancia de la relación creada

        Raises:
            ValueError: Si usuario_id o condicion_id no son válidos
        """
        if not usuario_id:
            raise ValueError("usuario_id es requerido")

        if not condicion_id:
            raise ValueError("condicion_id es requerido")

        usuario_condicion = cls(
            usuario_id=usuario_id,
            condicion_id=condicion_id
        )

        return usuario_condicion

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> tuple:
        """Obtener ID compuesto de la relación"""
        return (self.usuario_id, self.condicion_id)

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir relación a diccionario"""
        return {
            'usuario_id': str(self.usuario_id),
            'condicion_id': self.condicion_id,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_usuario(cls, usuario_id: uuid.UUID) -> list:
        """Buscar todas las condiciones de un usuario"""
        return cls.query.filter_by(usuario_id=usuario_id).all()

    @classmethod
    def get_by_condicion(cls, condicion_id: int) -> list:
        """Buscar todos los usuarios con una condición"""
        return cls.query.filter_by(condicion_id=condicion_id).all()

    @classmethod
    def get_relacion(cls, usuario_id: uuid.UUID, condicion_id: int) -> Optional['UsuarioCondicion']:
        """Buscar una relación específica"""
        return cls.query.filter_by(usuario_id=usuario_id, condicion_id=condicion_id).first()

    @classmethod
    def usuario_tiene_condicion(cls, usuario_id: uuid.UUID, condicion_id: int) -> bool:
        """Verificar si un usuario tiene una condición específica"""
        return cls.get_relacion(usuario_id, condicion_id) is not None

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        return f"<UsuarioCondicion usuario_id={self.usuario_id} condicion_id={self.condicion_id}>"

    def __str__(self) -> str:
        return f"Usuario {self.usuario_id} - Condición {self.condicion_id}"

