"""Widgets reutilizables: campos con filtro de teclado y formato en vivo."""
from __future__ import annotations

import calendar
import re
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

ROJO = "#D11D27"
ROJO_HOVER = "#B0151E"
NARANJA = "#F16522"
CARBON = "#18181B"
FONDO = "#F5F5F6"
BORDE = "#E4E4E7"

# Filtros de TECLADO: se evalúan en cada pulsación (validatecommand de Tk) sobre el texto que
# quedaría si se aceptara el cambio. Son más permisivos que los validadores finales (permiten
# estados intermedios como "4." mientras se escribe); la validación completa ocurre al guardar.
_NOMBRE_OK = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .,'&()/\-]*$")
_DOC_OK = re.compile(r"^[A-Za-z0-9.\-]*$")
_TEL_OK = re.compile(r"^[0-9 +\-()]*$")
_FECHA_OK = re.compile(r"^[0-9/]*$")
_DIG_OK = re.compile(r"^[0-9]*$")
_DEC_OK = re.compile(r"^[0-9]*[.,]?[0-9]*$")
_MONTO_OK = re.compile(r"^[0-9.]*$")

# tipo de campo -> (expresión permitida, largo máximo)
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
    """Deja solo los dígitos y agrega puntos de miles: '1234567' -> '1.234.567'."""
    digitos = "".join(c for c in texto if c.isdigit())
    if not digitos:
        return ""
    return f"{int(digitos):,}".replace(",", ".")


MESES = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
         "Octubre", "Noviembre", "Diciembre")
DIAS = ("Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do")
ANIO_MIN, ANIO_MAX = 2000, 2100


def parsear_fecha(texto: str) -> date | None:
    """Convierte 'DD/MM/AAAA' en date; None si el texto no es una fecha válida."""
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


class SelectorFecha(tk.Toplevel):
    """Calendario emergente. Llama a `al_elegir(date)` y se cierra al elegir un día."""

    def __init__(self, padre: tk.Misc, inicial: date | None, al_elegir, x: int, y: int) -> None:
        """Crea el calendario en (x, y) de pantalla, mostrando el mes de `inicial` (o el actual)."""
        super().__init__(padre)
        self.al_elegir = al_elegir
        self.seleccionada = inicial
        base = inicial or date.today()
        self.anio, self.mes = base.year, base.month
        self.overrideredirect(True)
        self.configure(bg=BORDE)
        self.geometry(f"+{x}+{y}")
        self.cuerpo = ttk.Frame(self, padding=8)
        self.cuerpo.pack(padx=1, pady=1)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<FocusOut>", self._perdio_foco)
        self._pintar()
        self.after(50, self._tomar_foco)

    def _tomar_foco(self) -> None:
        """Pide el foco para poder detectar cuándo el usuario hace clic fuera."""
        if self.winfo_exists():
            self.focus_force()

    def _perdio_foco(self, _e) -> None:
        """Programa el cierre si el foco no volvió al calendario (se espera un instante para evitar parpadeos)."""
        self.after(150, self._cerrar_si_sin_foco)

    def _cerrar_si_sin_foco(self) -> None:
        """Cierra el calendario si ningún widget lo tiene en foco."""
        if self.winfo_exists() and self.focus_get() is None:
            self.destroy()

    def _mover(self, delta_meses: int) -> None:
        """Navega `delta_meses` meses (±1 mes, ±12 = año), limitado a los años 2000-2100."""
        indice = self.anio * 12 + (self.mes - 1) + delta_meses
        anio, mes0 = divmod(indice, 12)
        if ANIO_MIN <= anio <= ANIO_MAX:
            self.anio, self.mes = anio, mes0 + 1
            self._pintar()

    def _elegir(self, dia: int) -> None:
        """Un día fue elegido: cierra el calendario y avisa a quien lo abrió."""
        d = date(self.anio, self.mes, dia)
        self.destroy()
        self.al_elegir(d)

    def _hoy(self) -> None:
        """Elige la fecha de hoy."""
        self.destroy()
        self.al_elegir(date.today())

    def _pintar(self) -> None:
        """Dibuja el mes actual: navegación, nombres de días y la grilla de días."""
        for w in self.cuerpo.winfo_children():
            w.destroy()
        nav = ttk.Frame(self.cuerpo)
        nav.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 4))
        for txt, delta, lado in (("«", -12, "left"), ("‹", -1, "left"), ("»", 12, "right"), ("›", 1, "right")):
            ttk.Button(nav, text=txt, width=3, command=lambda d=delta: self._mover(d)).pack(side=lado, padx=1)
        ttk.Label(nav, text=f"{MESES[self.mes - 1]} {self.anio}", font=("Segoe UI", 10, "bold"),
                  anchor="center").pack(side="left", expand=True, fill="x")
        for i, nombre in enumerate(DIAS):
            ttk.Label(self.cuerpo, text=nombre, style="Suave.TLabel", anchor="center", width=4).grid(row=1, column=i)
        hoy = date.today()
        for r, semana in enumerate(calendar.Calendar(firstweekday=0).monthdayscalendar(self.anio, self.mes)):
            for c, dia in enumerate(semana):
                if dia == 0:
                    continue
                d = date(self.anio, self.mes, dia)
                es_sel = d == self.seleccionada
                es_hoy = d == hoy
                b = tk.Button(
                    self.cuerpo, text=str(dia), width=3, relief="flat", bd=0, cursor="hand2",
                    bg=ROJO if es_sel else ("#FFF7ED" if es_hoy else "white"),
                    fg="white" if es_sel else (ROJO if c >= 5 else CARBON),
                    activebackground=NARANJA, activeforeground="white",
                    font=("Segoe UI", 9, "bold" if (es_sel or es_hoy) else "normal"),
                    command=lambda x=dia: self._elegir(x),
                )
                b.grid(row=r + 2, column=c, padx=1, pady=1)
        ttk.Button(self.cuerpo, text="Hoy", command=self._hoy).grid(row=9, column=0, columnspan=7, sticky="ew",
                                                                   pady=(6, 0))


class Campo:
    """Etiqueta + Entry con filtro de teclado + etiqueta de error en rojo.

    Si el filtro es "fecha" agrega un botón que abre un calendario.
    """

    def __init__(self, padre: tk.Misc, fila: int, etiqueta: str, filtro: str, *, col: int = 0,
                 ancho: int = 24, requerido: bool = False, sufijo: str = "", valor: str = "",
                 al_cambiar=None, al_elegir=None, columnspan: int = 1) -> None:
        """Crea etiqueta, entrada (con filtro de teclado), botón de calendario (si es fecha) y etiqueta de error.

        `filtro` elige la lista blanca de caracteres (ver FILTROS). `al_cambiar` se llama en cada cambio; `al_elegir`, al elegir una fecha en el calendario.
        """
        self.al_elegir = al_elegir
        regex, maximo = FILTROS[filtro]
        self.var = tk.StringVar(value=valor)
        marco = ttk.Frame(padre)
        marco.grid(row=fila, column=col, columnspan=columnspan, sticky="ew", padx=6, pady=(0, 4))
        marco.columnconfigure(0, weight=1)
        texto = etiqueta + (" *" if requerido else "")
        ttk.Label(marco, text=texto, style="Campo.TLabel").grid(row=0, column=0, sticky="w", columnspan=2)
        # validate="key": Tk llama a esta función ANTES de aplicar cada cambio; si devuelve False
        # el carácter se rechaza (así las letras nunca llegan a escribirse en un campo numérico).
        self.vcmd = (padre.register(lambda p, r=regex, m=maximo: len(p) <= m and bool(r.match(p))), "%P")
        self.entry = ttk.Entry(marco, textvariable=self.var, width=ancho, validate="key", validatecommand=self.vcmd)
        self.entry.grid(row=1, column=0, sticky="ew")
        if sufijo:
            ttk.Label(marco, text=sufijo, style="Suave.TLabel").grid(row=1, column=1, padx=(4, 0))
        if filtro == "fecha":
            self.boton_calendario = ttk.Button(marco, text="📅", width=3, command=self.abrir_calendario)
            self.boton_calendario.grid(row=1, column=1, padx=(4, 0))
            self.calendario: SelectorFecha | None = None
        self.error = ttk.Label(marco, text="", style="Error.TLabel", wraplength=300, justify="left")
        self.error.grid(row=2, column=0, columnspan=2, sticky="w")
        if filtro == "monto":
            self.var.trace_add("write", self._reformatear)
        if al_cambiar:
            self.var.trace_add("write", lambda *_: al_cambiar())

    def _reformatear(self, *_):
        """Reaplica los puntos de miles al escribir, conservando la posición del cursor."""
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

    def abrir_calendario(self) -> None:
        """Abre (o cierra, si ya estaba abierto) el calendario junto al campo."""
        if self.calendario is not None and self.calendario.winfo_exists():
            self.calendario.destroy()
            return
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 2
        self.calendario = SelectorFecha(self.entry, parsear_fecha(self.var.get()), self._fecha_elegida, x, y)

    def _fecha_elegida(self, d: date) -> None:
        """Escribe la fecha elegida en el campo y avisa para que se recalcule lo dependiente."""
        self.var.set(d.strftime("%d/%m/%Y"))
        if self.al_elegir:
            self.al_elegir()

    def get(self) -> str:
        """Texto actual del campo."""
        return self.var.get()

    def set(self, valor: str) -> None:
        """Reemplaza el texto del campo."""
        self.var.set(valor)

    def mostrar_error(self, mensaje: str) -> None:
        """Muestra un mensaje de error en rojo bajo el campo."""
        self.error.configure(text=mensaje)

    def limpiar_error(self) -> None:
        """Borra el mensaje de error del campo."""
        self.error.configure(text="")


def configurar_estilos(root: tk.Misc) -> None:
    """Aplica el tema y la paleta institucional (rojo, naranja, carbón) a todos los widgets ttk."""
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
