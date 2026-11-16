/**
 * El stock del grupo de reemplazos, abierto por sucursal (Abastecimiento, 13-11-2026).
 *
 * Una columna por cada sucursal que tiene stock de algún código del grupo, la de más
 * stock primero, y al final el total de siempre. Las sucursales sin stock no aparecen.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GrupoReemplazos, sucursalesConStock } from "@/components/grupo-reemplazos";
import type { GrupoVentas } from "@/lib/types";

const mocks = vi.hoisted(() => ({ grupoVentas: vi.fn(), consultaGrupoVentas: vi.fn() }));

vi.mock("@/lib/api-client", () => ({ api: mocks }));
vi.mock("next/link", () => ({
  default: ({ href, children, ...resto }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...resto}>{children}</a>
  ),
}));
vi.mock("recharts", async () => {
  const real = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...real,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    BarChart: () => <div />,
  };
});

const miembro = (producto: string, es_vigente: boolean, stock: Record<string, number>, cuenta = true) => ({
  producto, es_vigente, sku_ford: null, venta_12m: 10, venta_total: 20, ultimo_mes_con_venta: "202610",
  stock: Object.values(stock).reduce((a, b) => a + b, 0), stock_por_sucursal: stock,
  cuenta_en_el_total: cuenta, motivo_fuera: cuenta ? null : "no agrupado",
});

const GRUPO: GrupoVentas = {
  producto: "61 FL500S", vigente: "61 FL500S", sucursal: null,
  miembros: [
    miembro("61 FL500S", true, { LINDEROS: 300, TALCA: 59, CURICO: 0 }),
    miembro("19 AA5Z6714A", false, { TALCA: 180 }),
  ],
  meses: [], total_venta_12m: 20, total_stock: 539,
  total_stock_por_sucursal: { LINDEROS: 300, TALCA: 239, CURICO: 0 },
};

afterEach(cleanup);

describe("sucursalesConStock", () => {
  it("solo las sucursales con stock, la de más stock primero", () => {
    expect(sucursalesConStock(GRUPO)).toEqual(["LINDEROS", "TALCA"]);
  });

  it("vacío si la vista ya es de una sucursal o la API no trae el desglose", () => {
    expect(sucursalesConStock({ ...GRUPO, sucursal: "LINDEROS" })).toEqual([]);
    const sinDesglose = { ...GRUPO, miembros: GRUPO.miembros.map(({ stock_por_sucursal: _s, ...m }) => m) };
    expect(sucursalesConStock(sinDesglose)).toEqual([]);
  });
});

describe("tabla del grupo", () => {
  it("una columna por sucursal con stock, con el total del grupo abajo", async () => {
    mocks.grupoVentas.mockResolvedValue(GRUPO);
    render(<GrupoReemplazos producto="61 FL500S" />);

    const tabla = await screen.findByRole("table");
    const encabezados = within(tabla).getAllByRole("columnheader").map((th) => th.textContent);
    expect(encabezados).toEqual([
      "Código", "Código FORD", "Venta 12m", "Venta total", "Última venta",
      "LINDEROS", "TALCA", "Stock total",
    ]);
    expect(encabezados).not.toContain("CURICO");

    const fila = within(tabla).getByText("19 AA5Z6714A").closest("tr")!;
    const celdas = within(fila).getAllByRole("cell").map((td) => td.textContent);
    expect(celdas.slice(-3)).toEqual(["—", "180", "180"]);

    const pie = within(tabla).getByText("Total del grupo").closest("tr")!;
    expect(within(pie).getAllByRole("cell").map((td) => td.textContent).slice(-3))
      .toEqual(["300", "239", "539"]);
  });

  it("sin el desglose queda la columna de stock de siempre", async () => {
    mocks.grupoVentas.mockResolvedValue({ ...GRUPO, sucursal: "TALCA" });
    render(<GrupoReemplazos producto="61 FL500S" />);

    const tabla = await screen.findByRole("table");
    const encabezados = within(tabla).getAllByRole("columnheader").map((th) => th.textContent);
    expect(encabezados.at(-1)).toBe("Stock");
    expect(encabezados).not.toContain("LINDEROS");
  });
});
