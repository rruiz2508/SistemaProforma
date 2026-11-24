"""Validación y normalización de entradas (lista blanca). Sin dependencias de UI."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from .formato import formatear_documento

CAPITAL_MAX = 100_000_000_000
CUOTAS_MIN, CUOTAS_MAX = 1, 120
OBS_MAX = 300
NOMBRE_MAX = 120

_RE_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .,'&()/\-]+$")
_RE_TELEFONO = re.compile(r"^[0-9 +\-()]+$")
_RE_CI = re.compile(r"^(\d{1,3}(\.\d{3})+|\d{4,12})(-\d)?$")
_RE_PASAPORTE = re.compile(r"^[A-Za-z0-9]{6,12}$")
_RE_DECIMAL = re.compile(r"^\d+(\.\d+)?$")


class ErrorValidacion(ValueError):
    """Entrada inválida. `campo` identifica el campo; `mensaje` es apto para el usuario."""

    def __init__(self, campo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.campo = campo
        self.mensaje = mensaje


def _cap(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def validar_nombre(texto: str) -> str:
    t = (texto or "").strip()
    if not t:
        raise ErrorValidacion("nombre", "Ingrese el nombre o razón social del cliente.")
    if len(t) < 3:
        raise ErrorValidacion("nombre", "El nombre es demasiado corto (mínimo 3 caracteres).")
    if len(t) > NOMBRE_MAX:
        raise ErrorValidacion("nombre", f"El nombre no puede superar {NOMBRE_MAX} caracteres.")
    if not _RE_NOMBRE.match(t):
        raise ErrorValidacion("nombre", "El nombre contiene caracteres no permitidos.")
    return " ".join(t.split())


def validar_documento(texto: str) -> str:
    t = (texto or "").strip()
    if not t:
        raise ErrorValidacion("documento", "Ingrese el Nro. de Documento / C.I.")
    if any(c.isalpha() for c in t):
        if not _RE_PASAPORTE.match(t):
            raise ErrorValidacion("documento", "Pasaporte inválido: 6 a 12 letras o números, sin símbolos.")
        return t.upper()
    if not _RE_CI.match(t):
        raise ErrorValidacion("documento", "Documento inválido. Ejemplos: 4.567.890 o 4.567.890-1.")
    cuerpo = t.split("-")[0].replace(".", "")
    if not (4 <= len(cuerpo) <= 12) or int(cuerpo) == 0:
        raise ErrorValidacion("documento", "El número de documento no es válido.")
    return formatear_documento(t)


def validar_telefono(texto: str) -> str:
    t = (texto or "").strip()
    if not t:
        raise ErrorValidacion("telefono", "Ingrese un teléfono de contacto.")
    if not _RE_TELEFONO.match(t):
        raise ErrorValidacion("telefono", "El teléfono solo puede tener números, espacios, +, - y paréntesis.")
    digitos = re.sub(r"\D", "", t)
    if not 6 <= len(digitos) <= 15:
        raise ErrorValidacion("telefono", "El teléfono debe tener entre 6 y 15 dígitos.")
    if len(set(digitos)) == 1:
        raise ErrorValidacion("telefono", "El teléfono no es válido (dígitos repetidos).")
    return " ".join(t.split())


def validar_observaciones(texto: str) -> str:
    t = (texto or "").strip()
    if len(t) > OBS_MAX:
        raise ErrorValidacion("observaciones", f"Las observaciones no pueden superar {OBS_MAX} caracteres.")
    if not all(c.isprintable() or c in "\n\t" for c in t):
        raise ErrorValidacion("observaciones", "Las observaciones contienen caracteres no permitidos.")
    return t


def validar_capital(texto: str) -> int:
    t = str(texto).replace(".", "").replace(" ", "")
    if not t:
        raise ErrorValidacion("capital", "Ingrese el capital solicitado.")
    if not (t.isascii() and t.isdigit()):
        raise ErrorValidacion("capital", "El capital solo admite números positivos.")
    valor = int(t)
    if valor <= 0:
        raise ErrorValidacion("capital", "El capital debe ser mayor a cero.")
    if valor > CAPITAL_MAX:
        tope = f"{CAPITAL_MAX:,}".replace(",", ".")
        raise ErrorValidacion("capital", f"El capital no puede superar Gs. {tope}.")
    return valor


def validar_cuotas(texto: str) -> int:
    t = str(texto).strip()
    if not t:
        raise ErrorValidacion("cuotas", "Ingrese la cantidad de cuotas.")
    if not (t.isascii() and t.isdigit()):
        raise ErrorValidacion("cuotas", "Las cuotas deben ser un número entero.")
    valor = int(t)
    if not CUOTAS_MIN <= valor <= CUOTAS_MAX:
        raise ErrorValidacion("cuotas", f"Las cuotas deben estar entre {CUOTAS_MIN} y {CUOTAS_MAX}.")
    return valor


def validar_decimal(campo: str, etiqueta: str, texto: str, minimo: float, maximo: float) -> float:
    t = str(texto).strip().replace(",", ".")
    if not t:
        raise ErrorValidacion(campo, f"Ingrese {etiqueta}.")
    if not (t.isascii() and _RE_DECIMAL.match(t)):
        raise ErrorValidacion(campo, f"{_cap(etiqueta)} solo admite números (no negativos).")
    valor = Decimal(t)
    if not Decimal(str(minimo)) <= valor <= Decimal(str(maximo)):
        raise ErrorValidacion(campo, f"{_cap(etiqueta)} debe estar entre {minimo} y {maximo}.")
    return float(valor)


def validar_fecha(campo: str, etiqueta: str, texto: str) -> date:
    t = (texto or "").strip()
    if not t:
        raise ErrorValidacion(campo, f"Ingrese {etiqueta}.")
    try:
        d = datetime.strptime(t, "%d/%m/%Y").date()
    except ValueError:
        raise ErrorValidacion(campo, f"{_cap(etiqueta)} no es una fecha válida (use DD/MM/AAAA).") from None
    if not 2000 <= d.year <= 2100:
        raise ErrorValidacion(campo, f"{_cap(etiqueta)} debe estar entre los años 2000 y 2100.")
    return d
