"""Configuración desde variables de entorno (y archivo .env opcional)."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

def _raiz() -> Path:
    """Carpeta base donde viven `.env` y `data/`.

    Desde el código fuente es la raíz del proyecto. Dentro del ejecutable (PyInstaller) el código
    se descomprime en una carpeta temporal, así que se usa la carpeta donde está el .exe: de ese
    modo la base de datos y los PDF persisten junto al programa.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


RAIZ = _raiz()


def _cargar_dotenv(ruta: Path) -> None:
    """Carga pares CLAVE=VALOR de un .env sin pisar variables ya definidas."""
    if not ruta.is_file():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    """Configuración de la aplicación (rutas y datos institucionales que aparecen en el PDF)."""
    db_path: Path
    pdf_dir: Path
    log_path: Path
    empresa: str
    ruc: str
    direccion: str
    telefono: str


def _ruta(valor: str) -> Path:
    """Convierte una ruta relativa en absoluta respecto de la raíz del proyecto."""
    p = Path(valor)
    return p if p.is_absolute() else RAIZ / p


def cargar_config() -> Config:
    """Lee las variables PROFORMAS_* (y el archivo .env si existe) y devuelve la configuración.

    Todas tienen valores por defecto, así que la aplicación funciona sin .env.
    """
    _cargar_dotenv(RAIZ / ".env")
    env = os.environ.get
    return Config(
        db_path=_ruta(env("PROFORMAS_DB_PATH", "data/proformas.db")),
        pdf_dir=_ruta(env("PROFORMAS_PDF_DIR", "data/pdf")),
        log_path=_ruta(env("PROFORMAS_LOG_PATH", "data/app.log")),
        empresa=env("PROFORMAS_EMPRESA", "FUNDACIÓN INDUSTRIAL"),
        ruc=env("PROFORMAS_RUC", "80011774-3"),
        direccion=env("PROFORMAS_DIRECCION", "Senador Long N°625 c/ Lillo"),
        telefono=env("PROFORMAS_TELEFONO", "(021) 605 700"),
    )
