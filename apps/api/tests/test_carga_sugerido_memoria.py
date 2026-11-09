"""La carga del sugerido procesa el archivo fila a fila y da lo mismo que antes.

`procesar_filas` reemplaza en `cargar_sugerido` a armar la lista de filas crudas,
un dict por fila y recien ahi `procesar_registros`: esas tres copias juntas pasaban
los 512 MB de Render con el CSV del motor. Estos tests fijan que el resultado es
identico al del camino anterior, tambien en los casos raros de `dict(zip(...))`.
"""
import io

from openpyxl import Workbook

from src.services import excel_loader as el


def _como_antes(headers, rows):
    return el.procesar_registros([dict(zip(headers, r)) for r in rows])


def _csv(texto: str) -> bytes:
    return texto.encode("utf-8-sig")


CASOS = {
    "normal": (["Producto", "SucursalID", "Total Sugerido Suc", "Columna rara"],
               [["13 A", "LINDEROS", "5", "x"], ["13 B", "TALCA", "0", "y"]]),
    "cabecera repetida": (["Producto", "SucursalID", "Producto"],
                          [["13 A", "LINDEROS", "13 Z"], ["13 B", "TALCA"]]),
    "fila corta y larga": (["Producto", "SucursalID", "Costo Unitario"],
                           [["13 A"], ["13 B", "TALCA", "100", "sobra"]]),
    "todas cortas": (["Producto", "SucursalID", "Costo Unitario", "Columna rara"],
                     [["13 A", "LINDEROS"]]),
    "cabecera vacia": (["Producto", "", "SucursalID"], [["13 A", "?", "LINDEROS"]]),
    "sin filas": (["Producto", "SucursalID"], []),
}


def test_da_lo_mismo_que_armar_un_dict_por_fila():
    for nombre, (headers, rows) in CASOS.items():
        assert el.procesar_filas(headers, iter(rows)) == _como_antes(headers, rows), nombre


def test_el_csv_se_lee_igual_que_antes():
    for contenido in (
        _csv('Producto;SucursalID;Descripcion\n13 A;LINDEROS;"FILTRO 15"" X"\n13 B;TALCA;\n'),
        # Fin de linea de Windows, salto de linea dentro de un campo y una letra
        # que no es UTF-8: se tienen que leer igual que con el texto entero.
        _csv('Producto,SucursalID,Descripcion\r\n13 A,LINDEROS,"dos\r\nlineas"\r\n') + b"13 B,TALCA,\xe9\r\n",
        b"Producto,SucursalID\n13 A,LINDEROS",
    ):
        headers, rows = el._rows_from_csv(contenido)
        h2, it = el._iter_filas_csv(contenido)
        assert (h2, list(it)) == (headers, rows), contenido


def test_el_excel_se_lee_igual_que_antes():
    wb = Workbook()
    ws = wb.active
    ws.append(["Producto", "SucursalID", None, "Total Sugerido Suc"])
    ws.append(["13 A", "LINDEROS", None, 4])
    ws.append(["13 B", "TALCA", "x", None])
    buf = io.BytesIO()
    wb.save(buf)
    headers, rows = el._rows_from_xlsx(buf.getvalue())
    h2, it = el._iter_filas_xlsx(buf.getvalue())
    assert (h2, [list(r) for r in it]) == (headers, rows)


def test_un_csv_vacio_no_rompe():
    headers, it = el._iter_filas_csv(b"")
    assert headers == [] and list(it) == []


def test_la_carga_completa_guarda_las_mismas_filas(db_session):
    contenido = _csv("Producto,SucursalID,Total Sugerido Suc,Costo Unitario\n"
                     "13 A,LINDEROS,5,100\n13 B,LINDEROS,0,50\n")
    resumen = el.cargar_sugerido(db_session, "sugerido.csv", contenido)
    assert resumen["filas_cargadas"] == 2
    assert "Producto -> producto" in resumen["columnas_detectadas"]
