"""Widgets reutilizables: campos con filtro de teclado y formato en vivo."""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

ROJO = "#D11D27"
ROJO_HOVER = "#B0151E"
NARANJA = "#F16522"
CARBON = "#18181B"
FONDO = "#F5F5F6"
BORDE = "#E4E4E7"

_NOMBRE_OK = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .,'&()/\-]*$")
_DOC_OK = re.compile(r"^[A-Za-z0-9.\-]*$")
_TEL_OK = re.compile(r"^[0-9 +\-()]*$")
_FECHA_OK = re.compile(r"^[0-9/]*$")
_DIG_OK = re.compile(r"^[0-9]*$")
_DEC_OK = re.compile(r"^[0-9]*[.,]?[0-9]*$")
_MONTO_OK = re.compile(r"^[0-9.]*$")

FILTROS = {
    "nombre": (_NOMBRE_OK, 120),
    "documento": (_DOC_OK, 20),
    "telefono": (_TEL_OK, 25),
    "fecha": (_FECHA_OK, 10),
    "entero": (_DIG_OK, 3),
    "decimal": (_DEC_OK, 7),
    "monto": (_MONTO_OK, 16),
}


def formatear_miles(texto: str) -> str:
    digitos = "".join(c for c in texto if c.isdigit())
    if not digitos:
        return ""
    return f"{int(digitos):,}".replace(",", ".")


class Campo:
    """Etiqueta + Entry con filtro de teclado + etiqueta de error en rojo."""

    def __init__(self, padre: tk.Misc, fila: int, etiqueta: str, filtro: str, *, col: int = 0,
                 ancho: int = 24, requerido: bool = False, sufijo: str = "", valor: str = "",
                 al_cambiar=None, columnspan: int = 1) -> None:
        regex, maximo = FILTROS[filtro]
        self.var = tk.StringVar(value=valor)
        marco = ttk.Frame(padre)
        marco.grid(row=fila, column=col, columnspan=columnspan, sticky="ew", padx=6, pady=(0, 4))
        marco.columnconfigure(0, weight=1)
        texto = etiqueta + (" *" if requerido else "")
        ttk.Label(marco, text=texto, style="Campo.TLabel").grid(row=0, column=0, sticky="w", columnspan=2)
        self.vcmd = (padre.register(lambda p, r=regex, m=maximo: len(p) <= m and bool(r.match(p))), "%P")
        self.entry = ttk.Entry(marco, textvariable=self.var, width=ancho, validate="key", validatecommand=self.vcmd)
        self.entry.grid(row=1, column=0, sticky="ew")
        if sufijo:
            ttk.Label(marco, text=sufijo, style="Suave.TLabel").grid(row=1, column=1, padx=(4, 0))
        self.error = ttk.Label(marco, text="", style="Error.TLabel", wraplength=300, justify="left")
        self.error.grid(row=2, column=0, columnspan=2, sticky="w")
        if filtro == "monto":
            self.var.trace_add("write", self._reformatear)
        if al_cambiar:
            self.var.trace_add("write", lambda *_: al_cambiar())

    def _reformatear(self, *_):
        actual = self.var.get()
        nuevo = formatear_miles(actual)
        if nuevo != actual:
            pos = self.entry.index("insert")
            digitos_antes = sum(c.isdigit() for c in actual[:pos])
            self.var.set(nuevo)
            cuenta = 0
            nueva_pos = 0
            while nueva_pos < len(nuevo) and cuenta < digitos_antes:
                if nuevo[nueva_pos].isdigit():
                    cuenta += 1
                nueva_pos += 1
            self.entry.icursor(nueva_pos)

    def get(self) -> str:
        return self.var.get()

    def set(self, valor: str) -> None:
        self.var.set(valor)

    def mostrar_error(self, mensaje: str) -> None:
        self.error.configure(text=mensaje)

    def limpiar_error(self) -> None:
        self.error.configure(text="")


def configurar_estilos(root: tk.Misc) -> None:
    s = ttk.Style(root)
    s.theme_use("clam")
    root.configure(bg=FONDO)
    s.configure(".", font=("Segoe UI", 10), background="white")
    s.configure("TFrame", background="white")
    s.configure("Fondo.TFrame", background=FONDO)
    s.configure("Card.TLabelframe", background="white", bordercolor=BORDE, relief="solid")
    s.configure("Card.TLabelframe.Label", background="white", foreground=CARBON, font=("Segoe UI", 11, "bold"))
    s.configure("TLabel", background="white", foreground=CARBON)
    s.configure("Campo.TLabel", font=("Segoe UI", 9, "bold"))
    s.configure("Suave.TLabel", foreground="#71717A", font=("Segoe UI", 9))
    s.configure("Error.TLabel", foreground=ROJO, font=("Segoe UI", 9))
    s.configure("Ayuda.TLabel", foreground="#52525B", font=("Segoe UI", 9))
    s.configure("KpiTitulo.TLabel", font=("Segoe UI", 9, "bold"), foreground=ROJO)
    s.configure("KpiValor.TLabel", font=("Segoe UI", 17, "bold"))
    s.configure("KpiSub.TLabel", font=("Segoe UI", 8), foreground="#71717A")
    s.configure("Oscuro.TFrame", background=CARBON)
    s.configure("Oscuro.TLabel", background=CARBON, foreground="white")
    s.configure("OscuroSub.TLabel", background=CARBON, foreground="#A1A1AA", font=("Segoe UI", 9))
    s.configure("Titulo.TLabel", background=CARBON, foreground="white", font=("Segoe UI", 14, "bold"))
    s.configure("Aviso.TLabel", background="#FFF7ED", foreground=CARBON, font=("Segoe UI", 10, "bold"))
    s.configure("Aviso.TFrame", background="#FFF7ED")
    s.configure("Estado.TLabel", background=CARBON, foreground="white", font=("Segoe UI", 9))
    s.configure("TButton", padding=(10, 5), background=FONDO, bordercolor=BORDE)
    s.map("TButton", background=[("active", "#E4E4E7")])
    s.configure("Principal.TButton", background=ROJO, foreground="white", font=("Segoe UI", 10, "bold"))
    s.map("Principal.TButton", background=[("active", ROJO_HOVER)])
    s.configure("Naranja.TButton", background=NARANJA, foreground="white", font=("Segoe UI", 10, "bold"))
    s.map("Naranja.TButton", background=[("active", "#D95314")])
    s.configure("Peligro.TButton", foreground=ROJO)
    s.configure("Treeview", rowheight=24, font=("Segoe UI", 9), fieldbackground="white")
    s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background=FONDO, foreground=CARBON)
    s.configure("TRadiobutton", background="white")
