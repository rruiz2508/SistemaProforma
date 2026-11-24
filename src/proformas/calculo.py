"""Lógica financiera PURA de la proforma (Método Francés + gastos + IVA + seguro nivelado).

Es una traducción fiel de `calculateProforma` del prototipo HTML. No depende de UI, BD ni PDF.
Las reglas están descritas en docs/reglas-negocio.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

from .fechas import (
    dias_entre,
    siguiente_dia_habil,
    siguiente_mes_habil,
    sumar_meses,
    sumar_meses_habil,
)

# Regla legado: si el 1er vencimiento se aleja del habitual, se cobran los meses completos + 1 extra.
LEGACY_MES_EXTRA_PRIMER_VTO = True
BASE_DIAS_TAE = 365


def redondeo_js(x: float) -> int:
    """Redondeo half-up (igual a Math.round de JavaScript; Python usa half-even)."""
    return math.floor(x + 0.5)


def _r(x: float, entero: bool) -> float:
    """Redondea según el modo: entero (institucional) o 2 decimales (exacto)."""
    return float(redondeo_js(x)) if entero else round(x + 0.0, 2)


@dataclass(frozen=True)
class ParametrosProforma:
    capital: int
    tasa_anual: float  # TAN %
    cuotas: int
    iva_pct: float = 10.0
    pct_gastos: float = 2.0
    tasa_seguro: float = 0.25  # % mensual
    redondear: bool = True
    fecha_desembolso: date = field(default_factory=date.today)
    primer_vencimiento: date | None = None
    #: Vencimiento original (fin de semana) antes de trasladarse al lunes hábil.
    primer_vto_nominal: date | None = None

    def primer_vto_efectivo(self) -> date:
        return self.primer_vencimiento or siguiente_mes_habil(self.fecha_desembolso)


@dataclass(frozen=True)
class FilaCuota:
    cuota: int
    vencimiento: date
    dias: int
    saldo_inicial: float
    amort_capital: float
    g_adm: float
    amort_total: float
    interes: float
    iva: float
    extra_dias: float
    cuota_base_gastos: float
    seguro: float
    cuota_final: float
    saldo_final: float


@dataclass(frozen=True)
class Totales:
    amort_capital: float
    g_adm: float
    amort_total: float
    interes: float
    iva: float
    extra_dias: float
    base_gastos: float
    seguro: float
    cuota_final: float


@dataclass(frozen=True)
class ResultadoProforma:
    params: ParametrosProforma
    i_mensual_pct: float
    i_mensual_iva_pct: float
    tae_pct: float
    tasa_anual_iva_pct: float
    dias_primer_vto: int
    dias_traslado_fin_semana: int
    dias_excedentes: int
    primer_vto_modificado: bool
    meses_interes_primer_periodo: int
    extra_total_cuota: float
    plazo_dias_total: int
    g_adm_base: float
    g_adm_iva: float
    g_adm_total: float
    g_adm_mensual: float
    seguro_nivelado: float
    cuota_base_gastos: float
    cuota_final: float
    cuotero: tuple[FilaCuota, ...]
    totales: Totales

    @property
    def decimales(self) -> int:
        return 0 if self.params.redondear else 2


def normalizar_primer_vencimiento(
    deseado: date, desembolso: date
) -> tuple[date, date | None]:
    """Devuelve (vencimiento_hábil, nominal_si_hubo_traslado).

    Si el vencimiento deseado cae en fin de semana se traslada al lunes sin recargo de interés.
    """
    habil = siguiente_dia_habil(deseado)
    return habil, (deseado if habil != deseado else None)


def calcular_tae(capital: float, desembolso: date, pagos: list[tuple[date, float]]) -> float:
    """Tasa anual efectiva (%) por bisección: VP de los pagos = capital (act/365)."""
    if not capital > 0 or not pagos:
        return 0.0
    t = [dias_entre(desembolso, f) / BASE_DIAS_TAE for f, _ in pagos]

    def vp(r: float) -> float:
        return sum(m / (1 + r) ** ti for (_, m), ti in zip(pagos, t)) - capital

    if vp(0) <= 0:
        return 0.0
    lo, hi = 0.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if vp(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 * 100


def calcular_proforma(p: ParametrosProforma) -> ResultadoProforma:
    """Calcula la proforma completa. Lanza ValueError si los parámetros son incoherentes."""
    if p.capital <= 0 or p.cuotas < 1:
        raise ValueError("Capital y cuotas deben ser positivos.")
    n = p.cuotas
    capital = float(p.capital)
    ent = p.redondear

    iva = p.iva_pct / 100
    i_men = (p.tasa_anual / 100) / 12
    i_men_iva = i_men * (1 + iva)
    tasa_anual_iva = p.tasa_anual * (1 + iva)

    if i_men_iva > 0:
        factor = (1 + i_men_iva) ** n
        cuota_sin_gasto = capital * (i_men_iva * factor) / (factor - 1)
    else:
        cuota_sin_gasto = capital / n

    g_base = capital * (p.pct_gastos / 100)
    g_iva = g_base * iva
    g_total = g_base + g_iva
    g_mensual_ex = g_total / n

    d_des = p.fecha_desembolso
    v1_raw = p.primer_vto_efectivo()
    v1_habil = siguiente_dia_habil(d_des) if v1_raw < d_des else siguiente_dia_habil(v1_raw)

    nominal_1m = sumar_meses(d_des, 1)
    habil_1m = siguiente_dia_habil(nominal_1m)

    ancla = d_des if v1_raw < d_des else v1_raw
    dias_traslado = dias_entre(ancla, v1_habil)
    if v1_habil == habil_1m:
        ancla = nominal_1m
        dias_traslado = dias_entre(nominal_1m, habil_1m)
    elif p.primer_vto_nominal is not None and p.primer_vto_nominal < v1_habil:
        ancla = p.primer_vto_nominal
        dias_traslado = dias_entre(p.primer_vto_nominal, v1_habil)

    dias_primer = dias_entre(d_des, v1_habil)
    dias_comp = max(0, dias_primer - dias_traslado)
    dias_exc = max(0, dias_comp - 30)

    modificado = LEGACY_MES_EXTRA_PRIMER_VTO and dias_exc > 0 and v1_raw > siguiente_mes_habil(d_des)
    base_credito = capital + g_total
    meses_primer = 1
    if modificado:
        completos = 0
        while sumar_meses(d_des, completos + 1) <= ancla:
            completos += 1
        meses_primer = completos + 1

    if modificado:
        extra_base_total = i_men * (base_credito * meses_primer - capital)
    elif dias_exc > 0:
        extra_base_total = capital * (i_men / 30) * dias_exc
    else:
        extra_base_total = 0.0
    extra_total = extra_base_total * (1 + iva)
    extra_base_cuota_ex = extra_base_total / n
    extra_total_cuota_ex = extra_total / n

    # Seguro nivelado: promedio del seguro (con IVA) sobre el saldo de cada período.
    saldo_ex = capital
    seg_rate = p.tasa_seguro / 100
    suma_seg = ((base_credito if modificado else saldo_ex) * seg_rate) * (1 + iva)
    for k in range(1, n + 1):
        int_k = saldo_ex * i_men
        iva_int_k = int_k * iva
        amort_k = min(saldo_ex, max(0.0, cuota_sin_gasto - int_k - iva_int_k))
        saldo_ex = max(0.0, saldo_ex - amort_k)
        if k < n:
            suma_seg += (saldo_ex * seg_rate) * (1 + iva)
    seguro_niv_ex = suma_seg / n

    if not ent:
        seguro_niv = round(seguro_niv_ex, 2)
    elif modificado:
        seg_sin_iva = redondeo_js(seguro_niv_ex / (1 + iva))
        seguro_niv = float(seg_sin_iva + redondeo_js(seg_sin_iva * iva))
    else:
        seguro_niv = float(redondeo_js(seguro_niv_ex))

    g_mensual = _r(g_mensual_ex, ent)
    extra_total_cuota = _r(extra_total_cuota_ex, ent)

    base_gastos_ex = cuota_sin_gasto + g_mensual_ex + extra_total_cuota_ex
    cuota_base_gastos = _r(base_gastos_ex, ent)
    cuota_final_ref = _r(base_gastos_ex + seguro_niv_ex, ent)

    credito_red = redondeo_js(capital + g_total)
    ajuste = (redondeo_js(credito_red / 1000) * 1000 - credito_red) if (modificado and ent) else 0

    cuotero: list[FilaCuota] = []
    saldo_cap = capital
    saldo_g = _r(g_total, ent)
    prev = d_des
    tot = dict(ac=0.0, g=0.0, at=0.0, i=0.0, v=0.0, e=0.0, bg=0.0, s=0.0, cf=0.0)

    for k in range(1, n + 1):
        fecha = v1_habil if k == 1 else sumar_meses_habil(ancla, k - 1)
        dias_per = dias_entre(prev, fecha)
        prev = fecha

        s_ini = saldo_cap
        int_raw = s_ini * i_men
        interes = _r(int_raw + extra_base_cuota_ex, ent)
        iva_k = _r((int_raw + extra_base_cuota_ex) * iva, ent)
        extra_cuota = extra_total_cuota if ent else round(extra_total_cuota_ex, 2)

        g_cuota = g_mensual if k < n else _r(max(0.0, saldo_g), ent)
        saldo_g = max(0.0, saldo_g - g_cuota)
        seg = seguro_niv

        if k < n:
            cuota_final = cuota_final_ref
            disp = cuota_final - seg - g_cuota - interes - iva_k
            amort = float(max(0, min(s_ini, redondeo_js(disp)))) if ent else round(max(0.0, min(s_ini, disp)), 2)
        else:
            amort = _r(s_ini, ent) + ajuste
            cuota_final = _r(amort + g_cuota + interes + iva_k + seg, ent)
            residuo = cuota_final_ref - cuota_final
            if n > 1 and residuo != 0 and abs(residuo) <= max(5, cuota_final_ref * 0.005):
                interes = _r(interes + residuo, ent)
                cuota_final = cuota_final_ref

        s_fin = _r(max(0.0, s_ini - amort), ent)
        amort_total = _r(amort + g_cuota, ent)
        base_gastos_fila = _r(cuota_final - seg, ent)
        saldo_cap = s_fin

        tot["ac"] += amort
        tot["g"] += g_cuota
        tot["at"] += amort_total
        tot["i"] += interes
        tot["v"] += iva_k
        tot["e"] += extra_cuota
        tot["bg"] += base_gastos_fila
        tot["s"] += seg
        tot["cf"] += cuota_final

        cuotero.append(
            FilaCuota(k, fecha, dias_per, s_ini, amort, g_cuota, amort_total, interes, iva_k,
                      extra_cuota, base_gastos_fila, seg, cuota_final, s_fin)
        )

    ultimo = cuotero[-1].vencimiento
    if n == 1:
        cuota_final_ref = cuotero[0].cuota_final
        cuota_base_gastos = cuotero[0].cuota_base_gastos

    tae = calcular_tae(
        capital,
        d_des,
        [(f.vencimiento, f.amort_capital + f.interes + f.g_adm + f.iva + f.seguro) for f in cuotero],
    )

    return ResultadoProforma(
        params=p,
        i_mensual_pct=i_men * 100,
        i_mensual_iva_pct=i_men_iva * 100,
        tae_pct=tae,
        tasa_anual_iva_pct=tasa_anual_iva,
        dias_primer_vto=dias_primer,
        dias_traslado_fin_semana=dias_traslado,
        dias_excedentes=dias_exc,
        primer_vto_modificado=modificado,
        meses_interes_primer_periodo=meses_primer,
        extra_total_cuota=extra_total_cuota,
        plazo_dias_total=dias_entre(d_des, ultimo),
        g_adm_base=_r(g_base, ent),
        g_adm_iva=_r(g_iva, ent),
        g_adm_total=_r(g_total, ent),
        g_adm_mensual=g_mensual,
        seguro_nivelado=seguro_niv,
        cuota_base_gastos=cuota_base_gastos,
        cuota_final=cuota_final_ref,
        cuotero=tuple(cuotero),
        totales=Totales(tot["ac"], tot["g"], tot["at"], tot["i"], tot["v"], tot["e"],
                        tot["bg"], tot["s"], tot["cf"]),
    )
