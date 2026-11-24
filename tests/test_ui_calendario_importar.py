"""UI: selector de calendario e importación de respaldos."""
import tkinter as tk
from datetime import date

from proformas.db import RepositorioProformas
from proformas.ui.widgets import SelectorFecha

from test_importar import datos  # noqa: E402  (conftest agrega tests/ al path con rootdir)


def test_calendario_elige_fecha_y_actualiza_vencimiento(app):
    app.p_desemb.abrir_calendario()
    app.update()
    sel = app.p_desemb.calendario
    assert isinstance(sel, SelectorFecha) and sel.winfo_exists()
    sel._mover(1)
    mes, anio = sel.mes, sel.anio
    boton = next(w for w in sel.cuerpo.winfo_children() if isinstance(w, tk.Button) and w.cget("text") == "10")
    boton.invoke()
    app.update()
    assert app.p_desemb.get() == f"10/{mes:02d}/{anio}"
    assert app.p_vto.get() != "" and app.resultado is not None
    assert not sel.winfo_exists()


def test_calendario_abre_en_la_fecha_del_campo_y_cierra_con_escape(app):
    app.p_vto.set("15/03/2027")
    app.p_vto.abrir_calendario()
    app.update()
    sel = app.p_vto.calendario
    assert (sel.mes, sel.anio) == (3, 2027)
    sel.event_generate("<Escape>")
    app.update()
    assert not sel.winfo_exists()


def test_calendario_con_fecha_invalida_abre_en_hoy(app):
    app.p_vto.set("99/99/9999")
    app.p_vto.abrir_calendario()
    app.update()
    assert app.p_vto.calendario.anio == date.today().year
    app.p_vto.calendario.destroy()


def test_calendario_boton_hoy_y_limites_de_anio(app):
    app.p_desemb.set("01/01/2000")
    app.p_desemb.abrir_calendario()
    app.update()
    sel = app.p_desemb.calendario
    sel._mover(-1)  # no pasa de 2000
    assert (sel.mes, sel.anio) == (1, 2000)
    sel._hoy()
    app.update()
    assert app.p_desemb.get() == date.today().strftime("%d/%m/%Y")


def _preparar(app, monkeypatch, tmp_path, eleccion, confirma=True):
    from proformas.ui import app as modulo

    origen = tmp_path / "otro.db"
    otro = RepositorioProformas(origen)
    for n in ("Cliente Importado Uno", "Cliente Importado Dos"):
        otro.crear(datos(nombre_cliente=n))
    otro.cerrar()
    monkeypatch.setattr(modulo.filedialog, "askopenfilename", lambda **k: str(origen))
    monkeypatch.setattr(modulo.messagebox, "askyesnocancel", lambda *a, **k: eleccion)
    monkeypatch.setattr(modulo.messagebox, "askyesno", lambda *a, **k: confirma)


def test_importar_combinar_desde_la_ui(app, monkeypatch, tmp_path):
    app.c_nombre.set("Juan Pérez")
    app.c_doc.set("4567890")
    app.c_tel.set("0981 555-123")
    app.guardar()
    _preparar(app, monkeypatch, tmp_path, eleccion=True)
    app.importar()
    assert len(app.repo.listar()) == 3
    assert len(app.tv_guardadas.get_children()) == 3
    assert app.mensajes[-1][0] == "showinfo" and "Importadas: 2" in app.mensajes[-1][1]


def test_importar_reemplazar_cancelar_y_confirmar(app, monkeypatch, tmp_path):
    app.c_nombre.set("Juan Pérez")
    app.c_doc.set("4567890")
    app.c_tel.set("0981 555-123")
    app.guardar()
    _preparar(app, monkeypatch, tmp_path, eleccion=False, confirma=False)
    app.importar()  # no confirma el reemplazo
    assert len(app.repo.listar()) == 1
    _preparar(app, monkeypatch, tmp_path, eleccion=None)
    app.importar()  # cancelar
    assert len(app.repo.listar()) == 1
    _preparar(app, monkeypatch, tmp_path, eleccion=False, confirma=True)
    app.importar()
    assert {p.nombre_cliente for p in app.repo.listar()} == {"Cliente Importado Uno", "Cliente Importado Dos"}
    assert list((app.cfg.db_path.parent / "backups").glob("antes_de_importar_*.db"))


def test_importar_archivo_invalido_muestra_mensaje(app, monkeypatch, tmp_path):
    from proformas.ui import app as modulo

    malo = tmp_path / "malo.db"
    malo.write_text("no soy sqlite")
    monkeypatch.setattr(modulo.filedialog, "askopenfilename", lambda **k: str(malo))
    monkeypatch.setattr(modulo.messagebox, "askyesnocancel", lambda *a, **k: True)
    app.importar()
    assert app.mensajes[-1][0] == "showerror" and "válida" in app.mensajes[-1][1]
