"""Acceso a SQLite. Todas las consultas están parametrizadas (?)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .formato import ahora_iso

ESQUEMA = """
CREATE TABLE IF NOT EXISTS proformas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nro_operacion TEXT NOT NULL UNIQUE,
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT NOT NULL,
    nombre_cliente TEXT NOT NULL CHECK (length(trim(nombre_cliente)) > 0),
    documento TEXT NOT NULL CHECK (length(trim(documento)) > 0),
    telefono TEXT NOT NULL CHECK (length(trim(telefono)) > 0),
    observaciones TEXT NOT NULL DEFAULT '',
    fecha_desembolso TEXT NOT NULL,
    primer_vencimiento TEXT NOT NULL,
    primer_vto_nominal TEXT,
    capital INTEGER NOT NULL CHECK (capital > 0),
    tasa_anual REAL NOT NULL CHECK (tasa_anual >= 0),
    cuotas INTEGER NOT NULL CHECK (cuotas BETWEEN 1 AND 120),
    iva_pct REAL NOT NULL CHECK (iva_pct >= 0),
    pct_gastos REAL NOT NULL CHECK (pct_gastos >= 0),
    tasa_seguro REAL NOT NULL CHECK (tasa_seguro >= 0),
    redondeo_entero INTEGER NOT NULL DEFAULT 1 CHECK (redondeo_entero IN (0, 1)),
    cuota_base_gastos REAL NOT NULL,
    seguro_mensual REAL NOT NULL,
    cuota_final REAL NOT NULL,
    total_pagar REAL NOT NULL
);
"""


class ErrorBaseDatos(Exception):
    """Error de persistencia con mensaje apto para el usuario."""


@dataclass(frozen=True)
class Proforma:
    """Registro guardado."""

    id: int
    nro_operacion: str
    fecha_creacion: str
    fecha_actualizacion: str
    nombre_cliente: str
    documento: str
    telefono: str
    observaciones: str
    fecha_desembolso: str
    primer_vencimiento: str
    primer_vto_nominal: str | None
    capital: int
    tasa_anual: float
    cuotas: int
    iva_pct: float
    pct_gastos: float
    tasa_seguro: float
    redondeo_entero: int
    cuota_base_gastos: float
    seguro_mensual: float
    cuota_final: float
    total_pagar: float


CAMPOS_DATOS = (
    "nombre_cliente", "documento", "telefono", "observaciones", "fecha_desembolso",
    "primer_vencimiento", "primer_vto_nominal", "capital", "tasa_anual", "cuotas", "iva_pct",
    "pct_gastos", "tasa_seguro", "redondeo_entero", "cuota_base_gastos", "seguro_mensual",
    "cuota_final", "total_pagar",
)


class RepositorioProformas:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)
        try:
            if self.ruta != ":memory:":
                Path(self.ruta).parent.mkdir(parents=True, exist_ok=True)
            self._con = sqlite3.connect(self.ruta)
            self._con.row_factory = sqlite3.Row
            self._con.execute("PRAGMA foreign_keys = ON")
            self._con.executescript(ESQUEMA)
            self._con.commit()
        except (sqlite3.Error, OSError) as exc:
            raise ErrorBaseDatos("No se pudo abrir la base de datos.") from exc

    def cerrar(self) -> None:
        self._con.close()

    # ---------------------------------------------------------------- N° operación
    def _generar_nro_operacion(self) -> str:
        prefijo = datetime.now().strftime("%Y%m%d")
        fila = self._con.execute(
            "SELECT MAX(nro_operacion) AS m FROM proformas WHERE nro_operacion LIKE ?",
            (prefijo + "%",),
        ).fetchone()
        ultimo = int(fila["m"][8:]) if fila["m"] else 0
        return f"{prefijo}{ultimo + 1:03d}"

    # ---------------------------------------------------------------- CRUD
    def crear(self, datos: dict) -> Proforma:
        ahora = ahora_iso()
        try:
            with self._con:
                nro = self._generar_nro_operacion()
                cols = ("nro_operacion", "fecha_creacion", "fecha_actualizacion") + CAMPOS_DATOS
                valores = (nro, ahora, ahora) + tuple(datos[c] for c in CAMPOS_DATOS)
                marcadores = ", ".join("?" for _ in cols)
                cur = self._con.execute(
                    f"INSERT INTO proformas ({', '.join(cols)}) VALUES ({marcadores})", valores
                )  # nombres de columnas fijos (constantes), valores parametrizados
                nuevo_id = cur.lastrowid
        except (sqlite3.Error, KeyError) as exc:
            raise ErrorBaseDatos("No se pudo guardar la proforma. Verifique los datos e intente nuevamente.") from exc
        return self.obtener(nuevo_id)  # type: ignore[arg-type]

    def actualizar(self, id_: int, datos: dict) -> Proforma:
        try:
            with self._con:
                asignaciones = ", ".join(f"{c} = ?" for c in CAMPOS_DATOS)
                cur = self._con.execute(
                    f"UPDATE proformas SET {asignaciones}, fecha_actualizacion = ? WHERE id = ?",
                    tuple(datos[c] for c in CAMPOS_DATOS) + (ahora_iso(), id_),
                )
                if cur.rowcount == 0:
                    raise ErrorBaseDatos("La proforma ya no existe.")
        except (sqlite3.Error, KeyError) as exc:
            raise ErrorBaseDatos("No se pudo actualizar la proforma. Intente nuevamente.") from exc
        return self.obtener(id_)  # type: ignore[arg-type]

    def eliminar(self, id_: int) -> bool:
        try:
            with self._con:
                cur = self._con.execute("DELETE FROM proformas WHERE id = ?", (id_,))
        except sqlite3.Error as exc:
            raise ErrorBaseDatos("No se pudo eliminar la proforma.") from exc
        return cur.rowcount > 0

    def obtener(self, id_: int) -> Proforma | None:
        try:
            fila = self._con.execute("SELECT * FROM proformas WHERE id = ?", (id_,)).fetchone()
        except sqlite3.Error as exc:
            raise ErrorBaseDatos("No se pudo leer la proforma.") from exc
        return Proforma(**dict(fila)) if fila else None

    def listar(self, texto: str = "") -> list[Proforma]:
        t = texto.strip().lower()
        try:
            if not t:
                filas = self._con.execute("SELECT * FROM proformas ORDER BY id DESC").fetchall()
            else:
                patron = "%" + t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
                filas = self._con.execute(
                    """SELECT * FROM proformas
                       WHERE lower(nombre_cliente) LIKE ? ESCAPE '\\'
                          OR lower(documento) LIKE ? ESCAPE '\\'
                          OR lower(telefono) LIKE ? ESCAPE '\\'
                          OR nro_operacion LIKE ? ESCAPE '\\'
                       ORDER BY id DESC""",
                    (patron,) * 4,
                ).fetchall()
        except sqlite3.Error as exc:
            raise ErrorBaseDatos("No se pudo consultar la base de datos.") from exc
        return [Proforma(**dict(f)) for f in filas]

    def respaldar(self, destino: Path | str) -> Path:
        """Copia consistente de la BD usando la API de backup de SQLite."""
        destino = Path(destino)
        try:
            dest_con = sqlite3.connect(str(destino))
            try:
                self._con.backup(dest_con)
            finally:
                dest_con.close()
        except (sqlite3.Error, OSError) as exc:
            raise ErrorBaseDatos("No se pudo crear el respaldo.") from exc
        return destino
