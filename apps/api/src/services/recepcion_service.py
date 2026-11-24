"""Ultima recepcion de cada producto: la publica el motor, la lee el requerimiento.

Ver `models/ultima_recepcion.py` para el porque.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import UltimaRecepcion

settings = get_settings()

_LOTE = 1000
# "En el año" segun Abastecimiento: los ultimos 12 meses, no el año calendario
# (en enero casi todo saldria vacio).
DIAS_VENTANA = 365


def _fecha(v) -> date | None:
    if isinstance(v, date):
        return v
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def reemplazar(db: Session, filas: list[dict]) -> dict:
    """Reemplaza la foto con la que acaba de calcular el motor.

    Cada fila: producto, sucursal_id, fecha. Una fila sin fecha no dice nada y se
    descarta. Si para el mismo producto y sucursal viene mas de una, queda la mas
    reciente.
    """
    tenant = settings.default_tenant_id
    ultima: dict[tuple[str, str | None], date] = {}
    for f in filas:
        prod = str(f.get("producto") or "").strip()
        fecha = _fecha(f.get("fecha"))
        if not prod or fecha is None:
            continue
        clave = (prod, str(f.get("sucursal_id") or "").strip() or None)
        if clave not in ultima or fecha > ultima[clave]:
            ultima[clave] = fecha

    # Una tanda vacia NO borra lo que hay: mejor la foto anterior que decir
    # "no llego nunca" porque una corrida fallo.
    if not ultima:
        return {"filas_cargadas": 0, "ignoradas": len(filas), "reemplazo": False}

    validas = [
        {"tenant_id": tenant, "producto": p, "sucursal_id": s, "fecha": d}
        for (p, s), d in ultima.items()
    ]
    db.execute(delete(UltimaRecepcion).where(UltimaRecepcion.tenant_id == tenant))
    for i in range(0, len(validas), _LOTE):
        db.execute(insert(UltimaRecepcion), validas[i : i + _LOTE])
    db.commit()
    return {"filas_cargadas": len(validas), "ignoradas": len(filas) - len(validas),
            "reemplazo": True}


def por_producto_y_sucursal(
    db: Session, productos: set[str], hoy: date | None = None
) -> dict[str, dict[str | None, date]]:
    """{producto: {sucursal_id: fecha}} de los ultimos 12 meses, para el desglose."""
    if not productos:
        return {}
    desde = (hoy or date.today()) - timedelta(days=DIAS_VENTANA)
    stmt = select(UltimaRecepcion.producto, UltimaRecepcion.sucursal_id,
                  UltimaRecepcion.fecha).where(
        UltimaRecepcion.tenant_id == settings.default_tenant_id,
        UltimaRecepcion.producto.in_(productos),
        UltimaRecepcion.fecha >= desde,
    )
    salida: dict[str, dict[str | None, date]] = {}
    try:
        for p, s, d in db.execute(stmt).all():
            actual = salida.setdefault(p, {})
            if s not in actual or d > actual[s]:
                actual[s] = d
    except Exception:  # noqa: BLE001 - tabla ausente antes del primer despliegue
        db.rollback()
        return {}
    return salida


def por_producto(
    db: Session, productos: set[str], sucursal_id: str | None = None, hoy: date | None = None
) -> dict[str, date]:
    """{producto: fecha de la ultima recepcion} de los ultimos 12 meses.

    Con `sucursal_id`, solo las recepciones de esa sucursal; sin ella, la mas
    reciente de toda la empresa (incluye las importaciones, que no dicen sucursal).
    Tolerante a que la tabla no exista todavia.
    """
    if not productos:
        return {}
    desde = (hoy or date.today()) - timedelta(days=DIAS_VENTANA)
    stmt = (
        select(UltimaRecepcion.producto, func.max(UltimaRecepcion.fecha))
        .where(
            UltimaRecepcion.tenant_id == settings.default_tenant_id,
            UltimaRecepcion.producto.in_(productos),
            UltimaRecepcion.fecha >= desde,
        )
        .group_by(UltimaRecepcion.producto)
    )
    if sucursal_id:
        stmt = stmt.where(UltimaRecepcion.sucursal_id == sucursal_id)
    try:
        return {p: d for p, d in db.execute(stmt).all() if d is not None}
    except Exception:  # noqa: BLE001 - tabla ausente antes del primer despliegue
        db.rollback()
        return {}
