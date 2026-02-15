"""
Modelos relacionados con Reportes para NutriChat
Incluye: Reporte, FeedbackRecomendacion
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import Column, Text, Boolean, DateTime, BigInteger, ForeignKey, func
from app.db_types import GUID
from sqlalchemy import JSON

from .database import db


# ==================== REPORTE ====================

class Reporte(db.Model):
    """
    Modelo de Reporte para PostgreSQL (Supabase)
    Representa un reporte generado por administrador o usuario
    """

    __tablename__ = 'reportes'

    # Campos principales
    reporte_id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Relación con usuario (opcional, puede ser reporte del sistema)
    usuario_id = Column(GUID(), ForeignKey('usuarios.usuario_id'), nullable=True)

    # Información del reporte
    tipo = Column(Text, nullable=True)
    fecha_emision = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Datos estructurados
    parametros = Column(JSON, nullable=True)
    contenido = Column(JSON, nullable=True)

    # Enlace a archivo externo
    enlace_archivo = Column(Text, nullable=True)

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_reporte(cls, tipo: str = None, usuario_id: uuid.UUID = None,
                      parametros: Dict[str, Any] = None, **kwargs) -> 'Reporte':
        """
        Crear un nuevo reporte

        Args:
            tipo: Tipo de reporte
            usuario_id: ID del usuario que genera el reporte (opcional)
            parametros: Parámetros del reporte en formato diccionario
            **kwargs: Campos adicionales opcionales

        Returns:
            Reporte: Instancia del reporte creado
        """
        reporte = cls(
            tipo=tipo,
            usuario_id=usuario_id,
            parametros=parametros,
            **kwargs
        )

        return reporte

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> uuid.UUID:
        """Obtener ID del reporte"""
        return self.reporte_id

    @property
    def issued_at(self) -> datetime:
        """Obtener fecha de emisión"""
        return self.fecha_emision

    def get_parametros(self) -> Dict[str, Any]:
        """Obtener parámetros del reporte"""
        return self.parametros if self.parametros else {}

    def set_parametros(self, data: Dict[str, Any]) -> None:
        """Establecer parámetros del reporte"""
        self.parametros = data

    def get_contenido(self) -> Dict[str, Any]:
        """Obtener contenido del reporte"""
        return self.contenido if self.contenido else {}

    def set_contenido(self, data: Dict[str, Any]) -> None:
        """Establecer contenido del reporte"""
        self.contenido = data

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir reporte a diccionario"""
        return {
            'id': str(self.reporte_id),
            'usuario_id': str(self.usuario_id) if self.usuario_id else None,
            'tipo': self.tipo,
            'fecha_emision': self.fecha_emision.isoformat() if self.fecha_emision else None,
            'parametros': self.get_parametros(),
            'contenido': self.get_contenido(),
            'enlace_archivo': self.enlace_archivo,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_usuario(cls, usuario_id: uuid.UUID) -> list:
        """Buscar reportes por usuario"""
        return cls.query.filter_by(usuario_id=usuario_id).order_by(cls.fecha_emision.desc()).all()

    @classmethod
    def get_by_tipo(cls, tipo: str) -> list:
        """Buscar reportes por tipo"""
        if not tipo:
            return []
        return cls.query.filter_by(tipo=tipo).order_by(cls.fecha_emision.desc()).all()

    @classmethod
    def get_system_reportes(cls) -> list:
        """Obtener reportes del sistema (sin usuario_id)"""
        return cls.query.filter_by(usuario_id=None).order_by(cls.fecha_emision.desc()).all()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        tipo_str = f" - {self.tipo}" if self.tipo else ""
        return f"<Reporte reporte_id={self.reporte_id}{tipo_str}>"

    def __str__(self) -> str:
        tipo_str = f" ({self.tipo})" if self.tipo else ""
        fecha_str = self.fecha_emision.strftime('%Y-%m-%d') if self.fecha_emision else "Sin fecha"
        return f"Reporte{tipo_str} - {fecha_str}"


# ==================== FEEDBACK RECOMENDACION ====================

class FeedbackRecomendacion(db.Model):
    """
    Modelo de FeedbackRecomendacion para PostgreSQL (Supabase)
    Representa el feedback del usuario sobre recomendaciones del algoritmo
    """

    __tablename__ = 'feedback_recomendacion'

    # Campos principales
    feedback_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Relaciones
    usuario_id = Column(GUID(), ForeignKey('usuarios.usuario_id'), nullable=False)
    lista_id = Column(GUID(), ForeignKey('listas_mercado.lista_id'), nullable=False)

    # Información del feedback
    aceptada = Column(Boolean, nullable=True)
    comentarios = Column(Text, nullable=True)
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_feedback(cls, usuario_id: uuid.UUID, lista_id: uuid.UUID,
                       aceptada: bool = None, comentarios: str = None) -> 'FeedbackRecomendacion':
        """
        Crear un nuevo feedback de recomendación

        Args:
            usuario_id: ID del usuario (requerido)
            lista_id: ID de la lista de mercado (requerido)
            aceptada: Si la recomendación fue aceptada
            comentarios: Comentarios del usuario

        Returns:
            FeedbackRecomendacion: Instancia del feedback creado

        Raises:
            ValueError: Si usuario_id o lista_id no son válidos
        """
        if not usuario_id:
            raise ValueError("usuario_id es requerido")

        if not lista_id:
            raise ValueError("lista_id es requerido")

        feedback = cls(
            usuario_id=usuario_id,
            lista_id=lista_id,
            aceptada=aceptada,
            comentarios=comentarios.strip() if comentarios else None
        )

        return feedback

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> int:
        """Obtener ID del feedback"""
        return self.feedback_id

    @property
    def feedback_date(self) -> datetime:
        """Obtener fecha del feedback"""
        return self.fecha

    @property
    def is_accepted(self) -> Optional[bool]:
        """Verificar si la recomendación fue aceptada"""
        return self.aceptada

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convertir feedback a diccionario"""
        return {
            'id': self.feedback_id,
            'usuario_id': str(self.usuario_id),
            'lista_id': str(self.lista_id),
            'aceptada': self.aceptada,
            'comentarios': self.comentarios,
            'fecha': self.fecha.isoformat() if self.fecha else None,
        }

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro"""
        return self.to_dict()

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_usuario(cls, usuario_id: uuid.UUID) -> list:
        """Buscar feedback por usuario"""
        return cls.query.filter_by(usuario_id=usuario_id).order_by(cls.fecha.desc()).all()

    @classmethod
    def get_by_lista(cls, lista_id: uuid.UUID) -> list:
        """Buscar feedback por lista"""
        return cls.query.filter_by(lista_id=lista_id).order_by(cls.fecha.desc()).all()

    @classmethod
    def get_aceptadas(cls, usuario_id: uuid.UUID = None) -> list:
        """Buscar feedback aceptados"""
        query = cls.query.filter_by(aceptada=True)
        if usuario_id:
            query = query.filter_by(usuario_id=usuario_id)
        return query.order_by(cls.fecha.desc()).all()

    @classmethod
    def get_rechazadas(cls, usuario_id: uuid.UUID = None) -> list:
        """Buscar feedback rechazados"""
        query = cls.query.filter_by(aceptada=False)
        if usuario_id:
            query = query.filter_by(usuario_id=usuario_id)
        return query.order_by(cls.fecha.desc()).all()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        estado = "Aceptada" if self.aceptada else "Rechazada" if self.aceptada is False else "Sin estado"
        return f"<FeedbackRecomendacion feedback_id={self.feedback_id} - {estado}>"

    def __str__(self) -> str:
        estado = "Aceptada" if self.aceptada else "Rechazada" if self.aceptada is False else "Sin evaluar"
        return f"Feedback {self.feedback_id}: {estado}"

