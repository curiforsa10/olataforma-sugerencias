"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { formatoNumero } from "@/lib/formato";
import type { StockSucursalRow } from "@/lib/types";

/**
 * Stock de un codigo por sucursal (varias bodegas de una sucursal se suman), solo las
 * que tienen stock, la de mas stock primero. Mismo criterio que la tabla del historial
 * de reemplazos, para que las dos se lean igual.
 */
export function stockPorSucursal(filas: StockSucursalRow[]): [string, number][] {
  const total: Record<string, number> = {};
  for (const f of filas) {
    if (!(f.stock > 0)) continue;
    const s = f.sucursal_id || "SIN SUCURSAL";
    total[s] = (total[s] ?? 0) + f.stock;
  }
  return Object.entries(total).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

/**
 * El stock del codigo en todas las sucursales, cuando el codigo NO tiene reemplazos.
 *
 * El historial de reemplazos ya muestra el stock por sucursal, pero desaparece si el
 * codigo esta solo, y en el detalle del sugerido el comprador se quedaba sin ver donde
 * hay stock del producto (Abastecimiento, 24-11-2026). Va en el mismo lugar y con el
 * mismo formato: una fila, una columna por sucursal con stock y el total al final.
 */
export function StockPorSucursalCodigo({ producto }: { producto: string }) {
  const [filas, setFilas] = useState<StockSucursalRow[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let activo = true;
    setError(false);
    setFilas(null);
    api
      .catalogoDetalle(producto)
      .then((d) => activo && setFilas(d.stock_por_sucursal ?? []))
      .catch(() => activo && setError(true));
    return () => {
      activo = false;
    };
  }, [producto]);

  // Si no se pudo leer, no se muestra nada: decir "sin stock" seria inventar.
  if (error || filas === null) return null;

  const sucursales = stockPorSucursal(filas);
  const total = sucursales.reduce((a, [, c]) => a + c, 0);

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle>Stock por sucursal</CardTitle>
        <p className="text-[12px] text-slate-500">
          Este código no tiene reemplazos: es su stock en todas las sucursales.
        </p>
      </CardHeader>
      <CardContent>
        {sucursales.length === 0 ? (
          <p className="text-sm text-slate-500">Este código no tiene stock en ninguna sucursal.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Código</th>
                  {sucursales.map(([s]) => (
                    <th key={s} className="whitespace-nowrap px-3 py-2 text-right">
                      {s}
                    </th>
                  ))}
                  <th className="px-3 py-2 text-right">Stock total</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-[12px] text-slate-700">{producto}</td>
                  {sucursales.map(([s, c]) => (
                    <td key={s} className="px-3 py-2 text-right tabular-nums">
                      {formatoNumero(c)}
                    </td>
                  ))}
                  <td className="px-3 py-2 text-right font-semibold tabular-nums">
                    {formatoNumero(total)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
