"""
Modelo de TelegramSesion para NutriChat
Persiste el estado de conversación del bot de Telegram
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import Column, Text, BigInteger, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .database import db


class TelegramSesion(db.Model):
    """
    Modelo de TelegramSesion para PostgreSQL
    Representa una sesión temporal de conversación del bot de Telegram
    NO representa usuarios, representa sesiones temporales
    """

    __tablename__ = 'telegram_sesiones'

    # Campos principales
    sesion_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relación con usuario (opcional)
    telegram_id = Column(BigInteger, nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey('usuarios.usuario_id'), nullable=True)

    # Estado de conversación
    estado_conversacion = Column(Text, nullable=True)

    # Contexto temporal del flujo conversacional
    contexto = Column(JSONB, nullable=True)

    # Timestamps
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Índices
    __table_args__ = (
        Index('idx_telegram_sesiones_telegram_id', 'telegram_id'),
    )

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_sesion(cls, telegram_id: int, usuario_id: Optional[uuid.UUID] = None,
                     estado_conversacion: Optional[str] = None,
                     contexto: Optional[Dict[str, Any]] = None) -> 'TelegramSesion':
        """
        Crear una nueva sesión de Telegram

        Args:
            telegram_id: ID de Telegram (requerido)
            usuario_id: ID del usuario asociado (opcional)
            estado_conversacion: Estado actual de la conversación
            contexto: Datos temporales del flujo conversacional

        Returns:
            TelegramSesion: Instancia de la sesión creada

        Raises:
            ValueError: Si telegram_id no es válido
        """
        if not telegram_id:
            raise ValueError("telegram_id es requerido")

        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id debe ser un número entero")

        sesion = cls(
            telegram_id=telegram_id,
            usuario_id=usuario_id,
            estado_conversacion=estado_conversacion.strip() if estado_conversacion else None,
            contexto=contexto
        )

        return sesion

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> uuid.UUID:
        """Obtener ID de la sesión"""
        return self.sesion_id

    @property
    def created_at(self) -> datetime:
        """Obtener fecha de creación"""
        return self.creado_en

    @property
    def updated_at(self) -> datetime:
        """Obtener fecha de actualización"""
        return self.actualizado_en

    def get_contexto(self) -> Dict[str, Any]:
        """Obtener contexto de la conversación"""
        return self.contexto if self.contexto else {}

    def set_contexto(self, data: Dict[str, Any]) -> None:
        """Establecer contexto de la conversación"""
        self.contexto = data

    def update_contexto(self, key: str, value: Any) -> None:
        """Actualizar un valor específico en el contexto"""
        contexto = self.get_contexto()
        contexto[key] = value
        self.set_contexto(contexto)

    def clear_contexto(self) -> None:
        """Limpiar el contexto de la conversación"""
        self.contexto = {}

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir sesión a diccionario"""
        return {
            'id': str(self.sesion_id),
            'telegram_id': self.telegram_id,
            'usuario_id': str(self.usuario_id) if self.usuario_id else None,
            'estado_conversacion': self.estado_conversacion,
            'contexto': self.get_contexto(),
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
            'actualizado_en': self.actualizado_en.isoformat() if self.actualizado_en else None,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_telegram_id(cls, telegram_id: int) -> Optional['TelegramSesion']:
        """Buscar sesión por Telegram ID"""
        return cls.query.filter_by(telegram_id=telegram_id).order_by(cls.actualizado_en.desc()).first()

    @classmethod
    def get_by_usuario(cls, usuario_id: uuid.UUID) -> list:
        """Buscar sesiones por usuario"""
        return cls.query.filter_by(usuario_id=usuario_id).order_by(cls.actualizado_en.desc()).all()

    @classmethod
    def get_by_estado(cls, estado_conversacion: str) -> list:
        """Buscar sesiones por estado de conversación"""
        if not estado_conversacion:
            return []
        return cls.query.filter_by(estado_conversacion=estado_conversacion).all()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        estado_str = f" - {self.estado_conversacion}" if self.estado_conversacion else ""
        return f"<TelegramSesion sesion_id={self.sesion_id} telegram_id={self.telegram_id}{estado_str}>"

    def __str__(self) -> str:
        estado_str = f" ({self.estado_conversacion})" if self.estado_conversacion else " (Sin estado)"
        return f"Sesión Telegram {self.telegram_id}{estado_str}"

