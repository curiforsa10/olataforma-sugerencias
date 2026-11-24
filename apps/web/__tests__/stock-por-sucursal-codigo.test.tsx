/**
 * Sin reemplazos, el detalle del sugerido igual muestra el stock del código en todas
 * las sucursales (Abastecimiento, 24-11-2026).
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GrupoReemplazos } from "@/components/grupo-reemplazos";
import { StockPorSucursalCodigo, stockPorSucursal } from "@/components/stock-por-sucursal-codigo";

const mocks = vi.hoisted(() => ({
  grupoVentas: vi.fn(),
  consultaGrupoVentas: vi.fn(),
  catalogoDetalle: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({ api: mocks }));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}));

const fila = (sucursal_id: string | null, stock: number, bodega = "B1") => ({
  sucursal_id, stock, bodega, origen: "CURIFOR",
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("stockPorSucursal", () => {
  it("suma las bodegas de una sucursal, deja fuera las sin stock y ordena de mayor a menor", () => {
    expect(
      stockPorSucursal([fila("TALCA", 2), fila("LINDEROS", 3), fila("TALCA", 4, "B2"), fila("CURICO", 0)]),
    ).toEqual([["TALCA", 6], ["LINDEROS", 3]]);
  });
});

describe("StockPorSucursalCodigo", () => {
  it("una columna por sucursal con stock y el total", async () => {
    mocks.catalogoDetalle.mockResolvedValue({
      stock_por_sucursal: [fila("CHILLAN", 1), fila("LINDEROS", 5), fila("RANCAGUA", 0)],
    });
    render(<StockPorSucursalCodigo producto="25 JB3Z6477E" />);

    const tabla = await screen.findByRole("table");
    const cab = within(tabla).getAllByRole("columnheader").map((c) => c.textContent);
    expect(cab).toEqual(["Código", "LINDEROS", "CHILLAN", "Stock total"]);
    const celdas = within(tabla).getAllByRole("cell").map((c) => c.textContent);
    expect(celdas).toEqual(["25 JB3Z6477E", "5", "1", "6"]);
  });

  it("dice que no hay stock cuando ninguna sucursal tiene", async () => {
    mocks.catalogoDetalle.mockResolvedValue({ stock_por_sucursal: [fila("TALCA", 0)] });
    render(<StockPorSucursalCodigo producto="X" />);
    expect(await screen.findByText(/no tiene stock en ninguna sucursal/)).toBeInTheDocument();
  });

  it("si no se pudo leer, no muestra nada", async () => {
    mocks.catalogoDetalle.mockRejectedValue(new Error("404"));
    const { container } = render(<StockPorSucursalCodigo producto="X" />);
    await new Promise((r) => setTimeout(r, 0));
    expect(container).toBeEmptyDOMElement();
  });
});

describe("en el detalle del sugerido", () => {
  it("sin reemplazos aparece el stock por sucursal", async () => {
    mocks.grupoVentas.mockResolvedValue({ producto: "X", miembros: [], meses: [] });
    mocks.catalogoDetalle.mockResolvedValue({ stock_por_sucursal: [fila("TALCA", 2)] });
    render(<GrupoReemplazos producto="X" alternativa={<StockPorSucursalCodigo producto="X" />} />);
    expect(await screen.findByText("Stock por sucursal")).toBeInTheDocument();
    expect(screen.queryByText("Historial de reemplazos")).not.toBeInTheDocument();
  });
});
