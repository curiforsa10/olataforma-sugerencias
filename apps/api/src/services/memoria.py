"""Devolverle al sistema la memoria que ya se libero, despues de cada paso pesado.

Render corre la API en Linux con 512 MB. La publicacion del motor son mas de diez
POST seguidos (sugerido, stock, transito, precios, reemplazos...) y cada uno arma
decenas de MB que despues suelta. Python los libera, pero el asignador de memoria
de Linux (glibc) se los queda reservados, repartidos en varias "arenas" (una por
hilo del pool de FastAPI), y el proceso crece paso a paso aunque cada paso ya
termino. El 09-11-2026, con la carga del sugerido ya aligerada, Render corto por
memoria a las 16:42 en los reemplazos, un paso chico que llego con lo acumulado.

Dos medidas, solo en Linux (en Windows y macOS no hacen nada):
- `limitar_arenas()`: dos arenas como maximo en vez de una por hilo
  (`mallopt(M_ARENA_MAX, 2)`, lo mismo que la variable MALLOC_ARENA_MAX).
- `liberar()`: recolecta la basura de Python y le pide a glibc que devuelva al
  sistema lo que quedo libre (`malloc_trim(0)`). Se llama despues de cada paso
  pesado (ver `es_paso_pesado`).
"""
from __future__ import annotations

import ctypes
import gc
import sys

_M_ARENA_MAX = -8
_libc = None


def _glibc():
    global _libc
    if _libc is None:
        _libc = False
        if sys.platform.startswith("linux"):
            try:
                _libc = ctypes.CDLL("libc.so.6")
            except OSError:
                _libc = False
    return _libc or None


def limitar_arenas(maximo: int = 2) -> bool:
    """True si quedo aplicado. Rige para las arenas que se creen despues, por eso
    se llama al importar la app, antes de que arranque el pool de hilos."""
    libc = _glibc()
    if libc is None:
        return False
    try:
        return bool(libc.mallopt(_M_ARENA_MAX, maximo))
    except AttributeError:
        return False


def liberar() -> None:
    gc.collect()
    libc = _glibc()
    if libc is not None:
        try:
            libc.malloc_trim(0)
        except AttributeError:
            pass


# Los POST que manda el motor al publicar y los que suben o recalculan tablas
# enteras. Los GET de la web no: son muchos, chicos, y una recoleccion en cada uno
# costaria mas de lo que devuelve.
_PREFIJOS_PESADOS = ("/api/admin/", "/api/precios/", "/api/requerimiento/sku-proveedor")


def es_paso_pesado(metodo: str, ruta: str) -> bool:
    return metodo == "POST" and ruta.startswith(_PREFIJOS_PESADOS)
