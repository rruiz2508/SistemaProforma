"""Utilidades de fechas: días hábiles y suma de meses."""
from __future__ import annotations

import calendar
from datetime import date, timedelta


def sumar_meses(base: date, meses: int) -> date:
    """Suma meses conservando el día (o el último día del mes si no existe)."""
    indice = base.year * 12 + (base.month - 1) + meses
    anio, mes0 = divmod(indice, 12)
    mes = mes0 + 1
    ultimo = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(base.day, ultimo))


def siguiente_dia_habil(d: date) -> date:
    """Sábado -> lunes (+2), domingo -> lunes (+1)."""
    dow = d.weekday()  # lunes=0 ... domingo=6
    if dow == 5:
        return d + timedelta(days=2)
    if dow == 6:
        return d + timedelta(days=1)
    return d


def sumar_meses_habil(base: date, meses: int) -> date:
    """Suma `meses` a `base` y traslada el resultado a día hábil."""
    return siguiente_dia_habil(sumar_meses(base, meses))


def dias_entre(d1: date, d2: date) -> int:
    """Días corridos entre dos fechas (nunca negativo)."""
    return max(0, (d2 - d1).days)


def siguiente_mes_habil(d: date) -> date:
    """Primer vencimiento habitual: desembolso + 1 mes, trasladado a día hábil."""
    return sumar_meses_habil(d, 1)
