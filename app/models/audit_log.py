"""
Modelo de AuditLog para NutriChat
Registra eventos críticos del sistema para auditoría y trazabilidad
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import Column, Text, BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .database import db


class AuditLog(db.Model):
    """
    Modelo de AuditLog para PostgreSQL
    Registra eventos críticos del sistema para auditoría y trazabilidad
    NO se usa para reportes normales ni analytics
    """

    __tablename__ = 'audit_logs'

    # Campos principales
    log_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Información de la entidad afectada
    entidad = Column(Text, nullable=False)
    entidad_id = Column(Text, nullable=True)

    # Acción realizada
    accion = Column(Text, nullable=False)

    # Usuario que realizó la acción (opcional)
    usuario_id = Column(UUID(as_uuid=True), nullable=True)

    # Payload con datos relevantes del evento
    payload = Column(JSONB, nullable=True)

    # Timestamp
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_log(cls, entidad: str, accion: str, entidad_id: Optional[str] = None,
                  usuario_id: Optional[Any] = None, payload: Optional[Dict[str, Any]] = None) -> 'AuditLog':
        """
        Crear un nuevo registro de auditoría

        Args:
            entidad: Nombre de la entidad afectada (requerido)
            accion: Acción realizada (requerido)
            entidad_id: ID de la entidad afectada
            usuario_id: ID del usuario que realizó la acción
            payload: Datos relevantes del evento

        Returns:
            AuditLog: Instancia del log creado

        Raises:
            ValueError: Si entidad o accion no son válidos
        """
        if not entidad or not entidad.strip():
            raise ValueError("entidad es requerido")

        if not accion or not accion.strip():
            raise ValueError("accion es requerido")

        log = cls(
            entidad=entidad.strip(),
            accion=accion.strip(),
            entidad_id=str(entidad_id) if entidad_id else None,
            usuario_id=usuario_id,
            payload=payload
        )

        return log

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> int:
        """Obtener ID del log"""
        return self.log_id

    @property
    def created_at(self) -> datetime:
        """Obtener fecha de creación"""
        return self.creado_en

    def get_payload(self) -> Dict[str, Any]:
        """Obtener payload del evento"""
        return self.payload if self.payload else {}

    def set_payload(self, data: Dict[str, Any]) -> None:
        """Establecer payload del evento"""
        self.payload = data

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir log a diccionario"""
        return {
            'id': self.log_id,
            'entidad': self.entidad,
            'entidad_id': self.entidad_id,
            'accion': self.accion,
            'usuario_id': str(self.usuario_id) if self.usuario_id else None,
            'payload': self.get_payload(),
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_entidad(cls, entidad: str, limit: Optional[int] = None) -> list:
        """Buscar logs por entidad"""
        if not entidad:
            return []
        query = cls.query.filter_by(entidad=entidad).order_by(cls.creado_en.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_by_entidad_id(cls, entidad: str, entidad_id: str) -> list:
        """Buscar logs por entidad e ID"""
        if not entidad or not entidad_id:
            return []
        return cls.query.filter_by(entidad=entidad, entidad_id=entidad_id).order_by(cls.creado_en.desc()).all()

    @classmethod
    def get_by_usuario(cls, usuario_id: Any, limit: Optional[int] = None) -> list:
        """Buscar logs por usuario"""
        query = cls.query.filter_by(usuario_id=usuario_id).order_by(cls.creado_en.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_by_accion(cls, accion: str, limit: Optional[int] = None) -> list:
        """Buscar logs por acción"""
        if not accion:
            return []
        query = cls.query.filter_by(accion=accion).order_by(cls.creado_en.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_recent(cls, limit: int = 100) -> list:
        """Obtener logs recientes"""
        return cls.query.order_by(cls.creado_en.desc()).limit(limit).all()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        return f"<AuditLog log_id={self.log_id} entidad={self.entidad} accion={self.accion}>"

    def __str__(self) -> str:
        fecha_str = self.creado_en.strftime('%Y-%m-%d %H:%M:%S') if self.creado_en else "Sin fecha"
        return f"AuditLog [{fecha_str}]: {self.entidad} - {self.accion}"

