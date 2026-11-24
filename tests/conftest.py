"""Fixtures compartidos. La UI usa UNA sola ventana Tk por sesión de pruebas
(crear y destruir varias es inestable en Tk 8.6 / Windows)."""
import tkinter as tk
from dataclasses import replace

import pytest

from proformas.config import cargar_config
from proformas.db import RepositorioProformas


@pytest.fixture(scope="session")
def _ventana(tmp_path_factory):
    from proformas.ui import app as modulo

    tmp = tmp_path_factory.mktemp("ui")
    cfg = replace(cargar_config(), pdf_dir=tmp / "pdf", db_path=tmp / "ui.db")
    try:
        a = modulo.App(cfg, RepositorioProformas(cfg.db_path))
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
