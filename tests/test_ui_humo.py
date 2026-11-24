"""Prueba de humo de la UI: crea la ventana real y simula el flujo del usuario (sin mainloop)."""
import tkinter as tk
from dataclasses import replace

import pytest

from proformas.config import cargar_config
from proformas.db import RepositorioProformas


@pytest.fixture(scope="module")
def _ventana(tmp_path_factory):
    """Una sola ventana Tk por módulo (crear/destruir muchas es inestable en Tk 8.6/Windows)."""
    from proformas.ui import app as modulo

    tmp = tmp_path_factory.mktemp("ui")
    cfg = replace(cargar_config(), pdf_dir=tmp / "pdf")
    try:
        a = modulo.App(cfg, RepositorioProformas(tmp / "ui.db"))
    except tk.TclError:
        pytest.skip("Sin entorno gráfico")
    a.withdraw()
    yield a, modulo
    a.destroy()


@pytest.fixture
def app(_ventana, monkeypatch):
    a, modulo = _ventana
    mensajes = []
    for nombre in ("showwarning", "showerror", "showinfo"):
        monkeypatch.setattr(modulo.messagebox, nombre, lambda t, m, _n=nombre, **k: mensajes.append((_n, m)))
    monkeypatch.setattr(modulo.messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(modulo.os, "startfile", lambda p: None, raising=False)
    for r in a.repo.listar():
        a.repo.eliminar(r.id)
    a.vista.set("comercial")
    a.busqueda.set("")
    a.nueva(restablecer=True)
    a.mensajes = mensajes
    a.update()
    return a


def llenar_cliente(a, nombre="Juan Pérez", doc="4567890", tel="0981 555-123"):
    a.c_nombre.set(nombre)
    a.c_doc.set(doc)
    a.c_tel.set(tel)


def test_calculo_inicial_y_kpis(app):
    assert app.resultado is not None
    assert app.kpi["cuota"][0].cget("text").startswith("Gs. ")
    assert len(app.tv_cuotero.get_children()) == 13  # 12 cuotas + totales


def test_crud_completo(app):
    llenar_cliente(app)
    app.guardar()
    assert len(app.repo.listar()) == 1 and app.editando is not None
    app.p_capital.set("20.000.000")
    app.guardar()  # actualiza
    regs = app.repo.listar()
    assert len(regs) == 1 and regs[0].capital == 20_000_000 and app.editando is None
    app.tv_guardadas.selection_set(str(regs[0].id))
    app.pdf_seleccion()
    assert list((app.cfg.pdf_dir).glob("*.pdf"))
    app.eliminar_seleccion()
    assert app.repo.listar() == []


def test_obligatorios_vacios_no_guardan(app):
    app.guardar()
    assert app.repo.listar() == []
    assert app.mensajes and app.mensajes[-1][0] == "showwarning"
    assert app.c_nombre.error.cget("text") and app.c_tel.error.cget("text")


def test_telefono_invalido_no_guarda(app):
    llenar_cliente(app, tel="000000")
    app.guardar()
    assert app.repo.listar() == []
    assert "repetidos" in app.c_tel.error.cget("text")


def test_filtro_de_teclado_rechaza_letras(app):
    app.update()
    casos = ((app.p_capital, "12ab$", "10.000.00012"), (app.p_cuotas, "x", "12"), (app.c_tel, "09a1", "09 1"),
             (app.p_tan, "1.2.3", "24"))
    for campo, texto, _ in casos:
        antes = campo.get()
        campo.entry.delete(0, "end")
        campo.entry.insert(0, antes)
        campo.entry.insert("end", texto)
        despues = campo.get()
        assert not any(ch.isalpha() or ch == "$" for ch in despues), (campo, despues)
    app.c_tel.set("")
    app.c_tel.entry.insert(0, "abc")
    assert app.c_tel.get() == ""
    app.p_cuotas.entry.delete(0, "end")
    app.p_cuotas.entry.insert(0, "1x2")
    assert app.p_cuotas.get() == ""


def test_parametro_invalido_limpia_resultado_sin_romper(app):
    app.p_cuotas.set("")
    assert app.resultado is None
    assert app.p_cuotas.error.cget("text")
    app.p_cuotas.set("0")
    assert app.resultado is None
    app.p_cuotas.set("12")
    assert app.resultado is not None
    app.p_desemb.set("31/02/2026")
    assert app.resultado is None and app.p_desemb.error.cget("text")


def test_capital_cero_y_fechas_cruzadas(app):
    app.p_capital.set("0")
    assert app.resultado is None and app.p_capital.error.cget("text")
    app.p_capital.set("10.000.000")
    app.p_desemb.set("24/11/2026")
    app.p_vto.set("01/11/2026")
    assert app.resultado is None and "anterior" in app.p_vto.error.cget("text")


def test_entradas_hostiles_no_rompen(app):
    llenar_cliente(app, nombre="Robert'); DROP TABLE proformas;--", doc="4567890")
    app.guardar()
    assert app.repo.listar() == []  # nombre con caracteres no permitidos se rechaza
    llenar_cliente(app, nombre="😀😀😀")
    app.guardar()
    assert app.repo.listar() == []
    app.busqueda.set("' OR 1=1 --")
    app.update()
    assert app.repo.listar() == []


def test_vencimiento_fin_de_semana_se_traslada(app):
    app.p_desemb.set("24/11/2026")
    app.p_vto.set("28/12/2026")  # lunes? 28/12/2026 es lunes; usar sábado 26/12/2026
    app.p_vto.set("26/12/2026")
    app._normalizar_vto()
    assert app.p_vto.get() == "28/12/2026" and app.nominal is not None


def test_vista_analitica_y_exacto(app):
    app.vista.set("analitica")
    app.redondeo.current(1)
    app.recalcular()
    assert len(app.tv_cuotero["columns"]) == 14
    assert "," in app.kpi["cuota"][0].cget("text")


def test_excepcion_interna_no_cierra(app):
    try:
        raise RuntimeError("fallo interno")
    except RuntimeError:
        import sys
        app.report_callback_exception(*sys.exc_info())
    assert app.mensajes[-1][0] == "showerror" and "fallo interno" not in app.mensajes[-1][1]
