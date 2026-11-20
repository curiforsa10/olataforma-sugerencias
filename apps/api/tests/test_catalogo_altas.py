"""Al publicar el stock, los codigos con stock que el catalogo no tenia se agregan.

El catalogo se cargo una sola vez (31-05-2026). Al 20-11-2026 le faltaban ~4% de
los codigos con stock: no se podian buscar ni tenian ficha.
"""
from src.models import PrecioProducto, ProductoCatalogo
from src.services import catalogo_service


def _publicar(client, filas):
    r = client.post("/api/admin/stock-unificado", json={"filas": filas})
    assert r.status_code == 200
    return r.json()


def _fila(producto, stock=1.0, origen="CURIFOR"):
    return {"producto": producto, "bodega": "B1", "sucursal_id": "LINDEROS", "stock": stock, "origen": origen}


def _catalogo(db, producto):
    return db.query(ProductoCatalogo).filter_by(producto=producto).first()


def test_el_codigo_nuevo_con_stock_entra_al_catalogo(client, db_session):
    db_session.add(PrecioProducto(tenant_id="curifor", producto="19 NUEVO", glosa="FILTRO NUEVO"))
    db_session.commit()

    r = _publicar(client, [_fila("19 NUEVO", 3), _fila("19 NUEVO", 2), _fila("70 FRONTERA", 4, "FRONTERA")])

    assert r["catalogo"]["agregados"] == 2
    nuevo = _catalogo(db_session, "19 NUEVO")
    assert nuevo.glosa == "FILTRO NUEVO"
    assert nuevo.stock_total == 5
    assert _catalogo(db_session, "70 FRONTERA") is not None


def test_la_descripcion_sale_del_sugerido_si_la_lista_de_precios_no_la_tiene(client, db_session):
    # El conftest siembra "20 BXO5W30AA" en el sugerido, con su descripcion.
    _publicar(client, [_fila("20 BXO5W30AA")])

    assert _catalogo(db_session, "20 BXO5W30AA").glosa == "ACEITE 5W30 LITRO FORD"


def test_no_toca_lo_que_ya_estaba(client, db_session):
    db_session.add(ProductoCatalogo(tenant_id="curifor", producto="13 VIEJO", glosa="ORIGINAL",
                                    familia="FAMILIA", stock_total=99))
    db_session.commit()

    r = _publicar(client, [_fila("13 VIEJO", 1)])

    assert r["catalogo"]["agregados"] == 0
    viejo = _catalogo(db_session, "13 VIEJO")
    assert (viejo.glosa, viejo.familia, viejo.stock_total) == ("ORIGINAL", "FAMILIA", 99)


def test_publicar_dos_veces_no_duplica(client, db_session):
    _publicar(client, [_fila("19 NUEVO")])
    r = _publicar(client, [_fila("19 NUEVO")])

    assert r["catalogo"]["agregados"] == 0
    assert db_session.query(ProductoCatalogo).filter_by(producto="19 NUEVO").count() == 1


def test_sin_stock_no_entra(client, db_session):
    _publicar(client, [_fila("19 SIN STOCK", 0), _fila("19 CON STOCK", 1)])

    assert _catalogo(db_session, "19 SIN STOCK") is None
    assert _catalogo(db_session, "19 CON STOCK") is not None


def test_un_fallo_del_catalogo_no_tumba_la_publicacion_del_stock(client, monkeypatch):
    def falla(db):
        raise RuntimeError("se cayo")

    monkeypatch.setattr(catalogo_service, "agregar_desde_stock", falla)
    r = _publicar(client, [_fila("19 NUEVO")])

    assert r["reemplazo"] is True
    assert "error" in r["catalogo"]
