"""
Modelo de ScrapingCache para NutriChat
Cachea respuestas HTML del scraping para evitar requests repetidos
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import Column, Text, Integer, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from .database import db


class ScrapingCache(db.Model):
    """
    Modelo de ScrapingCache para PostgreSQL
    Cachea respuestas HTML del scraping para evitar requests repetidos
    y permitir depuración
    Uso exclusivo del scraper
    No expuesto por API pública
    """

    __tablename__ = 'scraping_cache'

    __table_args__ = (
        UniqueConstraint('url', name='uq_scraping_cache_url'),
    )

    # Campos principales
    cache_id = Column(Integer, primary_key=True, autoincrement=True)

    # URL única (obligatorio)
    url = Column(Text, nullable=False, unique=True)

    # Contenido HTML
    html_content = Column(Text, nullable=True)

    # Headers de la respuesta
    headers = Column(JSONB, nullable=True)

    # Código de estado HTTP
    status_code = Column(Integer, nullable=True)

    # Timestamps
    capturado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valido_hasta = Column(DateTime(timezone=True), nullable=True)

    # ==================== MÉTODOS DE CREACIÓN ====================

    @classmethod
    def create_cache(cls, url: str, html_content: Optional[str] = None,
                    headers: Optional[Dict[str, Any]] = None,
                    status_code: Optional[int] = None,
                    valido_hasta: Optional[datetime] = None) -> 'ScrapingCache':
        """
        Crear un nuevo registro de cache de scraping

        Args:
            url: URL única (requerido)
            html_content: Contenido HTML capturado
            headers: Headers de la respuesta HTTP
            status_code: Código de estado HTTP
            valido_hasta: Fecha hasta la cual el cache es válido

        Returns:
            ScrapingCache: Instancia del cache creado

        Raises:
            ValueError: Si url no es válido
        """
        if not url or not url.strip():
            raise ValueError("url es requerido")

        cache = cls(
            url=url.strip(),
            html_content=html_content,
            headers=headers,
            status_code=status_code,
            valido_hasta=valido_hasta
        )

        return cache

    # ==================== PROPIEDADES DE CONVENIENCIA ====================

    @property
    def id(self) -> int:
        """Obtener ID del cache"""
        return self.cache_id

    @property
    def captured_at(self) -> datetime:
        """Obtener fecha de captura"""
        return self.capturado_en

    @property
    def valid_until(self) -> Optional[datetime]:
        """Obtener fecha de validez"""
        return self.valido_hasta

    @property
    def is_valid(self) -> bool:
        """Verificar si el cache es válido"""
        if self.valido_hasta is None:
            return True
        return datetime.now(timezone.utc) < self.valido_hasta

    @property
    def is_expired(self) -> bool:
        """Verificar si el cache ha expirado"""
        return not self.is_valid

    def get_headers(self) -> Dict[str, Any]:
        """Obtener headers de la respuesta"""
        return self.headers if self.headers else {}

    def set_headers(self, data: Dict[str, Any]) -> None:
        """Establecer headers de la respuesta"""
        self.headers = data

    # ==================== SERIALIZACIÓN ====================

    def to_dict(self, include_html: bool = False) -> Dict[str, Any]:
        """
        Convertir cache a diccionario

        Args:
            include_html: Si incluir el contenido HTML (puede ser muy grande)

        Returns:
            Diccionario con los datos del cache
        """
        data = {
            'id': self.cache_id,
            'url': self.url,
            'headers': self.get_headers(),
            'status_code': self.status_code,
            'capturado_en': self.capturado_en.isoformat() if self.capturado_en else None,
            'valido_hasta': self.valido_hasta.isoformat() if self.valido_hasta else None,
            'is_valid': self.is_valid,
            'is_expired': self.is_expired,
        }

        if include_html:
            data['html_content'] = self.html_content
        else:
            data['html_content_length'] = len(self.html_content) if self.html_content else 0

        return data

    def to_json_safe(self) -> Dict[str, Any]:
        """Convertir a JSON seguro (sin HTML por defecto)"""
        return self.to_dict(include_html=False)

    # ==================== MÉTODOS DE CONSULTA ====================

    @classmethod
    def get_by_url(cls, url: str) -> Optional['ScrapingCache']:
        """Buscar cache por URL"""
        if not url:
            return None
        return cls.query.filter_by(url=url.strip()).first()

    @classmethod
    def get_valid_by_url(cls, url: str) -> Optional['ScrapingCache']:
        """Buscar cache válido por URL"""
        if not url:
            return None
        cache = cls.get_by_url(url)
        if cache and cache.is_valid:
            return cache
        return None

    @classmethod
    def get_expired(cls, limit: Optional[int] = None) -> list:
        """Obtener caches expirados"""
        query = cls.query.filter(
            cls.valido_hasta.isnot(None),
            cls.valido_hasta < datetime.now(timezone.utc)
        ).order_by(cls.capturado_en.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_by_status_code(cls, status_code: int) -> list:
        """Buscar caches por código de estado"""
        return cls.query.filter_by(status_code=status_code).order_by(cls.capturado_en.desc()).all()

    @classmethod
    def get_recent(cls, limit: int = 100) -> list:
        """Obtener caches recientes"""
        return cls.query.order_by(cls.capturado_en.desc()).limit(limit).all()

    # ==================== REPRESENTACIÓN ====================

    def __repr__(self) -> str:
        status_str = f" - {self.status_code}" if self.status_code else ""
        return f"<ScrapingCache cache_id={self.cache_id} url={self.url[:50]}...{status_str}>"

    def __str__(self) -> str:
        fecha_str = self.capturado_en.strftime('%Y-%m-%d %H:%M') if self.capturado_en else "Sin fecha"
        estado = "Válido" if self.is_valid else "Expirado"
        return f"Cache [{fecha_str}]: {self.url[:50]}... ({estado})"

