"""
Modelo de ConfiguracionSistema para NutriChat
Almacena parámetros globales del sistema que pueden cambiar sin modificar código
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import Column, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from .database import db


class ConfiguracionSistema(db.Model):
    """
    Modelo de ConfiguracionSistema para PostgreSQL
    Almacena parámetros globales del sistema que pueden cambiar sin modificar código
    Usado por lógica interna del sistema
    Modificado solo por rol administrador
    """

    __tablename__ = 'configuracion_sistema'

    # Campos principales
    clave = Column(Text, primary_key=True)

    # Valor en formato JSONB (obligatorio)
    valor = Column(JSONB, nullable=False)

    # Timestamp de actualización
    actualizado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_config(cls, clave: str, valor: Dict[str, Any]) -> 'ConfiguracionSistema':
        """
        Crear una nueva configuración del sistema

        Args:
            clave: Clave única de la configuración (requerido)
            valor: Valor de la configuración en formato diccionario (requerido)

        Returns:
            ConfiguracionSistema: Instancia de la configuración creada

        Raises:
            ValueError: Si clave o valor no son válidos
        """
        if not clave or not clave.strip():
            raise ValueError("clave es requerido")

        if valor is None:
            raise ValueError("valor es requerido")

        config = cls(
            clave=clave.strip(),
            valor=valor
        )

        return config

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> str:
        """Obtener clave de la configuración"""
        return self.clave

    @property
    def updated_at(self) -> datetime:
        """Obtener fecha de actualización"""
        return self.actualizado_en

    def get_valor(self) -> Dict[str, Any]:
        """Obtener valor de la configuración"""
        return self.valor if self.valor else {}

    def set_valor(self, data: Dict[str, Any]) -> None:
        """Establecer valor de la configuración"""
        if data is None:
            raise ValueError("valor no puede ser None")
        self.valor = data

    def get_valor_key(self, key: str, default: Any = None) -> Any:
        """Obtener un valor específico dentro de la configuración"""
        valor = self.get_valor()
        return valor.get(key, default)

    def set_valor_key(self, key: str, value: Any) -> None:
        """Establecer un valor específico dentro de la configuración"""
        valor = self.get_valor()
        valor[key] = value
        self.set_valor(valor)

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir configuración a diccionario"""
        return {
            'clave': self.clave,
            'valor': self.get_valor(),
            'actualizado_en': self.actualizado_en.isoformat() if self.actualizado_en else None,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_clave(cls, clave: str) -> Optional['ConfiguracionSistema']:
        """Buscar configuración por clave"""
        if not clave:
            return None
        return cls.query.filter_by(clave=clave).first()

    @classmethod
    def get_all(cls) -> list:
        """Obtener todas las configuraciones"""
        return cls.query.order_by(cls.clave).all()

    @classmethod
    def get_valor_by_clave(cls, clave: str, default: Any = None) -> Any:
        """
        Obtener valor de una configuración por clave

        Args:
            clave: Clave de la configuración
            default: Valor por defecto si no existe

        Returns:
            Valor de la configuración o default
        """
        config = cls.get_by_clave(clave)
        if config:
            return config.get_valor()
        return default

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        return f"<ConfiguracionSistema clave={self.clave}>"

    def __str__(self) -> str:
        return f"Configuración: {self.clave}"

