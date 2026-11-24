"""Ventana principal. Solo orquesta: lee campos -> valida -> calcula -> muestra/guarda."""
from __future__ import annotations

import logging
import os
import sys
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import formato as f
from ..calculo import ParametrosProforma, ResultadoProforma, calcular_proforma, normalizar_primer_vencimiento
from ..config import RAIZ, Config
from ..db import ErrorBaseDatos, Proforma, RepositorioProformas
from ..fechas import siguiente_dia_habil, siguiente_mes_habil
from ..pdf import ErrorPdf, generar_pdf, nombre_archivo_seguro
from ..validadores import (
    ErrorValidacion,
    validar_capital,
    validar_cuotas,
    validar_decimal,
    validar_documento,
    validar_fecha,
    validar_nombre,
    validar_observaciones,
    validar_telefono,
)
from .widgets import CARBON, Campo, configurar_estilos

log = logging.getLogger("proformas")

# Definición de columnas del cuotero: (clave, título, ancho en px, alineación).
# "Comercial" es la que ve el cliente; "Analítica" replica las columnas de la planilla Excel.
COLS_COMERCIAL = (
    ("n", "N°", 40, "center"), ("vto", "Vencimiento", 90, "center"), ("dias", "Días", 50, "center"),
    ("saldo_ini", "Saldo Inicial", 105, "e"), ("amort", "Amort. Capital", 105, "e"),
    ("gadm", "Gastos Adm.", 90, "e"), ("interes", "Interés", 90, "e"), ("iva", "IVA", 80, "e"),
    ("seguro", "Seg. Vida", 80, "e"), ("cuota", "Cuota Final", 105, "e"), ("saldo_fin", "Saldo Final", 105, "e"),
)
COLS_ANALITICA = (
    ("n", "N°", 40, "center"), ("vto", "Vencimiento", 90, "center"), ("dias", "Días", 50, "center"),
    ("saldo_ini", "Saldo Ini.", 100, "e"), ("amort", "Amort. Cap.", 100, "e"), ("gadm", "G. Adm.", 85, "e"),
    ("amort_total", "Amort. Total", 100, "e"), ("interes", "Interés", 85, "e"), ("iva", "IVA", 75, "e"),
    ("extra", "Int. Días Extra", 95, "e"), ("base", "Base + G. Adm", 100, "e"),
    ("seguro", "Seg. Nivelado", 90, "e"), ("cuota", "Cuota Final", 100, "e"), ("saldo_fin", "Saldo Fin.", 100, "e"),
)


class App(tk.Tk):
    """Ventana principal. Solo orquesta: lee los campos, valida, llama al cálculo y muestra/guarda.

    No contiene reglas de negocio (están en `calculo.py`) ni SQL (está en `db.py`).

    Estado que mantiene:
      editando  -- id de la proforma en edición (None si se está creando una nueva).
      nominal   -- 1er vencimiento original si cayó en fin de semana y se trasladó al lunes.
      resultado -- último cálculo válido (None si algún parámetro es inválido).
    """
    def __init__(self, cfg: Config, repo: RepositorioProformas) -> None:
        """Crea la ventana, aplica los estilos, arma los widgets y carga el estado inicial."""
        super().__init__()
        self.cfg = cfg
        self.repo = repo
        self.editando: int | None = None
        self.nominal: date | None = None
        self.resultado: ResultadoProforma | None = None
        self.vista = tk.StringVar(value="comercial")

        self.title("Sistema de Proformas · Fundación Industrial")
        self._poner_icono()
        self.geometry("1240x860")
        self.minsize(900, 600)
        configurar_estilos(self)
        self._construir()
        self.nueva(restablecer=True)
        self._refrescar_lista()

    # ------------------------------------------------------------------ errores internos
    def report_callback_exception(self, exc, val, tb) -> None:  # noqa: D401
        """Ningún error interno cierra la app ni muestra un traceback al usuario."""
        # Tk llama a este método cuando falla cualquier callback (clic, tecla...). Por defecto
        # imprimiría el traceback en consola; aquí se guarda en el log y se avisa con un mensaje
        # comprensible, sin cerrar la aplicación.
        log.error("Error no controlado en la interfaz", exc_info=(exc, val, tb))
        self._estado("Ocurrió un error inesperado. La operación no se completó.", error=True)
        messagebox.showerror(
            "Error inesperado",
            "Ocurrió un problema inesperado y la operación no se completó.\n"
            "Revise los datos e intente nuevamente. Sus proformas guardadas no se ven afectadas.",
        )

    # ------------------------------------------------------------------ construcción de la UI
    def _poner_icono(self) -> None:
        """Usa assets/icono.ico como ícono de la ventana (si no se encuentra, se omite sin error).

        En el ejecutable PyInstaller los recursos se descomprimen en `sys._MEIPASS`.
        """
        base = Path(getattr(sys, "_MEIPASS", RAIZ))
        try:
            self.iconbitmap(str(base / "assets" / "icono.ico"))
        except tk.TclError:
            pass

    def _construir(self) -> None:
        """Arma la estructura general: barra superior, barra de estado y el cuerpo con desplazamiento vertical."""
        barra = ttk.Frame(self, style="Oscuro.TFrame")
        barra.pack(fill="x")
        ttk.Frame(barra, height=5, style="Oscuro.TFrame").pack(fill="x")
        cab = ttk.Frame(barra, style="Oscuro.TFrame")
        cab.pack(fill="x", padx=16, pady=8)
        ttk.Label(cab, text="FUNDACIÓN INDUSTRIAL", style="Titulo.TLabel").pack(side="left")
        ttk.Label(cab, text="   Sistema de Proformas · Método Francés · Gastos Administrativos y Seguro Nivelado",
                  style="OscuroSub.TLabel").pack(side="left")
        ttk.Button(cab, text="Importar BD…", command=self.importar).pack(side="right")
        ttk.Button(cab, text="Respaldar BD…", command=self.respaldar).pack(side="right", padx=6)

        self.estado = ttk.Label(self, text="Listo.", style="Estado.TLabel", anchor="w", padding=(12, 4))
        self.estado.pack(side="bottom", fill="x")

        cont = ttk.Frame(self, style="Fondo.TFrame")
        cont.pack(fill="both", expand=True)
        # Tk no tiene un contenedor con scroll nativo: se usa un Canvas que aloja un Frame y se
        # ajusta su región desplazable cada vez que el Frame cambia de tamaño.
        self.lienzo = tk.Canvas(cont, bg="#F5F5F6", highlightthickness=0)
        sb = ttk.Scrollbar(cont, orient="vertical", command=self.lienzo.yview)
        self.lienzo.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.lienzo.pack(side="left", fill="both", expand=True)
        self.cuerpo = ttk.Frame(self.lienzo, style="Fondo.TFrame")
        self._ventana = self.lienzo.create_window((0, 0), window=self.cuerpo, anchor="nw")
        self.cuerpo.bind("<Configure>", lambda e: self.lienzo.configure(scrollregion=self.lienzo.bbox("all")))
        self.lienzo.bind("<Configure>", lambda e: self.lienzo.itemconfigure(self._ventana, width=e.width))
        self.bind_all("<MouseWheel>", self._rueda)

        self.banner = ttk.Frame(self.cuerpo, style="Aviso.TFrame", padding=8)
        self.banner_txt = ttk.Label(self.banner, text="", style="Aviso.TLabel")
        self.banner_txt.pack(side="left")
        ttk.Button(self.banner, text="Cancelar edición", command=lambda: self.nueva(restablecer=False)).pack(side="right")

        sup = ttk.Frame(self.cuerpo, style="Fondo.TFrame")
        sup.pack(fill="x", padx=12, pady=(10, 6))
        sup.columnconfigure(0, weight=2, uniform="a")
        sup.columnconfigure(1, weight=3, uniform="a")
        self._card_cliente(sup)
        self._card_parametros(sup)
        self._kpis()
        self._card_cuotero()
        self._card_guardadas()

    def _rueda(self, e: tk.Event) -> None:
        """Desplaza el cuerpo con la rueda del mouse, salvo sobre widgets que ya tienen su propio desplazamiento."""
        if isinstance(e.widget, (ttk.Treeview, tk.Text, ttk.Combobox)) or str(e.widget).endswith("combo"):
            return
        self.lienzo.yview_scroll(int(-e.delta / 120), "units")

    # ---- 1. Cliente
    def _card_cliente(self, padre: ttk.Frame) -> None:
        """Sección 1: datos del cliente y botones de acción (guardar, PDF, limpiar)."""
        card = ttk.LabelFrame(padre, text=" 1  Datos del Cliente ", style="Card.TLabelframe", padding=10)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        card.columnconfigure(0, weight=1)
        self.c_nombre = Campo(card, 0, "Nombre del Cliente / Razón Social", "nombre", requerido=True, ancho=40)
        self.c_doc = Campo(card, 1, "Nro. de Documento / C.I. / RUC / Pasaporte", "documento", requerido=True)
        ttk.Label(card, text="Ej.: 4.567.890 · 4.567.890-1 · AB123456", style="Suave.TLabel").grid(
            row=2, column=0, sticky="w", padx=6)
        self.c_tel = Campo(card, 3, "Teléfono de Contacto", "telefono", requerido=True)
        ttk.Label(card, text="Observaciones / Destino (opcional)", style="Campo.TLabel").grid(
            row=4, column=0, sticky="w", padx=6)
        self.t_obs = tk.Text(card, height=3, width=40, font=("Segoe UI", 10), wrap="word", relief="solid", bd=1)
        self.t_obs.grid(row=5, column=0, sticky="ew", padx=6)
        self.e_obs = ttk.Label(card, text="", style="Error.TLabel")
        self.e_obs.grid(row=6, column=0, sticky="w", padx=6)
        self.t_obs.bind("<KeyRelease>", lambda e: self._limitar_obs())

        botones = ttk.Frame(card)
        botones.grid(row=7, column=0, sticky="ew", pady=(10, 0))
        botones.columnconfigure((0, 1), weight=1)
        self.b_guardar = ttk.Button(botones, text="Guardar Proforma", style="Principal.TButton", command=self.guardar)
        self.b_guardar.grid(row=0, column=0, sticky="ew", padx=(6, 3))
        ttk.Button(botones, text="Generar PDF", style="Naranja.TButton", command=self.pdf_actual).grid(
            row=0, column=1, sticky="ew", padx=(3, 6))
        ttk.Button(botones, text="Limpiar / Nueva Proforma", command=lambda: self.nueva(restablecer=True)).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 0))

    def _limitar_obs(self) -> None:
        """Corta las observaciones a 300 caracteres (un Text no tiene filtro de teclado propio)."""
        txt = self.t_obs.get("1.0", "end-1c")
        if len(txt) > 300:
            self.t_obs.delete("1.0", "end")
            self.t_obs.insert("1.0", txt[:300])
            self.e_obs.configure(text="Máximo 300 caracteres.")
        else:
            self.e_obs.configure(text="")

    # ---- 2. Parámetros
    def _card_parametros(self, padre: ttk.Frame) -> None:
        """Sección 2: parámetros del cálculo, atajos rápidos y criterio de redondeo."""
        card = ttk.LabelFrame(padre, text=" 2  Parámetros — Método Francés (recálculo en vivo) ",
                              style="Card.TLabelframe", padding=10)
        card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        card.columnconfigure((0, 1), weight=1, uniform="p")
        rc = self.recalcular
        self.p_desemb = Campo(card, 0, "Fecha de Desembolso (DD/MM/AAAA)", "fecha", col=0, al_cambiar=rc,
                             al_elegir=lambda: self._al_cambiar_desembolso())
        self.p_vto = Campo(card, 0, "Primer Vencimiento (Cuota 1)", "fecha", col=1, al_cambiar=rc,
                           al_elegir=lambda: self._normalizar_vto())
        self.p_capital = Campo(card, 1, "Capital Solicitado (Gs.)", "monto", col=0, valor="10.000.000", al_cambiar=rc)
        self.p_cuotas = Campo(card, 1, "Cantidad de Cuotas Mensuales (1–120)", "entero", col=1, valor="12",
                              sufijo="meses", al_cambiar=rc)
        self.p_iva = Campo(card, 2, "Tasa de IVA (%)", "decimal", col=0, valor="10", al_cambiar=rc)
        self.p_tan = Campo(card, 2, "Tasa Anual Nominal — T.A.N. (%)", "decimal", col=1, valor="24", al_cambiar=rc)
        self.p_gastos = Campo(card, 3, "Gastos Administrativos (%)", "decimal", col=0, valor="2", al_cambiar=rc)
        self.p_seguro = Campo(card, 3, "Tasa de Seguro (% mensual)", "decimal", col=1, valor="0,25", al_cambiar=rc)
        for e in (self.p_desemb.entry, ):
            e.bind("<FocusOut>", lambda ev: self._al_cambiar_desembolso())
            e.bind("<Return>", lambda ev: self._al_cambiar_desembolso())
        self.p_vto.entry.bind("<FocusOut>", lambda ev: self._normalizar_vto())
        self.p_vto.entry.bind("<Return>", lambda ev: self._normalizar_vto())

        rapidos = ttk.Frame(card)
        rapidos.grid(row=4, column=0, columnspan=2, sticky="w", padx=6)
        ttk.Label(rapidos, text="Capital:", style="Suave.TLabel").pack(side="left")
        for txt, inc in (("+1M", 1_000_000), ("+5M", 5_000_000), ("+10M", 10_000_000)):
            ttk.Button(rapidos, text=txt, width=5, command=lambda i=inc: self._sumar_capital(i)).pack(side="left", padx=2)
        ttk.Label(rapidos, text="   Plazo:", style="Suave.TLabel").pack(side="left")
        for m in (6, 12, 18, 24, 36):
            ttk.Button(rapidos, text=f"{m}m", width=4, command=lambda x=m: self.p_cuotas.set(str(x))).pack(side="left", padx=2)
        rap2 = ttk.Frame(card)
        rap2.grid(row=5, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 0))
        ttk.Label(rap2, text="Seguro:", style="Suave.TLabel").pack(side="left")
        for txt, val in (("0,25% (Micro)", "0,25"), ("0,12% (Funcionario)", "0,12"), ("0% (Sin seguro)", "0")):
            ttk.Button(rap2, text=txt, command=lambda v=val: self.p_seguro.set(v)).pack(side="left", padx=2)

        pie = ttk.Frame(card)
        pie.grid(row=6, column=0, columnspan=2, sticky="ew", padx=6, pady=(8, 0))
        ttk.Label(pie, text="Criterio de redondeo:", style="Campo.TLabel").pack(side="left")
        self.redondeo = ttk.Combobox(pie, state="readonly", width=32, name="combo",
                                     values=("Redondeo Institucional (Entero)", "Exacto con decimales"))
        self.redondeo.current(0)
        self.redondeo.pack(side="left", padx=6)
        self.redondeo.bind("<<ComboboxSelected>>", lambda e: self.recalcular())
        self.lbl_tasas = ttk.Label(card, text="", style="Ayuda.TLabel", justify="left")
        self.lbl_tasas.grid(row=7,column=0, columnspan=2, sticky="w", padx=6, pady=(8, 0))
        self.lbl_fechas = ttk.Label(card, text="", style="Ayuda.TLabel", justify="left")
        self.lbl_fechas.grid(row=8,column=0, columnspan=2, sticky="w", padx=6)

    def _sumar_capital(self, inc: int) -> None:
        """Suma `inc` al capital actual (tope: 100.000.000.000). Si el capital es inválido parte de 0."""
        try:
            actual = validar_capital(self.p_capital.get())
        except ErrorValidacion:
            actual = 0
        self.p_capital.set(f.miles(min(actual + inc, 100_000_000_000)))

    # ---- KPIs
    def _kpis(self) -> None:
        """Fila de 4 tarjetas con los indicadores: cuota final, base + gastos, seguro nivelado y total."""
        fila = ttk.Frame(self.cuerpo, style="Fondo.TFrame")
        fila.pack(fill="x", padx=12, pady=6)
        fila.columnconfigure((0, 1, 2, 3), weight=1, uniform="k")
        self.kpi = {}
        defs = (("cuota", "CUOTA FINAL MENSUAL"), ("base", "BASE + G. ADM"),
                ("seguro", "SEGURO NIVELADO MENSUAL"), ("total", "TOTAL GENERAL A PAGAR"))
        for i, (clave, titulo) in enumerate(defs):
            tarjeta = ttk.Frame(fila, padding=10, relief="solid", borderwidth=1)
            tarjeta.grid(row=0, column=i, sticky="nsew", padx=4)
            ttk.Label(tarjeta, text=titulo, style="KpiTitulo.TLabel").pack(anchor="w")
            v = ttk.Label(tarjeta, text="—", style="KpiValor.TLabel")
            v.pack(anchor="w")
            s = ttk.Label(tarjeta, text="", style="KpiSub.TLabel")
            s.pack(anchor="w")
            self.kpi[clave] = (v, s)

    # ---- 3. Cuotero
    def _card_cuotero(self) -> None:
        """Sección 3: tabla del cuotero con selector de vista comercial / analítica."""
        card = ttk.LabelFrame(self.cuerpo, text=" 3  Vista Previa del Cuotero ", style="Card.TLabelframe", padding=8)
        card.pack(fill="x", padx=12, pady=6)
        sel = ttk.Frame(card)
        sel.pack(fill="x")
        ttk.Radiobutton(sel, text="Vista Comercial (Cliente)", value="comercial", variable=self.vista,
                        command=self._pintar_cuotero).pack(side="left", padx=4)
        ttk.Radiobutton(sel, text="Vista Analítica Completa", value="analitica", variable=self.vista,
                        command=self._pintar_cuotero).pack(side="left", padx=12)
        cont = ttk.Frame(card)
        cont.pack(fill="x", pady=(6, 0))
        self.tv_cuotero = ttk.Treeview(cont, show="headings", height=10)
        sy = ttk.Scrollbar(cont, orient="vertical", command=self.tv_cuotero.yview)
        sx = ttk.Scrollbar(card, orient="horizontal", command=self.tv_cuotero.xview)
        self.tv_cuotero.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tv_cuotero.pack(side="left", fill="x", expand=True)
        sy.pack(side="right", fill="y")
        sx.pack(fill="x")
        self.tv_cuotero.tag_configure("total", background=CARBON, foreground="#F7D100")
        self.tv_cuotero.tag_configure("cero", background="#FFFBEB")

    # ---- 4. Guardadas
    def _card_guardadas(self) -> None:
        """Sección 4: proformas guardadas, buscador y acciones (editar, PDF, eliminar)."""
        card = ttk.LabelFrame(self.cuerpo, text=" 4  Proformas Guardadas (SQLite) ", style="Card.TLabelframe", padding=8)
        card.pack(fill="x", padx=12, pady=(6, 14))
        top = ttk.Frame(card)
        top.pack(fill="x")
        self.lbl_cant = ttk.Label(top, text="0 registros", style="Suave.TLabel")
        self.lbl_cant.pack(side="left")
        self.busqueda = tk.StringVar()
        ttk.Entry(top, textvariable=self.busqueda, width=40).pack(side="right")
        ttk.Label(top, text="Buscar (cliente, C.I., teléfono o N° operación):", style="Suave.TLabel").pack(side="right", padx=6)
        self.busqueda.trace_add("write", lambda *_: self._refrescar_lista())
        cols = (("op", "N° Operación", 110, "center"), ("fecha", "Fecha", 120, "center"), ("cliente", "Cliente", 220, "w"),
                ("doc", "Documento", 100, "center"), ("tel", "Teléfono", 110, "center"), ("capital", "Capital", 110, "e"),
                ("plazo", "Cuotas / TAN", 100, "center"), ("cuota", "Cuota Mensual", 110, "e"),
                ("total", "Total a Pagar", 120, "e"))
        cont = ttk.Frame(card)
        cont.pack(fill="x", pady=6)
        self.tv_guardadas = ttk.Treeview(cont, columns=[c[0] for c in cols], show="headings", height=6,
                                         selectmode="browse")
        for clave, titulo, ancho, ancla in cols:
            self.tv_guardadas.heading(clave, text=titulo)
            self.tv_guardadas.column(clave, width=ancho, anchor=ancla, stretch=True)
        sy = ttk.Scrollbar(cont, orient="vertical", command=self.tv_guardadas.yview)
        self.tv_guardadas.configure(yscrollcommand=sy.set)
        self.tv_guardadas.pack(side="left", fill="x", expand=True)
        sy.pack(side="right", fill="y")
        self.tv_guardadas.bind("<Double-1>", lambda e: self.editar_seleccion())
        acc = ttk.Frame(card)
        acc.pack(fill="x")
        ttk.Button(acc, text="Editar", command=self.editar_seleccion).pack(side="left", padx=(0, 6))
        ttk.Button(acc, text="Descargar PDF", command=self.pdf_seleccion).pack(side="left", padx=6)
        ttk.Button(acc, text="Eliminar", style="Peligro.TButton", command=self.eliminar_seleccion).pack(side="left", padx=6)

    # ------------------------------------------------------------------ utilidades UI
    def _estado(self, texto: str, error: bool = False) -> None:
        """Muestra un mensaje en la barra de estado (✔ éxito, ⚠ problema)."""
        self.estado.configure(text=("⚠ " if error else "✔ ") + texto)

    def _campos_param(self) -> dict[str, Campo]:
        """Mapa 'clave de validación -> Campo' de los parámetros, para mostrar cada error junto a su campo."""
        return {"desembolso": self.p_desemb, "primer_vto": self.p_vto, "capital": self.p_capital,
                "cuotas": self.p_cuotas, "iva": self.p_iva, "tan": self.p_tan, "gastos": self.p_gastos,
                "seguro": self.p_seguro}

    # ------------------------------------------------------------------ fechas
    def _al_cambiar_desembolso(self) -> None:
        """Al cambiar el desembolso, propone el 1er vencimiento habitual (+1 mes hábil) y descarta el traslado manual."""
        try:
            d = validar_fecha("desembolso", "la fecha de desembolso", self.p_desemb.get())
        except ErrorValidacion:
            return
        self.nominal = None
        self.p_vto.set(f.fecha_dmy(siguiente_mes_habil(d)))

    def _normalizar_vto(self) -> None:
        """Valida el 1er vencimiento: no puede ser anterior al desembolso; si cae en fin de semana lo pasa al lunes."""
        try:
            d = validar_fecha("primer_vto", "el primer vencimiento", self.p_vto.get())
            des = validar_fecha("desembolso", "la fecha de desembolso", self.p_desemb.get())
        except ErrorValidacion:
            return
        if d < des:
            self.p_vto.set(f.fecha_dmy(siguiente_dia_habil(des)))
            self.nominal = None
            self._estado("El 1er vencimiento no puede ser anterior al desembolso; se ajustó.", error=True)
            return
        habil, nominal = normalizar_primer_vencimiento(d, des)
        self.nominal = nominal
        if nominal:
            self.p_vto.set(f.fecha_dmy(habil))
            self._estado("El 1er vencimiento caía en fin de semana: se trasladó al lunes hábil sin recargo de interés.")

    # ------------------------------------------------------------------ lectura y validación
    def _validar_parametros(self) -> tuple[ParametrosProforma | None, dict[str, str]]:
        """Valida todos los parámetros a la vez.

        Devuelve (ParametrosProforma, {}) si todo es válido o (None, {clave: mensaje}) si hay errores, de modo que se puedan marcar todos los campos incorrectos en una sola pasada.
        """
        errores: dict[str, str] = {}
        val: dict = {}

        def intentar(clave: str, fn):
            """Ejecuta una validación y guarda su valor o su mensaje de error."""
            try:
                val[clave] = fn()
            except ErrorValidacion as e:
                errores[clave] = e.mensaje

        intentar("desembolso", lambda: validar_fecha("desembolso", "la fecha de desembolso", self.p_desemb.get()))
        intentar("primer_vto", lambda: validar_fecha("primer_vto", "el primer vencimiento", self.p_vto.get()))
        intentar("capital", lambda: validar_capital(self.p_capital.get()))
        intentar("cuotas", lambda: validar_cuotas(self.p_cuotas.get()))
        intentar("iva", lambda: validar_decimal("iva", "la tasa de IVA", self.p_iva.get(), 0, 50))
        intentar("tan", lambda: validar_decimal("tan", "la T.A.N.", self.p_tan.get(), 0, 200))
        intentar("gastos", lambda: validar_decimal("gastos", "el porcentaje de gastos", self.p_gastos.get(), 0, 50))
        intentar("seguro", lambda: validar_decimal("seguro", "la tasa de seguro", self.p_seguro.get(), 0, 10))
        if "desembolso" in val and "primer_vto" in val and val["primer_vto"] < val["desembolso"]:
            errores["primer_vto"] = "El primer vencimiento no puede ser anterior al desembolso."
        if errores:
            return None, errores
        habil, nominal = normalizar_primer_vencimiento(val["primer_vto"], val["desembolso"])
        # Si el campo ya muestra el lunes al que se trasladó un vencimiento de fin de semana,
        # se conserva la fecha original (nominal): el cálculo la necesita para contar los meses.
        if nominal is None and self.nominal and habil == siguiente_dia_habil(self.nominal):
            nominal = self.nominal
        return ParametrosProforma(
            capital=val["capital"], tasa_anual=val["tan"], cuotas=val["cuotas"], iva_pct=val["iva"],
            pct_gastos=val["gastos"], tasa_seguro=val["seguro"], redondear=self.redondeo.current() == 0,
            fecha_desembolso=val["desembolso"], primer_vencimiento=habil, primer_vto_nominal=nominal,
        ), errores

    def _validar_cliente(self) -> tuple[dict, dict[str, str]]:
        """Valida los datos del cliente. Devuelve (valores normalizados, {clave: mensaje de error})."""
        errores: dict[str, str] = {}
        val: dict = {}
        for clave, fn, campo in (
            ("nombre", validar_nombre, self.c_nombre), ("documento", validar_documento, self.c_doc),
            ("telefono", validar_telefono, self.c_tel),
        ):
            try:
                val[clave] = fn(campo.get())
            except ErrorValidacion as e:
                errores[clave] = e.mensaje
        try:
            val["observaciones"] = validar_observaciones(self.t_obs.get("1.0", "end-1c"))
        except ErrorValidacion as e:
            errores["observaciones"] = e.mensaje
        return val, errores

    def _mostrar_errores_cliente(self, errores: dict[str, str]) -> None:
        """Escribe (o limpia) el mensaje de error bajo cada campo del cliente."""
        for clave, campo in (("nombre", self.c_nombre), ("documento", self.c_doc), ("telefono", self.c_tel)):
            campo.mostrar_error(errores.get(clave, ""))
        self.e_obs.configure(text=errores.get("observaciones", ""))

    # ------------------------------------------------------------------ cálculo en vivo
    def recalcular(self) -> None:
        """Recalcula en vivo. Con parámetros inválidos marca los errores y limpia el resultado, sin romper."""
        params, errores = self._validar_parametros()
        for clave, campo in self._campos_param().items():
            campo.mostrar_error(errores.get(clave, ""))
        if params is None:
            self.resultado = None
            self._limpiar_resultados()
            return
        self.resultado = calcular_proforma(params)
        self._mostrar_resultado(self.resultado)

    def _limpiar_resultados(self) -> None:
        """Deja las tarjetas, las tasas y el cuotero vacíos (parámetros inválidos)."""
        for v, s in self.kpi.values():
            v.configure(text="—")
            s.configure(text="Corrija los parámetros marcados")
        self.lbl_tasas.configure(text="")
        self.lbl_fechas.configure(text="")
        self.tv_cuotero.delete(*self.tv_cuotero.get_children())

    def _mostrar_resultado(self, r: ResultadoProforma) -> None:
        """Vuelca el resultado del cálculo en las tarjetas, el resumen de tasas/fechas y el cuotero."""
        d = r.decimales
        p = r.params
        self.kpi["cuota"][0].configure(text=f.gs(r.cuota_final, d))
        self.kpi["cuota"][1].configure(text=f"{p.cuotas} cuotas · 1er Vto: {f.fecha_dmy(r.cuotero[0].vencimiento)}")
        self.kpi["base"][0].configure(text=f.gs(r.cuota_base_gastos, d))
        self.kpi["base"][1].configure(text=f"Incluye G. Adm. ({f.gs(r.g_adm_mensual, d)}/mes)")
        self.kpi["seguro"][0].configure(text=f.gs(r.seguro_nivelado, d))
        self.kpi["seguro"][1].configure(text=f"Total seguro: {f.gs(r.totales.seguro, d)}")
        self.kpi["total"][0].configure(text=f.gs(r.totales.cuota_final, d))
        self.kpi["total"][1].configure(text=f"Int. + IVA: {f.gs(r.totales.interes + r.totales.iva, d)}")
        self.lbl_tasas.configure(
            text=f"T.A.E. (Efectiva Anual): {f.porcentaje(r.tae_pct)}   ·   Tasa anual c/ IVA: "
                 f"{f.porcentaje(r.tasa_anual_iva_pct)}   ·   Mensual / c/ IVA: {f.miles(r.i_mensual_pct, 4)}% / "
                 f"{f.miles(r.i_mensual_iva_pct, 4)}%\n"
                 f"Gastos Adm. + IVA: {f.gs(r.g_adm_total, d)} ({f.gs(r.g_adm_mensual, d)}/mes)")
        if r.primer_vto_modificado:
            extra = f"1er vto modificado: {r.meses_interes_primer_periodo} meses de interés (regla legado)"
        elif r.dias_excedentes > 0:
            extra = f"+{r.dias_excedentes} días extra: {f.gs(r.extra_total_cuota, d)}/cuota"
        elif r.dias_traslado_fin_semana > 0:
            extra = "Sin recargo (traslado a día hábil)"
        else:
            extra = "Sin recargo (≤ 30 días)"
        self.lbl_fechas.configure(
            text=f"Plazo total de la operación: {r.plazo_dias_total} días   ·   Días al 1er vto: {r.dias_primer_vto}   ·   {extra}")
        self._pintar_cuotero()

    def _pintar_cuotero(self) -> None:
        """Redibuja la tabla del cuotero según la vista elegida y agrega la fila de totales."""
        tv = self.tv_cuotero
        tv.delete(*tv.get_children())
        analitica = self.vista.get() == "analitica"
        cols = COLS_ANALITICA if analitica else COLS_COMERCIAL
        tv.configure(columns=[c[0] for c in cols])
        for clave, titulo, ancho, ancla in cols:
            tv.heading(clave, text=titulo)
            tv.column(clave, width=ancho, anchor=ancla, stretch=False)
        r = self.resultado
        if r is None:
            return
        d = r.decimales
        m = lambda v: f.miles(v, d)  # noqa: E731
        t = r.totales
        for x in r.cuotero:
            if analitica:
                vals = (x.cuota, f.fecha_dmy(x.vencimiento), x.dias, m(x.saldo_inicial), m(x.amort_capital), m(x.g_adm),
                        m(x.amort_total), m(x.interes), m(x.iva), m(x.extra_dias), m(x.cuota_base_gastos),
                        m(x.seguro), m(x.cuota_final), m(x.saldo_final))
            else:
                vals = (x.cuota, f.fecha_dmy(x.vencimiento), x.dias, m(x.saldo_inicial), m(x.amort_capital), m(x.g_adm),
                        m(x.interes), m(x.iva), m(x.seguro), m(x.cuota_final), m(x.saldo_final))
            tv.insert("", "end", values=vals)
        if analitica:
            tot = ("", "TOTALES", "", "", m(t.amort_capital), m(t.g_adm), m(t.amort_total), m(t.interes), m(t.iva),
                   m(t.extra_dias), m(t.base_gastos), m(t.seguro), m(t.cuota_final), "0")
        else:
            tot = ("", "TOTALES", "", "", m(t.amort_capital), m(t.g_adm), m(t.interes), m(t.iva), m(t.seguro),
                   m(t.cuota_final), "0")
        tv.insert("", "end", values=tot, tags=("total",))

    # ------------------------------------------------------------------ acciones
    def _datos_para_guardar(self) -> tuple[dict, ResultadoProforma, dict] | None:
        """Valida cliente y parámetros y arma el diccionario a persistir.

        Si hay errores los muestra (campos en rojo + aviso con la lista) y devuelve None.
        """
        cliente, err_c = self._validar_cliente()
        params, err_p = self._validar_parametros()
        self._mostrar_errores_cliente(err_c)
        for clave, campo in self._campos_param().items():
            campo.mostrar_error(err_p.get(clave, ""))
        if err_c or err_p:
            lista = "\n".join("• " + m for m in [*err_c.values(), *err_p.values()])
            self._estado("Hay datos incorrectos o incompletos. Revise los campos marcados en rojo.", error=True)
            messagebox.showwarning("Revise los datos", "No se pudo continuar:\n\n" + lista)
            return None
        resultado = calcular_proforma(params)
        datos = {
            "nombre_cliente": cliente["nombre"], "documento": cliente["documento"],
            "telefono": cliente["telefono"], "observaciones": cliente["observaciones"],
            "fecha_desembolso": params.fecha_desembolso.isoformat(),
            "primer_vencimiento": params.primer_vencimiento.isoformat(),
            "primer_vto_nominal": params.primer_vto_nominal.isoformat() if params.primer_vto_nominal else None,
            "capital": params.capital, "tasa_anual": params.tasa_anual, "cuotas": params.cuotas,
            "iva_pct": params.iva_pct, "pct_gastos": params.pct_gastos, "tasa_seguro": params.tasa_seguro,
            "redondeo_entero": 1 if params.redondear else 0,
            "cuota_base_gastos": resultado.cuota_base_gastos, "seguro_mensual": resultado.seguro_nivelado,
            "cuota_final": resultado.cuota_final, "total_pagar": resultado.totales.cuota_final,
        }
        return datos, resultado, cliente

    def guardar(self) -> None:
        """Guarda una proforma nueva o actualiza la que se está editando."""
        pre = self._datos_para_guardar()
        if pre is None:
            return
        datos, _, _ = pre
        try:
            if self.editando is None:
                p = self.repo.crear(datos)
                self._poner_edicion(p)
                self._estado(f"Proforma {p.nro_operacion} guardada para {p.nombre_cliente}.")
            else:
                p = self.repo.actualizar(self.editando, datos)
                self._estado(f"Proforma {p.nro_operacion} actualizada correctamente.")
                self.nueva(restablecer=False)
        except ErrorBaseDatos as e:
            log.exception("Error de base de datos al guardar")
            self._estado(str(e), error=True)
            messagebox.showerror("No se pudo guardar", str(e))
            return
        self._refrescar_lista()

    def pdf_actual(self) -> None:
        """Genera el PDF de lo que hay en pantalla (exige datos válidos del cliente; no requiere haber guardado)."""
        pre = self._datos_para_guardar()
        if pre is None:
            return
        datos, resultado, cliente = pre
        nro = ""
        if self.editando is not None:
            reg = self.repo.obtener(self.editando)
            nro = reg.nro_operacion if reg else ""
        self._emitir_pdf(resultado, nro, f.iso_a_dmy_hora(f.ahora_iso()), cliente["nombre"], cliente["documento"],
                         cliente["telefono"], cliente["observaciones"])

    def pdf_seleccion(self) -> None:
        """Genera el PDF de la proforma seleccionada en la lista, recalculándola desde sus parámetros."""
        reg = self._seleccion()
        if reg is None:
            return
        resultado = calcular_proforma(self._params_de(reg))
        self._emitir_pdf(resultado, reg.nro_operacion, f.iso_a_dmy_hora(reg.fecha_creacion), reg.nombre_cliente,
                         reg.documento, reg.telefono, reg.observaciones)

    def _emitir_pdf(self, resultado, nro, emision, nombre, documento, telefono, obs) -> None:
        """Escribe el PDF en la carpeta configurada con un nombre seguro y lo abre con el visor predeterminado."""
        archivo = f"Proforma_{nro or 'SIN_GUARDAR'}_{nombre_archivo_seguro(nombre)}.pdf"
        try:
            ruta = generar_pdf(self.cfg.pdf_dir / archivo, resultado, self.cfg, nro_operacion=nro,
                               fecha_emision=emision, nombre=nombre, documento=documento, telefono=telefono,
                               observaciones=obs)
        except ErrorPdf as e:
            log.exception("Error al generar PDF")
            self._estado(str(e), error=True)
            messagebox.showerror("No se pudo generar el PDF", str(e))
            return
        self._estado(f"PDF generado: {ruta}")
        try:
            os.startfile(ruta)  # type: ignore[attr-defined]  # solo Windows
        except (AttributeError, OSError):
            messagebox.showinfo("PDF generado", f"El PDF se guardó en:\n{ruta}")

    @staticmethod
    def _params_de(reg: Proforma) -> ParametrosProforma:
        """Reconstruye los parámetros de cálculo a partir de un registro guardado."""
        return ParametrosProforma(
            capital=reg.capital, tasa_anual=reg.tasa_anual, cuotas=reg.cuotas, iva_pct=reg.iva_pct,
            pct_gastos=reg.pct_gastos, tasa_seguro=reg.tasa_seguro, redondear=bool(reg.redondeo_entero),
            fecha_desembolso=date.fromisoformat(reg.fecha_desembolso),
            primer_vencimiento=date.fromisoformat(reg.primer_vencimiento),
            primer_vto_nominal=date.fromisoformat(reg.primer_vto_nominal) if reg.primer_vto_nominal else None,
        )

    def _seleccion(self) -> Proforma | None:
        """Devuelve la proforma seleccionada en la lista (avisa si no hay ninguna o si ya no existe)."""
        sel = self.tv_guardadas.selection()
        if not sel:
            messagebox.showinfo("Seleccione una proforma", "Primero seleccione una proforma de la lista.")
            return None
        try:
            reg = self.repo.obtener(int(sel[0]))
        except ErrorBaseDatos as e:
            messagebox.showerror("Error", str(e))
            return None
        if reg is None:
            self._refrescar_lista()
            messagebox.showinfo("No encontrada", "La proforma seleccionada ya no existe.")
        return reg

    def editar_seleccion(self) -> None:
        """Carga la proforma seleccionada en el formulario y entra en modo edición."""
        reg = self._seleccion()
        if reg is None:
            return
        self.nueva(restablecer=False)
        self.c_nombre.set(reg.nombre_cliente)
        self.c_doc.set(reg.documento)
        self.c_tel.set(reg.telefono)
        self.t_obs.delete("1.0", "end")
        self.t_obs.insert("1.0", reg.observaciones)
        self.p_desemb.set(f.fecha_iso_a_dmy(reg.fecha_desembolso))
        self.p_vto.set(f.fecha_iso_a_dmy(reg.primer_vencimiento))
        self.nominal = date.fromisoformat(reg.primer_vto_nominal) if reg.primer_vto_nominal else None
        self.p_capital.set(f.miles(reg.capital))
        self.p_cuotas.set(str(reg.cuotas))
        self.p_iva.set(f"{reg.iva_pct:g}".replace(".", ","))
        self.p_tan.set(f"{reg.tasa_anual:g}".replace(".", ","))
        self.p_gastos.set(f"{reg.pct_gastos:g}".replace(".", ","))
        self.p_seguro.set(f"{reg.tasa_seguro:g}".replace(".", ","))
        self.redondeo.current(0 if reg.redondeo_entero else 1)
        self._poner_edicion(reg)
        self.recalcular()
        self.lienzo.yview_moveto(0)
        self._estado(f"Editando proforma {reg.nro_operacion} de {reg.nombre_cliente}.")

    def _poner_edicion(self, reg: Proforma) -> None:
        """Muestra el aviso 'Modo edición' y cambia el texto del botón guardar."""
        self.editando = reg.id
        self.banner_txt.configure(text=f"Modo edición — Proforma {reg.nro_operacion}: al guardar se actualiza el registro.")
        self.banner.pack(fill="x", padx=12, pady=(10, 0), before=self.cuerpo.winfo_children()[1])
        self.b_guardar.configure(text=f"Actualizar Proforma {reg.nro_operacion}")

    def eliminar_seleccion(self) -> None:
        """Elimina la proforma seleccionada, previa confirmación explícita del usuario."""
        reg = self._seleccion()
        if reg is None:
            return
        if not messagebox.askyesno(
            "Eliminar proforma",
            f"¿Eliminar la proforma {reg.nro_operacion} de «{reg.nombre_cliente}» ({f.gs(reg.capital)})?\n\n"
            "Esta acción no se puede deshacer.", icon="warning", default="no",
        ):
            return
        try:
            self.repo.eliminar(reg.id)
        except ErrorBaseDatos as e:
            self._estado(str(e), error=True)
            messagebox.showerror("No se pudo eliminar", str(e))
            return
        if self.editando == reg.id:
            self.nueva(restablecer=False)
        self._refrescar_lista()
        self._estado(f"Proforma {reg.nro_operacion} eliminada.")

    def nueva(self, restablecer: bool) -> None:
        """Sale del modo edición. Con restablecer=True deja los parámetros por defecto."""
        self.editando = None
        self.nominal = None
        self.banner.pack_forget()
        self.b_guardar.configure(text="Guardar Proforma")
        for c in (self.c_nombre, self.c_doc, self.c_tel):
            c.set("")
            c.limpiar_error()
        self.t_obs.delete("1.0", "end")
        self.e_obs.configure(text="")
        if restablecer:
            hoy = date.today()
            self.p_desemb.set(f.fecha_dmy(hoy))
            self.p_vto.set(f.fecha_dmy(siguiente_mes_habil(hoy)))
            self.p_capital.set("10.000.000")
            self.p_cuotas.set("12")
            self.p_iva.set("10")
            self.p_tan.set("24")
            self.p_gastos.set("2")
            self.p_seguro.set("0,25")
            self.redondeo.current(0)
        self.recalcular()

    def _refrescar_lista(self) -> None:
        """Recarga la lista de proformas guardadas aplicando el filtro del buscador."""
        try:
            filas = self.repo.listar(self.busqueda.get())
        except ErrorBaseDatos as e:
            self._estado(str(e), error=True)
            return
        tv = self.tv_guardadas
        tv.delete(*tv.get_children())
        for p in filas:
            d = 0 if p.redondeo_entero else 2
            tv.insert("", "end", iid=str(p.id), values=(
                p.nro_operacion, f.iso_a_dmy_hora(p.fecha_creacion), p.nombre_cliente, p.documento, p.telefono,
                f.gs(p.capital), f"{p.cuotas}m · {f.miles(p.tasa_anual, 1)}%", f.gs(p.cuota_final, d),
                f.gs(p.total_pagar, d)))
        self.lbl_cant.configure(text=f"{len(filas)} registro(s)")

    def importar(self) -> None:
        """Importa un respaldo (.db): combinar con lo actual o reemplazarlo (con copia automática)."""
        origen = filedialog.askopenfilename(
            title="Seleccione el respaldo de la base de datos a importar",
            filetypes=[("Base de datos SQLite", "*.db *.sqlite *.sqlite3"), ("Todos los archivos", "*.*")])
        if not origen:
            return
        eleccion = messagebox.askyesnocancel(
            "Importar base de datos",
            "¿Cómo desea importar las proformas del respaldo?\n\n"
            "SÍ  →  COMBINAR: agrega las proformas que no tiene, sin borrar las actuales.\n"
            "NO  →  REEMPLAZAR: borra las proformas actuales y deja las del respaldo\n"
            "            (se guarda antes una copia automática de seguridad).\n"
            "CANCELAR  →  no hacer nada.",
            icon="question", default="yes")
        if eleccion is None:
            return
        modo = "combinar" if eleccion else "reemplazar"
        if modo == "reemplazar" and not messagebox.askyesno(
                "Confirmar reemplazo",
                "Se eliminarán todas las proformas actuales y se cargarán las del respaldo.\n\n¿Desea continuar?",
                icon="warning", default="no"):
            return
        copia = self.cfg.db_path.parent / "backups" / f"antes_de_importar_{datetime.now():%Y%m%d_%H%M%S}.db"
        try:
            res = self.repo.importar(origen, modo, copia_previa=copia)
        except ErrorBaseDatos as e:
            log.warning("Importación rechazada: %s", e)
            self._estado(str(e), error=True)
            messagebox.showerror("No se pudo importar", str(e))
            return
        self.nueva(restablecer=False)
        self._refrescar_lista()
        partes = [f"Importadas: {res.importadas}"]
        if res.duplicadas:
            partes.append(f"ya existentes (omitidas): {res.duplicadas}")
        if res.invalidas:
            partes.append(f"descartadas por datos inválidos: {res.invalidas}")
        texto = " · ".join(partes)
        if res.copia_previa:
            texto += f"\n\nCopia de seguridad previa:\n{res.copia_previa}"
        self._estado(f"Importación ({modo}) finalizada. " + " · ".join(partes))
        messagebox.showinfo("Importación finalizada", texto)

    def respaldar(self) -> None:
        """Guarda una copia de la base de datos en la ubicación que elija el usuario."""
        destino = filedialog.asksaveasfilename(
            title="Guardar respaldo de la base de datos", defaultextension=".db",
            initialfile=f"Proformas_respaldo_{date.today().isoformat()}.db", filetypes=[("Base de datos SQLite", "*.db")])
        if not destino:
            return
        try:
            self.repo.respaldar(destino)
        except ErrorBaseDatos as e:
            self._estado(str(e), error=True)
            messagebox.showerror("No se pudo respaldar", str(e))
            return
        self._estado(f"Respaldo guardado en {destino}")
