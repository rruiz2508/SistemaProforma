"""Punto de entrada: python -m proformas"""
from __future__ import annotations

import logging
import sys
from tkinter import Tk, messagebox

from .config import cargar_config
from .db import ErrorBaseDatos, RepositorioProformas


def main() -> None:
    """Configura el log, abre la base de datos y lanza la ventana principal (bucle de eventos de Tk).

    Si la base de datos no se puede abrir muestra un mensaje claro y termina con código 1.
    """
    cfg = cargar_config()
    try:
        cfg.log_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=cfg.log_path, level=logging.INFO, encoding="utf-8",
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    except OSError:
        logging.basicConfig(level=logging.WARNING)
    try:
        repo = RepositorioProformas(cfg.db_path)
    except ErrorBaseDatos as e:
        logging.getLogger("proformas").exception("No se pudo abrir la BD")
        raiz = Tk()
        raiz.withdraw()
        messagebox.showerror("Sistema de Proformas", f"{e}\nVerifique permisos de la carpeta de datos.")
        sys.exit(1)

    from .ui.app import App  # import tardío: la UI no es necesaria para las pruebas

    app = App(cfg, repo)
    try:
        app.mainloop()
    finally:
        repo.cerrar()


if __name__ == "__main__":
    main()
