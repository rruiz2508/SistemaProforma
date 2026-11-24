"""Acceso a SQLite. Todas las consultas están parametrizadas (?)."""
from __future__ import annotations

import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .formato import ahora_iso
from .validadores import (
    CAPITAL_MAX,
    ErrorValidacion,
    validar_documento,
    validar_nombre,
    validar_observaciones,
    validar_telefono,
)

# Esquema de la única tabla. Los CHECK son la "segunda barrera" de validación: aunque algún
# dato incorrecto llegara a esta capa (p. ej. desde un archivo importado), la base lo rechaza.
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


# Columnas que aporta el usuario/cálculo (el resto: id, nro_operacion y fechas, las genera el repositorio).
# Son constantes del código, nunca texto del usuario: por eso es seguro armar con ellas el SQL.
CAMPOS_DATOS = (
    "nombre_cliente", "documento", "telefono", "observaciones", "fecha_desembolso",
    "primer_vencimiento", "primer_vto_nominal", "capital", "tasa_anual", "cuotas", "iva_pct",
    "pct_gastos", "tasa_seguro", "redondeo_entero", "cuota_base_gastos", "seguro_mensual",
    "cuota_final", "total_pagar",
)


@dataclass(frozen=True)
class ResultadoImportacion:
    """Resumen de una importación: cuántas filas entraron, cuáles ya existían y cuáles se descartaron."""
    modo: str
    importadas: int
    duplicadas: int  # ya existían (mismo N° de operación, fecha y documento)
    invalidas: int  # filas descartadas por datos incorrectos
    copia_previa: Path | None = None


_CABECERA_SQLITE = b"SQLite format 3\x00"  # los primeros 16 bytes de todo archivo SQLite
_TAM_MAX_IMPORTACION = 500 * 1024 * 1024  # tope razonable para no leer archivos gigantes
_COLS_REQUERIDAS = set(CAMPOS_DATOS) | {"nro_operacion", "fecha_creacion", "fecha_actualizacion"}
_RE_NRO_OP = re.compile(r"^\d{11}$")
MSG_NO_VALIDA = "El archivo seleccionado no es una base de datos de proformas válida."


def _limpiar_fila(fila: dict) -> dict:
    """Valida y normaliza una fila de un archivo externo. Lanza ValueError/ErrorValidacion si es inválida.

    Se convierte cada valor a su tipo (int/float) en lugar de confiar en el archivo: SQLite
    acepta texto en columnas numéricas y un CHECK como `capital > 0` lo daría por válido.
    """
    d = {
        "nombre_cliente": validar_nombre(str(fila["nombre_cliente"])),
        "documento": validar_documento(str(fila["documento"])),
        "telefono": validar_telefono(str(fila["telefono"])),
        "observaciones": validar_observaciones(str(fila["observaciones"] or "")),
        "capital": int(fila["capital"]),
        "cuotas": int(fila["cuotas"]),
        "tasa_anual": float(fila["tasa_anual"]),
        "iva_pct": float(fila["iva_pct"]),
        "pct_gastos": float(fila["pct_gastos"]),
        "tasa_seguro": float(fila["tasa_seguro"]),
        "redondeo_entero": 1 if int(fila["redondeo_entero"]) else 0,
        "cuota_base_gastos": float(fila["cuota_base_gastos"]),
        "seguro_mensual": float(fila["seguro_mensual"]),
        "cuota_final": float(fila["cuota_final"]),
        "total_pagar": float(fila["total_pagar"]),
    }
    for campo in ("fecha_desembolso", "primer_vencimiento"):
        d[campo] = date.fromisoformat(str(fila[campo])).isoformat()
    nominal = fila["primer_vto_nominal"]
    d["primer_vto_nominal"] = date.fromisoformat(str(nominal)).isoformat() if nominal else None
    if not 1 <= d["capital"] <= CAPITAL_MAX or not 1 <= d["cuotas"] <= 120:
        raise ValueError("fuera de rango")
    if not (0 <= d["tasa_anual"] <= 200 and 0 <= d["iva_pct"] <= 50 and 0 <= d["pct_gastos"] <= 50
            and 0 <= d["tasa_seguro"] <= 10):
        raise ValueError("fuera de rango")
    if not all(math.isfinite(d[k]) for k in ("cuota_base_gastos", "seguro_mensual", "cuota_final", "total_pagar")):
        raise ValueError("no finito")
    for k in ("fecha_creacion", "fecha_actualizacion"):
        datetime.strptime(str(fila[k]), "%Y-%m-%d %H:%M")
        d[k] = str(fila[k])
    d["nro_operacion"] = str(fila["nro_operacion"])
    return d


class RepositorioProformas:
    """Acceso a la tabla `proformas` de SQLite.

    Todas las consultas usan parámetros (?) y las operaciones de escritura se hacen dentro de transacciones. Los errores de SQLite se traducen a `ErrorBaseDatos` con un mensaje apto para el usuario.
    """
    def __init__(self, ruta: Path | str) -> None:
        """Abre (o crea) la base de datos y garantiza que exista el esquema."""
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
        """Cierra la conexión con la base de datos."""
        self._con.close()

    # ---------------------------------------------------------------- N° operación
    def _generar_nro_operacion(self) -> str:
        """Genera el siguiente N° de operación del día: AAAAMMDD + secuencia de 3 dígitos."""
        prefijo = datetime.now().strftime("%Y%m%d")
        fila = self._con.execute(
            "SELECT MAX(nro_operacion) AS m FROM proformas WHERE nro_operacion LIKE ?",
            (prefijo + "%",),
        ).fetchone()
        ultimo = int(fila["m"][8:]) if fila["m"] else 0
        return f"{prefijo}{ultimo + 1:03d}"

    # ---------------------------------------------------------------- CRUD
    def crear(self, datos: dict) -> Proforma:
        """Inserta una proforma nueva y devuelve el registro guardado (con su id y N° de operación)."""
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
        """Actualiza todos los campos de la proforma `id_` y devuelve el registro modificado."""
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
        """Elimina la proforma `id_`. Devuelve True si existía."""
        try:
            with self._con:
                cur = self._con.execute("DELETE FROM proformas WHERE id = ?", (id_,))
        except sqlite3.Error as exc:
            raise ErrorBaseDatos("No se pudo eliminar la proforma.") from exc
        return cur.rowcount > 0

    def obtener(self, id_: int) -> Proforma | None:
        """Devuelve la proforma `id_` o None si no existe."""
        try:
            fila = self._con.execute("SELECT * FROM proformas WHERE id = ?", (id_,)).fetchone()
        except sqlite3.Error as exc:
            raise ErrorBaseDatos("No se pudo leer la proforma.") from exc
        return Proforma(**dict(fila)) if fila else None

    def listar(self, texto: str = "") -> list[Proforma]:
        """Lista las proformas (la más reciente primero), opcionalmente filtradas por `texto`.

        Busca en nombre, documento, teléfono y N° de operación. Los comodines de LIKE (% y _) escritos por el usuario se escapan para tratarlos como texto literal.
        """
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

    def importar(self, origen: Path | str, modo: str = "combinar",
                 copia_previa: Path | str | None = None) -> ResultadoImportacion:
        """Importa proformas desde un respaldo (.db) creado por esta aplicación.

        modo="combinar": agrega las que no existen, conserva las actuales.
        modo="reemplazar": borra las actuales y deja las del archivo (antes guarda `copia_previa`).
        La operación es atómica: si algo falla no se modifica la base actual.
        """
        if modo not in ("combinar", "reemplazar"):
            raise ValueError("Modo de importación desconocido.")
        origen = Path(origen)
        try:
            if not origen.is_file() or origen.stat().st_size > _TAM_MAX_IMPORTACION:
                raise ErrorBaseDatos(MSG_NO_VALIDA)
            with open(origen, "rb") as fh:
                if fh.read(16) != _CABECERA_SQLITE:
                    raise ErrorBaseDatos(MSG_NO_VALIDA)
            if origen.resolve() == Path(self.ruta).resolve():
                raise ErrorBaseDatos("El archivo seleccionado es la base de datos que ya está en uso.")
        except OSError as exc:
            raise ErrorBaseDatos("No se pudo leer el archivo seleccionado.") from exc

        # --- Paso 1: abrir el archivo SOLO LECTURA y comprobar que es un respaldo de este sistema ---
        try:
            src = sqlite3.connect(origen.resolve().as_uri() + "?mode=ro", uri=True)
        except sqlite3.Error as exc:
            raise ErrorBaseDatos(MSG_NO_VALIDA) from exc
        src.row_factory = sqlite3.Row
        try:
            try:
                if src.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ErrorBaseDatos("El archivo está dañado y no se puede importar.")
                cols = {r["name"] for r in src.execute("PRAGMA table_info(proformas)")}
                if not _COLS_REQUERIDAS <= cols:
                    raise ErrorBaseDatos(MSG_NO_VALIDA)
                filas = [dict(r) for r in src.execute("SELECT * FROM proformas ORDER BY id")]
            except sqlite3.Error as exc:
                raise ErrorBaseDatos(MSG_NO_VALIDA) from exc
        finally:
            src.close()

        # --- Paso 2: copia de seguridad previa (solo al reemplazar) ---
        previa: Path | None = None
        if modo == "reemplazar" and copia_previa is not None:
            previa = self.respaldar(copia_previa)

        # --- Paso 3: aplicar las filas en UNA transacción: si algo falla no queda nada a medias ---
        importadas = duplicadas = invalidas = 0
        try:
            with self._con:
                if modo == "reemplazar":
                    self._con.execute("DELETE FROM proformas")
                    self._con.execute("DELETE FROM sqlite_sequence WHERE name = 'proformas'")
                for fila in filas:
                    try:
                        d = _limpiar_fila(fila)
                    except (ValueError, TypeError, KeyError, OverflowError, ErrorValidacion):
                        invalidas += 1
                        continue
                    # N° de operación: si es inválido se genera uno nuevo; si ya existe y es el MISMO
                    # registro se omite (duplicado); si existe pero es otro registro (p. ej. dos
                    # máquinas crearon la operación 001 del mismo día) se le asigna un N° nuevo.
                    nro = d["nro_operacion"]
                    if not _RE_NRO_OP.match(nro):
                        nro = self._generar_nro_operacion()
                    else:
                        ex = self._con.execute(
                            "SELECT fecha_creacion, documento, nombre_cliente, capital, cuotas, total_pagar "
                            "FROM proformas WHERE nro_operacion = ?", (nro,)
                        ).fetchone()
                        if ex is not None:
                            misma = (ex["fecha_creacion"] == d["fecha_creacion"] and ex["documento"] == d["documento"]
                                     and ex["nombre_cliente"] == d["nombre_cliente"] and ex["capital"] == d["capital"]
                                     and ex["cuotas"] == d["cuotas"] and ex["total_pagar"] == d["total_pagar"])
                            if misma:
                                duplicadas += 1
                                continue
                            nro = self._generar_nro_operacion()
                    cols_ins = ("nro_operacion", "fecha_creacion", "fecha_actualizacion") + CAMPOS_DATOS
                    vals = (nro, d["fecha_creacion"], d["fecha_actualizacion"]) + tuple(d[c] for c in CAMPOS_DATOS)
                    try:
                        self._con.execute(
                            f"INSERT INTO proformas ({', '.join(cols_ins)}) VALUES ({', '.join('?' for _ in cols_ins)})",
                            vals,
                        )
                    except sqlite3.IntegrityError:
                        invalidas += 1
                        continue
                    importadas += 1
        except sqlite3.Error as exc:
            raise ErrorBaseDatos("No se pudo importar la base de datos. No se modificó nada.") from exc
        return ResultadoImportacion(modo, importadas, duplicadas, invalidas, previa)

    def respaldar(self, destino: Path | str) -> Path:
        """Copia consistente de la BD usando la API de backup de SQLite."""
        destino = Path(destino)
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            dest_con = sqlite3.connect(str(destino))
            try:
                self._con.backup(dest_con)
            finally:
                dest_con.close()
        except (sqlite3.Error, OSError) as exc:
            raise ErrorBaseDatos("No se pudo crear el respaldo.") from exc
        return destino
