"""Tabla `ultima_recepcion`: la fecha en que llego por ultima vez cada producto a cada sucursal.

La pide Abastecimiento para el requerimiento de sucursal (24-11-2026): al decidir si
comprar lo que pide el vendedor, saber si el repuesto llego hace poco -aca o en otra
sucursal- dice si se esta moviendo o si nadie lo compra hace rato.

Sale de los seguimientos de compra: la Fecha Documento P/E del nacional, la Fecha
Recepcion de Frontera y la Fecha Documento Recepcion del importado. Las
importaciones casi nunca dicen sucursal: van con `sucursal_id` "DESCONOCIDO" y solo
cuentan para la fecha de la empresa.

Es una FOTO de los ultimos 12 meses: el motor la reemplaza completa en cada corrida.
"""
from datetime import date

from sqlalchemy import Date, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class UltimaRecepcion(Base):
    __tablename__ = "ultima_recepcion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, default="curifor", index=True)

    producto: Mapped[str] = mapped_column(String, nullable=False)
    sucursal_id: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        Index("ix_recepcion_producto_sucursal", "producto", "sucursal_id"),
    )
