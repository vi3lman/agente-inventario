"""Inventario de ejemplo guardado en SQLite.

Simula los datos que un agente consultaría en un ERP (por ejemplo, SAP
Business One): artículos con su stock y los pedidos de compra creados.
"""

import sqlite3

ARTICULOS_INICIALES = [
    ("A100", "Notebook 14 pulgadas", 42, 4_500_000),
    ("A200", "Monitor 24 pulgadas", 0, 1_200_000),
    ("B300", "Teclado mecánico", 15, 450_000),
    ("B310", "Teclado inalámbrico", 3, 280_000),
    ("C400", "Mouse inalámbrico", 120, 150_000),
]
"""list[tuple]: Código, descripción, stock y precio en guaraníes."""


class ArticuloNoEncontradoError(Exception):
    """El código no corresponde a ningún artículo."""


class Inventario:
    """Acceso a los artículos y pedidos.

    Args:
        ruta (str): Archivo de la base. ``":memory:"`` crea una base temporal,
            útil para los tests.
    """

    def __init__(self, ruta=":memory:"):
        self.conexion = sqlite3.connect(ruta)
        self.conexion.row_factory = sqlite3.Row
        self._crear_tablas()

    def _crear_tablas(self):
        with self.conexion:
            self.conexion.executescript(
                """
                CREATE TABLE IF NOT EXISTS articulos (
                    codigo TEXT PRIMARY KEY,
                    descripcion TEXT NOT NULL,
                    stock INTEGER NOT NULL CHECK (stock >= 0),
                    precio_pyg INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT NOT NULL REFERENCES articulos (codigo),
                    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
                    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self.conexion.executemany(
                "INSERT OR IGNORE INTO articulos VALUES (?, ?, ?, ?)", ARTICULOS_INICIALES
            )

    def consultar_stock(self, codigo):
        """Devuelve el artículo con su stock.

        Raises:
            ArticuloNoEncontradoError: Si el código no existe.
        """
        fila = self.conexion.execute(
            "SELECT * FROM articulos WHERE codigo = ?", (codigo.strip().upper(),)
        ).fetchone()
        if fila is None:
            raise ArticuloNoEncontradoError(f"No existe el artículo {codigo}.")
        return dict(fila)

    def buscar_articulos(self, texto):
        """Busca artículos cuya descripción contenga el texto, sin importar mayúsculas."""

        filas = self.conexion.execute(
            "SELECT * FROM articulos WHERE descripcion LIKE ? ORDER BY codigo",
            (f"%{texto.strip()}%",),
        ).fetchall()
        return [dict(fila) for fila in filas]

    def crear_pedido(self, codigo, cantidad):
        """Registra un pedido de compra para reponer un artículo.

        Raises:
            ArticuloNoEncontradoError: Si el código no existe.
            ValueError: Si la cantidad no es positiva.
        """
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero.")
        articulo = self.consultar_stock(codigo)
        with self.conexion:
            cursor = self.conexion.execute(
                "INSERT INTO pedidos (codigo, cantidad) VALUES (?, ?)",
                (articulo["codigo"], cantidad),
            )
        return {"id_pedido": cursor.lastrowid, "codigo": articulo["codigo"], "cantidad": cantidad}

    def pedidos(self):
        """Lista los pedidos creados, del más reciente al más antiguo."""

        filas = self.conexion.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
        return [dict(fila) for fila in filas]
