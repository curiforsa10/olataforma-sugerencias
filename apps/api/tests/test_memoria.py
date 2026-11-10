"""Despues de cada POST pesado la API devuelve al sistema la memoria libre.

El 09-11-2026 Render corto la API por memoria a mitad de la publicacion del motor,
en un paso chico que llego con lo que habian dejado reservado los anteriores.
"""
from src.services import memoria


def test_solo_los_post_de_publicacion_son_pasos_pesados():
    assert memoria.es_paso_pesado("POST", "/api/admin/cargar-sugerido")
    assert memoria.es_paso_pesado("POST", "/api/admin/reemplazos-ford")
    assert memoria.es_paso_pesado("POST", "/api/precios/recalcular")
    assert memoria.es_paso_pesado("POST", "/api/requerimiento/sku-proveedor")
    assert not memoria.es_paso_pesado("GET", "/api/admin/fuentes")
    assert not memoria.es_paso_pesado("GET", "/api/sugerido")
    assert not memoria.es_paso_pesado("POST", "/api/sugerencias-manuales")


def test_liberar_no_rompe_en_ningun_sistema():
    memoria.liberar()
    assert memoria.limitar_arenas() in (True, False)


def test_el_middleware_libera_tras_un_post_pesado_y_no_cambia_la_respuesta(client, monkeypatch):
    llamadas = []
    monkeypatch.setattr(memoria, "liberar", lambda: llamadas.append(1))
    r = client.post("/api/admin/stock-transito", json={"filas": []})
    assert r.status_code in (200, 400)
    assert llamadas == [1]


def test_el_middleware_no_toca_las_consultas_de_la_web(client, monkeypatch):
    llamadas = []
    monkeypatch.setattr(memoria, "liberar", lambda: llamadas.append(1))
    assert client.get("/api/health").status_code == 200
    client.get("/api/sugerido?limit=10")
    assert llamadas == []
