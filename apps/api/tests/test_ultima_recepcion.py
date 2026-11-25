"""Ultima recepcion de cada producto, para el requerimiento de sucursal.

Abastecimiento (24-11-2026): al revisar lo que pide el vendedor, ver cuando llego el
repuesto por ultima vez en los ultimos 12 meses en la empresa, y desplegar el stock y
la ultima recepcion de cada sucursal.
"""
from datetime import date, timedelta

from src.models import StockUnificado, Sugerido, UltimaRecepcion
from src.services import recepcion_service, requerimiento_service

HOY = date.today()


def _dias(n):
    return (HOY - timedelta(days=n)).isoformat()


def _publicar(client, filas):
    r = client.post("/api/admin/recepciones", json={"filas": filas})
    assert r.status_code == 200
    return r.json()


def test_publicar_reemplaza_la_foto_y_deja_la_mas_reciente(client, db_session):
    _publicar(client, [{"producto": "19 VIEJO", "sucursal_id": "TALCA", "fecha": _dias(5)}])
    r = _publicar(client, [
        {"producto": "19 A", "sucursal_id": "LINDEROS", "fecha": _dias(40)},
        {"producto": "19 A", "sucursal_id": "LINDEROS", "fecha": _dias(10)},
        {"producto": "19 A", "sucursal_id": "CURICO", "fecha": _dias(3)},
        {"producto": "19 SIN FECHA", "sucursal_id": "LINDEROS", "fecha": None},
    ])

    assert r["filas_cargadas"] == 2
    filas = {(f.producto, f.sucursal_id): f.fecha for f in db_session.query(UltimaRecepcion)}
    assert filas == {("19 A", "LINDEROS"): HOY - timedelta(days=10),
                     ("19 A", "CURICO"): HOY - timedelta(days=3)}


def test_una_tanda_vacia_no_borra_lo_que_hay(client, db_session):
    _publicar(client, [{"producto": "19 A", "sucursal_id": "LINDEROS", "fecha": _dias(5)}])
    r = _publicar(client, [{"producto": "19 A", "sucursal_id": "LINDEROS", "fecha": ""}])

    assert r["reemplazo"] is False
    assert db_session.query(UltimaRecepcion).count() == 1


def test_por_producto_en_la_sucursal_y_en_la_empresa(db_session):
    recepcion_service.reemplazar(db_session, [
        {"producto": "19 A", "sucursal_id": "LINDEROS", "fecha": _dias(30)},
        {"producto": "19 A", "sucursal_id": "CURICO", "fecha": _dias(2)},
        # Importacion: no dice sucursal, solo cuenta para la empresa.
        {"producto": "19 B", "sucursal_id": "DESCONOCIDO", "fecha": _dias(8)},
        # Hace mas de 12 meses: no cuenta.
        {"producto": "19 C", "sucursal_id": "LINDEROS", "fecha": _dias(400)},
    ])
    prods = {"19 A", "19 B", "19 C"}

    assert recepcion_service.por_producto(db_session, prods, "LINDEROS") == {
        "19 A": HOY - timedelta(days=30)}
    assert recepcion_service.por_producto(db_session, prods) == {
        "19 A": HOY - timedelta(days=2), "19 B": HOY - timedelta(days=8)}


def test_el_requerimiento_trae_la_fecha_global_y_el_desglose(db_session):
    db_session.add(Sugerido(tenant_id="curifor", producto="19 F2GZ19G490A", sucursal_id="LINDEROS",
                            nombre_sucursal="Linderos", clasificacion_abc="D", pedir="No"))
    db_session.add_all([
        StockUnificado(tenant_id="curifor", producto="19 F2GZ19G490A", bodega="B1",
                       sucursal_id="CURICO", stock=1),
        StockUnificado(tenant_id="curifor", producto="19 F2GZ19G490A", bodega="B2",
                       sucursal_id="CURICO", stock=0.5),
        StockUnificado(tenant_id="curifor", producto="19 F2GZ19G490A", bodega="B1",
                       sucursal_id="TALCA", stock=0.5),
        StockUnificado(tenant_id="curifor", producto="19 F2GZ19G490A", bodega="B1",
                       sucursal_id="RANCAGUA", stock=0),
    ])
    db_session.commit()
    recepcion_service.reemplazar(db_session, [
        {"producto": "19 F2GZ19G490A", "sucursal_id": "CURICO", "fecha": _dias(32)},
        # Llego a Chillan y ya no queda: igual se ve, por la fecha.
        {"producto": "19 F2GZ19G490A", "sucursal_id": "CHILLAN", "fecha": _dias(60)},
        # Hace mas de 12 meses: no cuenta.
        {"producto": "19 F2GZ19G490A", "sucursal_id": "TALCA", "fecha": _dias(400)},
    ])

    r = requerimiento_service.analizar(db_session, "LINDEROS",
                                       [{"producto": "19 F2GZ19G490A", "cantidad": 1}])
    linea = r["lineas"][0]

    assert linea["ult_recepcion_empresa"] == _dias(32)
    assert "ult_recepcion_sucursal" not in linea
    assert linea["stock_nacional"] == 2
    assert linea["por_sucursal"] == [
        {"sucursal_id": "CURICO", "stock": 1.5, "stock_reemplazos": 0.0, "stock_por_codigo": {}, "ult_recepcion": _dias(32),
         "recepcion_por_codigo": {"19 F2GZ19G490A": _dias(32)}},
        {"sucursal_id": "TALCA", "stock": 0.5, "stock_reemplazos": 0.0, "stock_por_codigo": {}, "ult_recepcion": None,
         "recepcion_por_codigo": {}},
        {"sucursal_id": "CHILLAN", "stock": 0.0, "stock_reemplazos": 0.0, "stock_por_codigo": {}, "ult_recepcion": _dias(60),
         "recepcion_por_codigo": {"19 F2GZ19G490A": _dias(60)}},
    ]
    # El desglose cuadra con "Nacional".
    assert sum(f["stock"] for f in linea["por_sucursal"]) == linea["stock_nacional"]


def test_la_ruta_del_requerimiento_devuelve_la_fecha_y_el_desglose(client, db_session):
    recepcion_service.reemplazar(db_session, [
        {"producto": "61 FL500S", "sucursal_id": "LINDEROS", "fecha": _dias(26)},
    ])
    r = client.post("/api/requerimiento/reanalizar", json={
        "sucursal_id": "LINDEROS", "lineas": [{"producto": "61 FL500S", "cantidad": 1}]})

    assert r.status_code == 200
    linea = r.json()["lineas"][0]
    assert linea["ult_recepcion_empresa"] == _dias(26)
    assert linea["por_sucursal"] == [{"sucursal_id": "LINDEROS", "stock": 0.0,
                                      "stock_reemplazos": 0.0, "stock_por_codigo": {}, "ult_recepcion": _dias(26),
                                      "recepcion_por_codigo": {"61 FL500S": _dias(26)}}]


def test_el_desglose_trae_el_stock_de_los_reemplazos_y_la_recepcion_del_grupo(db_session):
    """`61 FL500S` con `19 AA5Z6714A` y `61 LB542`: se pidio ver el stock de los
    reemplazos al lado (Abastecimiento, 24-11-2026). La fecha es la del grupo: el
    repuesto es el mismo aunque haya llegado con otro codigo."""
    db_session.add(Sugerido(tenant_id="curifor", producto="61 FL500S", sucursal_id="CD REPUESTOS",
                            reemplazos="19 AA5Z6714A, 61 LB542"))
    db_session.add_all([
        StockUnificado(tenant_id="curifor", producto="61 FL500S", bodega="B1",
                       sucursal_id="CD REPUESTOS", stock=137),
        StockUnificado(tenant_id="curifor", producto="61 LB542", bodega="B1",
                       sucursal_id="CD REPUESTOS", stock=282),
        StockUnificado(tenant_id="curifor", producto="19 AA5Z6714A", bodega="B1",
                       sucursal_id="CD REPUESTOS", stock=1),
        StockUnificado(tenant_id="curifor", producto="19 AA5Z6714A", bodega="B1",
                       sucursal_id="TALCA", stock=37),
    ])
    db_session.commit()
    recepcion_service.reemplazar(db_session, [
        {"producto": "61 FL500S", "sucursal_id": "CD REPUESTOS", "fecha": _dias(20)},
        {"producto": "61 LB542", "sucursal_id": "CD REPUESTOS", "fecha": _dias(5)},
        {"producto": "19 AA5Z6714A", "sucursal_id": "TALCA", "fecha": _dias(9)},
    ])

    r = requerimiento_service.analizar(db_session, "LINDEROS",
                                       [{"producto": "61 FL500S", "cantidad": 4}])
    linea = r["lineas"][0]

    assert linea["stock_nacional"] == 137   # "Nacional" sigue siendo solo este codigo
    assert linea["ult_recepcion_empresa"] == _dias(5)
    assert linea["por_sucursal"] == [
        {"sucursal_id": "CD REPUESTOS", "stock": 137.0, "stock_reemplazos": 283.0,
         "stock_por_codigo": {"61 LB542": 282.0, "19 AA5Z6714A": 1.0},
         "ult_recepcion": _dias(5),
         "recepcion_por_codigo": {"61 FL500S": _dias(20), "61 LB542": _dias(5)}},
        {"sucursal_id": "TALCA", "stock": 0.0, "stock_reemplazos": 37.0,
         "stock_por_codigo": {"19 AA5Z6714A": 37.0},
         "ult_recepcion": _dias(9),
         "recepcion_por_codigo": {"19 AA5Z6714A": _dias(9)}},
    ]
    # Una columna por codigo de reemplazo en el desglose (Abastecimiento, 25-11-2026).
    assert sorted(linea["codigos_reemplazo"]) == ["19 AA5Z6714A", "61 LB542"]
