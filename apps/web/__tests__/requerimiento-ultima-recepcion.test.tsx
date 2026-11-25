/**
 * Requerimiento de sucursal: la última recepción de la empresa (12 meses) y, desde
 * "Nacional", el stock y la última recepción de cada sucursal (Abastecimiento, 24-11-2026).
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import RequerimientoPage from "@/app/requerimiento/page";

const mocks = vi.hoisted(() => ({
  sucursales: vi.fn(),
  analizarRequerimiento: vi.fn(),
  archivoPortal: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({ api: mocks }));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));

const linea = (producto: string, emp: string | null, por_sucursal: unknown[], nacional = 2,
               reemplazos: string | null = null) => ({
  producto, texto_original: producto, cantidad: 1, estado: "sin_venta_local", duplicado: false,
  descripcion: "REPUESTO", proveedor: "FORD", costo_unitario: 1000, reemplazos,
  nombre_sucursal: "Linderos", stock_sucursal: 0, stock_nacional: nacional, meses_con_venta_3m: null,
  meses_con_venta_6m: null, meses_con_venta_12m: null, venta_mensual: null, venta_12m: null,
  clasificacion_abc: null, stock_cd: null, total_sugerido_suc: null, frecuencia_otra_sucursal: null,
  transito_sucursal: null, transito_nacional: null, transito_pedido_desde: null,
  ult_recepcion_empresa: emp, por_sucursal,
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

async function analizar(lineas: unknown[]) {
  mocks.sucursales.mockResolvedValue([{ sucursal_id: "LINDEROS", nombre: "Linderos" }]);
  mocks.analizarRequerimiento.mockResolvedValue({
    lineas, resumen: { total: lineas.length, en_sugerido: 0, sin_venta_local: lineas.length, no_existe: 0, duplicados: 0 },
  });
  render(<RequerimientoPage />);
  await screen.findByRole("option", { name: "Linderos" });
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "LINDEROS" } });
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "19 F2GZ19G490A" } });
  fireEvent.click(screen.getByRole("button", { name: /Analizar la lista/ }));
  return screen.findByRole("table");
}

describe("Requerimiento: última recepción", () => {
  it("una sola columna con la fecha de la empresa, después de Nacional", async () => {
    const tabla = await analizar([
      linea("19 F2GZ19G490A", "2026-10-23", []),
      linea("61 FL500S", null, []),
    ]);
    const cab = within(tabla).getAllByRole("columnheader").map((c) => c.textContent);
    const i = cab.indexOf("Últ. recepción");
    expect(i).toBe(cab.indexOf("Nacional") + 1);
    expect(cab).not.toContain("Últ. recepción acá");

    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(within(filas[0]).getAllByRole("cell")[i].textContent).toBe("23-10-2026");
    expect(within(filas[1]).getAllByRole("cell")[i].textContent).toBe("—");
  });

  it("Nacional despliega el stock y la última recepción de cada sucursal", async () => {
    await analizar([
      linea("19 F2GZ19G490A", "2026-10-23", [
        { sucursal_id: "CURICO", stock: 1, ult_recepcion: "2026-10-23" },
        { sucursal_id: "TALCA", stock: 1, ult_recepcion: null },
        { sucursal_id: "DESCONOCIDO", stock: 0, ult_recepcion: "2026-09-01" },
      ]),
    ]);
    const boton = screen.getByRole("button", { name: /2/, expanded: false });
    fireEvent.click(boton);

    const tablas = screen.getAllByRole("table");
    const desglose = tablas[tablas.length - 1];
    const filas = within(desglose).getAllByRole("row").map((f) =>
      within(f).queryAllByRole("cell").map((c) => c.textContent));
    expect(filas.slice(1)).toEqual([
      ["CURICO", "1", "23-10-2026"],
      ["TALCA", "1", "—"],
      ["Importación (sin sucursal)", "0", "01-09-2026"],
      ["Total", "2", "23-10-2026"],
    ]);

    fireEvent.click(screen.getByRole("button", { name: /2/, expanded: true }));
    expect(screen.getAllByRole("table")).toHaveLength(1);
  });

  it("sin desglose, Nacional es solo el número", async () => {
    await analizar([linea("19 X", null, [], 0)]);
    expect(screen.queryByRole("button", { expanded: false })).not.toBeInTheDocument();
  });

  it("con reemplazos, cada código con su stock y su última recepción, y el total del grupo",
     async () => {
    await analizar([{
      ...linea("61 FL500S", "2026-11-19", [
        { sucursal_id: "CD REPUESTOS", stock: 137, stock_reemplazos: 283,
          stock_por_codigo: { "61 LB542": 282, "19 AA5Z6714A": 1 }, ult_recepcion: "2026-11-19",
          recepcion_por_codigo: { "61 FL500S": "2026-11-01", "61 LB542": "2026-11-19" } },
        { sucursal_id: "TALCA", stock: 0, stock_reemplazos: 37,
          stock_por_codigo: { "19 AA5Z6714A": 37 }, ult_recepcion: "2026-11-15",
          recepcion_por_codigo: { "19 AA5Z6714A": "2026-11-15" } },
      ], 137, "19 AA5Z6714A, 61 LB542"),
      codigos_reemplazo: ["19 AA5Z6714A", "61 LB542"],
    }]);
    fireEvent.click(screen.getByRole("button", { name: /137/, expanded: false }));

    const tablas = screen.getAllByRole("table");
    const desglose = tablas[tablas.length - 1];
    const cab = within(desglose).getAllByRole("columnheader").map((c) => c.textContent);
    const fecha = "Últ. recepción (12 meses)";
    expect(cab).toEqual(["Sucursal", "61 FL500S", "19 AA5Z6714A", "61 LB542", "Total stock",
                         "Stock", fecha, "Stock", fecha, "Stock", fecha]);
    const filas = within(desglose).getAllByRole("row").slice(2).map((f) =>
      within(f).queryAllByRole("cell").map((c) => c.textContent));
    expect(filas).toEqual([
      ["CD REPUESTOS", "137", "01-11-2026", "1", "—", "282", "19-11-2026", "420"],
      ["TALCA", "0", "—", "37", "15-11-2026", "0", "—", "37"],
      ["Total", "137", "01-11-2026", "38", "15-11-2026", "282", "19-11-2026", "457"],
    ]);
  });

  it("con una API anterior (sin stock por código), los reemplazos van sumados", async () => {
    await analizar([
      linea("61 FL500S", "2026-11-19", [
        { sucursal_id: "CD REPUESTOS", stock: 137, stock_reemplazos: 283, ult_recepcion: "2026-11-19" },
      ], 137, "19 AA5Z6714A, 61 LB542"),
    ]);
    fireEvent.click(screen.getByRole("button", { name: /137/, expanded: false }));
    const tablas = screen.getAllByRole("table");
    const cab = within(tablas[tablas.length - 1]).getAllByRole("columnheader").map((c) => c.textContent);
    expect(cab).toEqual(["Sucursal", "61 FL500S", "Reemplazos", "Total", "Últ. recepción (12 meses)"]);
  });
});
