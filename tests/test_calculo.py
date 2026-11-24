"""Pruebas del cálculo contra los valores producidos por el prototipo HTML (tests/golden)."""
import json
from datetime import date
from pathlib import Path

import pytest

from proformas.calculo import ParametrosProforma, calcular_proforma, redondeo_js

GOLDEN = json.loads((Path(__file__).parent / "golden" / "referencia_html.json").read_text(encoding="utf-8"))


def _params(inp: dict) -> ParametrosProforma:
    return ParametrosProforma(
        capital=inp["capital"],
        tasa_anual=inp["tasaAnual"],
        cuotas=inp["plazoMeses"],
        iva_pct=inp["ivaPct"],
        pct_gastos=inp["pctGastos"],
        tasa_seguro=inp["tasaSeguro"],
        redondear=inp["redondear"],
        fecha_desembolso=date.fromisoformat(inp["fechaDesembolso"]),
        primer_vencimiento=date.fromisoformat(inp["primerVencimiento"]),
    )


@pytest.mark.parametrize("caso", GOLDEN, ids=[c["input"]["name"] for c in GOLDEN])
def test_coincide_con_prototipo_html(caso):
    r = calcular_proforma(_params(caso["input"]))
    o = caso["out"]
    tol = 0.011
    assert r.cuota_final == pytest.approx(o["cuotaFinal"], abs=tol)
    assert r.cuota_base_gastos == pytest.approx(o["cuotaBaseGastos"], abs=tol)
    assert r.seguro_nivelado == pytest.approx(o["seguro"], abs=tol)
    assert r.g_adm_total == pytest.approx(o["gAdmTotal"], abs=tol)
    assert r.g_adm_mensual == pytest.approx(o["gAdmMensual"], abs=tol)
    assert r.totales.cuota_final == pytest.approx(o["totalPagar"], abs=0.5)
    assert r.totales.interes == pytest.approx(o["totInteres"], abs=0.5)
    assert r.totales.iva == pytest.approx(o["totIva"], abs=0.5)
    assert r.tae_pct == pytest.approx(o["tae"], abs=0.01)
    assert r.primer_vto_modificado == o["primerVtoModificado"]
    assert r.plazo_dias_total == o["plazoDias"]
    assert len(r.cuotero) == len(o["schedule"])
    for fila, esp in zip(r.cuotero, o["schedule"]):
        assert fila.cuota == esp[0]
        assert fila.vencimiento.strftime("%d/%m/%Y") == esp[1]
        assert fila.dias == esp[2]
        assert fila.saldo_inicial == pytest.approx(esp[3], abs=tol)
        assert fila.amort_capital == pytest.approx(esp[4], abs=tol)
        assert fila.interes == pytest.approx(esp[6], abs=tol)
        assert fila.cuota_final == pytest.approx(esp[9], abs=tol)
        assert fila.saldo_final == pytest.approx(esp[10], abs=tol)


def test_caso_de_oro_valores_conocidos():
    caso = next(c for c in GOLDEN if c["input"]["name"] == "oro")
    r = calcular_proforma(_params(caso["input"]))
    assert r.cuota_final == 991072
    assert r.g_adm_total == 220000
    assert r.g_adm_mensual == 18333


@pytest.mark.parametrize("caso", GOLDEN, ids=[c["input"]["name"] for c in GOLDEN])
def test_saldo_cierra_en_cero_y_cuotas_iguales(caso):
    r = calcular_proforma(_params(caso["input"]))
    assert r.cuotero[-1].saldo_final == 0
    assert r.totales.amort_capital == pytest.approx(r.params.capital, abs=1500)
    if r.params.cuotas > 1:
        assert r.cuotero[-1].cuota_final == pytest.approx(r.cuota_final, abs=0.011)


def test_redondeo_half_up():
    assert redondeo_js(2.5) == 3
    assert redondeo_js(0.5) == 1
    assert redondeo_js(1.4999) == 1


def test_parametros_invalidos():
    with pytest.raises(ValueError):
        calcular_proforma(ParametrosProforma(capital=0, tasa_anual=24, cuotas=12))
    with pytest.raises(ValueError):
        calcular_proforma(ParametrosProforma(capital=1000, tasa_anual=24, cuotas=0))


def test_primer_vencimiento_fin_de_semana_se_traslada():
    from proformas.calculo import normalizar_primer_vencimiento

    sabado = date(2026, 11, 28)
    habil, nominal = normalizar_primer_vencimiento(sabado, date(2026, 10, 28))
    assert habil == date(2026, 11, 30) and nominal == sabado
    habil, nominal = normalizar_primer_vencimiento(date(2026, 11, 27), date(2026, 10, 28))
    assert habil == date(2026, 11, 27) and nominal is None
