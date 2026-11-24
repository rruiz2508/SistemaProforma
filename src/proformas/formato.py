"""Formato de montos, fechas y documentos."""
from __future__ import annotations

from datetime import date, datetime


def miles(valor: float | int, decimales: int = 0) -> str:
    """1234567.5 -> '1.234.568' (decimales=0) o '1.234.567,50' (decimales=2)."""
    texto = f"{float(valor):,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def gs(valor: float | int, decimales: int = 0) -> str:
    """Formato de guaraníes: 1234567 -> 'Gs. 1.234.567'."""
    return f"Gs. {miles(valor, decimales)}"


def porcentaje(valor: float, decimales: int = 2) -> str:
    """Formato de porcentaje con coma decimal: 26.8 -> '26,80%'."""
    return f"{miles(valor, decimales)}%"


def fecha_dmy(d: date) -> str:
    """Fecha como DD/MM/AAAA."""
    return d.strftime("%d/%m/%Y")


def fecha_iso_a_dmy(iso: str | None) -> str:
    """Convierte 'AAAA-MM-DD' (como se guarda en la BD) a DD/MM/AAAA; '-' si está vacía."""
    if not iso:
        return "-"
    return fecha_dmy(date.fromisoformat(iso))


def ahora_iso() -> str:
    """Fecha y hora actuales como 'AAAA-MM-DD HH:MM' (formato de la BD)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def iso_a_dmy_hora(iso: str) -> str:
    """Convierte 'AAAA-MM-DD HH:MM' a 'DD/MM/AAAA HH:MM' para mostrar."""
    try:
        return datetime.strptime(iso, "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


def formatear_documento(texto: str) -> str:
    """C.I. '4567890' -> '4.567.890'; RUC '4567890-1' -> '4.567.890-1'; pasaporte en mayúsculas."""
    t = texto.strip()
    if any(c.isalpha() for c in t):
        return "".join(c for c in t if c.isalnum() or c == "-").upper()
    cuerpo, sep, dv = t.partition("-")
    digitos = "".join(c for c in cuerpo if c.isdigit())
    if not digitos:
        return ""
    con_puntos = f"{int(digitos):,}".replace(",", ".")
    if sep:
        return f"{con_puntos}-{''.join(c for c in dv if c.isdigit())[:1]}"
    return con_puntos
