"""Generación del PDF de la proforma (cuotero) con reportlab.

Diseño:
  * Página 1: encabezado institucional (logo, título, N° de operación, RUC), panel con los datos
    del solicitante, tarjetas con los 4 indicadores clave y el inicio del cuotero.
  * Páginas siguientes: encabezado compacto y la continuación del cuotero (la fila de títulos
    de la tabla se repite en cada página).
  * Pie en todas las páginas: tira tricolor, leyenda y "Página X de Y".

Se usan dos plantillas de página (PageTemplate) para que las páginas 2+ no desperdicien el
espacio que ocupa el encabezado grande de la primera.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as lienzo_pdf
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .calculo import ResultadoProforma
from .config import Config
from .formato import fecha_dmy, gs, miles

# --- Paleta institucional (la misma del prototipo web) ---------------------------------------
ROJO = colors.HexColor("#D11D27")
AMARILLO = colors.HexColor("#F7D100")
AMBAR = colors.HexColor("#D97706")
NARANJA = colors.HexColor("#F16522")
CARBON = colors.HexColor("#18181B")
GRIS_TEXTO = colors.HexColor("#52525B")
GRIS_SUAVE = colors.HexColor("#71717A")
GRIS_FONDO = colors.HexColor("#F4F4F5")
GRIS_LINEA = colors.HexColor("#E4E4E7")
ROSA_SUAVE = colors.HexColor("#FEF2F2")

ANCHO, ALTO = A4
MARGEN = 14 * mm  # margen lateral
ALTO_CABECERA_P1 = 44 * mm  # espacio reservado al encabezado de la página 1
ALTO_CABECERA_PN = 20 * mm  # y al encabezado compacto de las demás
ALTO_PIE = 16 * mm


class ErrorPdf(Exception):
    """No se pudo generar el PDF (el mensaje es apto para mostrar al usuario)."""


def nombre_archivo_seguro(texto: str) -> str:
    """Convierte un texto cualquiera en un nombre de archivo seguro.

    Deja solo [A-Z0-9_]: evita path traversal (``../``) y caracteres inválidos en Windows.
    """
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^A-Z0-9]+", "_", sin_tildes.upper()).strip("_")
    return (limpio or "PROFORMA")[:40]


# =============================================================================================
# Elementos gráficos de página (se dibujan directamente sobre el canvas)
# =============================================================================================
def _tira_tricolor(c, y: float, alto: float = 1.3 * mm) -> None:
    """Dibuja la barra de acento rojo / amarillo / naranja con el ancho útil de la página."""
    ancho_util = ANCHO - 2 * MARGEN
    x = MARGEN
    for color, fraccion in ((ROJO, 0.45), (AMARILLO, 0.30), (NARANJA, 0.25)):
        c.setFillColor(color)
        c.rect(x, y, ancho_util * fraccion, alto, stroke=0, fill=1)
        x += ancho_util * fraccion


def _logo(c, x: float, y: float, escala: float = 0.16) -> None:
    """Logotipo vectorial (trazos rojo, amarillo y naranja) con el nombre de la institución.

    Las coordenadas originales (0..140) vienen del SVG del prototipo web, cuyo eje Y crece hacia
    abajo; la función `p` las convierte al sistema de reportlab (Y hacia arriba).
    """
    c.saveState()
    c.setLineCap(1)  # extremos redondeados
    c.setLineJoin(1)
    c.setLineWidth(10 * escala * mm)
    s = escala * mm

    def p(px: float, py: float) -> tuple[float, float]:
        """Convierte coordenadas del SVG (Y hacia abajo) al sistema de reportlab (Y hacia arriba)."""
        return x + px * s, y + (140 - py) * s

    c.setStrokeColor(ROJO)  # "F" diagonal
    ruta = c.beginPath()
    ruta.moveTo(*p(72, 36))
    ruta.lineTo(*p(26, 82))
    ruta.lineTo(*p(88, 144))
    c.drawPath(ruta, stroke=1, fill=0)
    c.line(*p(57, 113), *p(93, 77))
    c.setStrokeColor(AMARILLO)  # flecha ascendente
    c.line(*p(55.5, 83.5), *p(121.5, 17.5))
    ruta = c.beginPath()
    ruta.moveTo(*p(89.5, 17.5))
    ruta.lineTo(*p(121.5, 17.5))
    ruta.lineTo(*p(121.5, 49.5))
    c.drawPath(ruta, stroke=1, fill=0)
    c.setStrokeColor(NARANJA)  # barra inferior
    c.line(*p(85.5, 115.5), *p(108.5, 92.5))
    c.restoreState()

    c.setFillColor(CARBON)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 27 * mm, y + 15.5 * mm, "FUNDACIÓN")
    c.drawString(x + 27 * mm, y + 9 * mm, "INDUSTRIAL")


class _LienzoNumerado(lienzo_pdf.Canvas):
    """Canvas que dibuja el pie en todas las páginas con "Página X de Y".

    Para conocer el total de páginas hay que esperar a terminar el documento: se guardan los
    estados de cada página y recién en `save()` se dibuja el pie con el total conocido.
    """

    def __init__(self, *args, leyenda: str = "", **kwargs) -> None:
        """Guarda la leyenda del pie y prepara la lista de estados de página."""
        super().__init__(*args, **kwargs)
        self._estados: list[dict] = []
        self._leyenda = leyenda

    def showPage(self) -> None:  # noqa: N802 (nombre impuesto por reportlab)
        """Intercepta el fin de cada página para guardar su estado en lugar de cerrarla."""
        self._estados.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        """Con el total de páginas ya conocido, dibuja el pie en cada una y escribe el archivo."""
        total = len(self._estados)
        for estado in self._estados:
            self.__dict__.update(estado)
            self._pie(total)
            super().showPage()
        super().save()

    def _pie(self, total: int) -> None:
        """Dibuja tira tricolor, leyenda institucional y 'Página X de Y'."""
        _tira_tricolor(self, 9 * mm)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(GRIS_SUAVE)
        self.drawString(MARGEN, 13 * mm, self._leyenda)
        self.drawRightString(ANCHO - MARGEN, 13 * mm, f"Página {self._pageNumber} de {total}")


# =============================================================================================
# Generación del documento
# =============================================================================================
def generar_pdf(
    destino: Path,
    resultado: ResultadoProforma,
    cfg: Config,
    *,
    nro_operacion: str,
    fecha_emision: str,
    nombre: str,
    documento: str,
    telefono: str,
    observaciones: str = "",
) -> Path:
    """Escribe el PDF de la proforma en `destino` y devuelve la ruta.

    Lanza `ErrorPdf` (con mensaje para el usuario) si no se puede escribir el archivo, por
    ejemplo porque está abierto en otro programa.
    """
    p = resultado.params
    dec = resultado.decimales  # 0 = redondeo institucional, 2 = exacto
    t = resultado.totales
    titulo_cliente = nombre.upper()

    # ---- Encabezados por plantilla --------------------------------------------------------
    def cabecera_primera(c, doc) -> None:
        """Encabezado grande de la página 1: logo, título, N° de operación, emisión y datos de la institución."""
        _tira_tricolor(c, ALTO - 10 * mm)
        _logo(c, MARGEN, ALTO - 36 * mm)
        c.setFillColor(CARBON)
        c.setFont("Helvetica-Bold", 15)
        c.drawRightString(ANCHO - MARGEN, ALTO - 21 * mm, "PROFORMA DE PRÉSTAMO")
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(ROJO)
        if nro_operacion:
            c.drawRightString(ANCHO - MARGEN, ALTO - 26.5 * mm, f"Operación N° {nro_operacion}")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(GRIS_TEXTO)
        c.drawRightString(ANCHO - MARGEN, ALTO - 31.5 * mm, f"Fecha de emisión: {fecha_emision}")
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GRIS_SUAVE)
        c.drawRightString(
            ANCHO - MARGEN, ALTO - 36 * mm, f"RUC: {cfg.ruc} · {cfg.direccion} · Tel.: {cfg.telefono}"
        )
        c.setStrokeColor(GRIS_LINEA)
        c.setLineWidth(0.6)
        c.line(MARGEN, ALTO - 40 * mm, ANCHO - MARGEN, ALTO - 40 * mm)

    def cabecera_siguientes(c, doc) -> None:
        """Encabezado compacto de las páginas 2 en adelante."""
        _tira_tricolor(c, ALTO - 10 * mm)
        c.setFillColor(CARBON)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGEN, ALTO - 16 * mm, "FUNDACIÓN INDUSTRIAL")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(GRIS_TEXTO)
        ref = f"Operación N° {nro_operacion} · " if nro_operacion else ""
        c.drawRightString(ANCHO - MARGEN, ALTO - 16 * mm, f"{ref}{titulo_cliente}")
        c.setStrokeColor(GRIS_LINEA)
        c.setLineWidth(0.6)
        c.line(MARGEN, ALTO - 18.5 * mm, ANCHO - MARGEN, ALTO - 18.5 * mm)

    ancho_util = ANCHO - 2 * MARGEN
    marco_primera = Frame(MARGEN, ALTO_PIE, ancho_util, ALTO - ALTO_PIE - ALTO_CABECERA_P1,
                          id="p1", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    marco_siguientes = Frame(MARGEN, ALTO_PIE, ancho_util, ALTO - ALTO_PIE - ALTO_CABECERA_PN,
                             id="pn", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    doc = BaseDocTemplate(
        str(destino), pagesize=A4, title=f"Proforma {nro_operacion}".strip(), author=cfg.empresa,
        subject="Proforma de préstamo - Método Francés",
    )
    doc.addPageTemplates([
        PageTemplate(id="primera", frames=[marco_primera], onPage=cabecera_primera),
        PageTemplate(id="siguientes", frames=[marco_siguientes], onPage=cabecera_siguientes),
    ])

    # ---- Estilos de texto -----------------------------------------------------------------
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=8.5, leading=11, textColor=CARBON)
    etiqueta = ParagraphStyle("etiqueta", parent=base, fontName="Helvetica-Bold", fontSize=7, leading=9,
                              textColor=GRIS_SUAVE)
    valor = ParagraphStyle("valor", parent=base, fontName="Helvetica-Bold", fontSize=9.5, leading=12)
    seccion = ParagraphStyle("seccion", parent=base, fontName="Helvetica-Bold", fontSize=10, leading=13,
                             textColor=CARBON, spaceBefore=2, spaceAfter=3)
    nota = ParagraphStyle("nota", parent=base, fontSize=7.5, leading=10, textColor=GRIS_SUAVE)

    def esc(texto: str) -> str:
        """Escapa los caracteres que reportlab interpreta como marcado (&, <, >)."""
        return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ---- 1) Panel de datos del solicitante y de la operación -------------------------------
    def dato(rotulo: str, texto: str) -> list:
        """Una celda 'ETIQUETA / valor' apilada."""
        return [Paragraph(rotulo.upper(), etiqueta), Paragraph(texto, valor)]

    primer_vto = resultado.cuotero[0].vencimiento
    filas_datos = [
        [dato("Solicitante", esc(titulo_cliente)), dato("C.I. / RUC", esc(documento)),
         dato("Teléfono", esc(telefono))],
        [dato("Capital solicitado", gs(p.capital)),
         dato("Plazo · T.A.N. · T.A.E.",
              f"{p.cuotas} cuotas · {miles(p.tasa_anual, 1)}% · {miles(resultado.tae_pct, 2)}%"),
         dato("Desembolso · 1er vencimiento", f"{fecha_dmy(p.fecha_desembolso)} · {fecha_dmy(primer_vto)}")],
    ]
    panel = Table(filas_datos, colWidths=[ancho_util * 0.40, ancho_util * 0.30, ancho_util * 0.30])
    panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, GRIS_LINEA),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ROJO),  # filete rojo a la izquierda
    ]))

    # ---- 2) Tarjetas con los indicadores clave --------------------------------------------
    def tarjeta(rotulo: str, importe: str, detalle: str, color, oscura: bool = False) -> list:
        """Celda de indicador: rótulo de color, importe grande y detalle pequeño."""
        e_rot = ParagraphStyle("kr", parent=etiqueta, textColor=AMARILLO if oscura else color)
        e_imp = ParagraphStyle("ki", parent=valor, fontSize=12.5, leading=15,
                               textColor=colors.white if oscura else CARBON)
        e_det = ParagraphStyle("kd", parent=nota, textColor=colors.HexColor("#A1A1AA") if oscura else GRIS_SUAVE)
        return [Paragraph(rotulo.upper(), e_rot), Paragraph(importe, e_imp), Paragraph(detalle, e_det)]

    separador = 3 * mm
    ancho_tarjeta = (ancho_util - 3 * separador) / 4
    tarjetas = Table(
        [[
            tarjeta("Cuota final mensual", gs(resultado.cuota_final, dec), f"{p.cuotas} cuotas fijas", ROJO),
            "",
            tarjeta("Base + G. Adm.", gs(resultado.cuota_base_gastos, dec),
                    f"G. Adm.: {gs(resultado.g_adm_mensual, dec)}/mes", NARANJA),
            "",
            tarjeta("Seguro nivelado", gs(resultado.seguro_nivelado, dec), "por mes, en todas las cuotas", AMBAR),
            "",
            tarjeta("Total a pagar", gs(t.cuota_final, dec), f"Plazo total: {resultado.plazo_dias_total} días",
                    CARBON, oscura=True),
        ]],
        colWidths=[ancho_tarjeta, separador, ancho_tarjeta, separador, ancho_tarjeta, separador, ancho_tarjeta],
    )
    tarjetas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (0, 0), 0.5, GRIS_LINEA), ("BOX", (2, 0), (2, 0), 0.5, GRIS_LINEA),
        ("BOX", (4, 0), (4, 0), 0.5, GRIS_LINEA), ("BOX", (6, 0), (6, 0), 0.5, CARBON),
        ("BACKGROUND", (6, 0), (6, 0), CARBON),
        # Filete superior grueso del color de cada indicador
        ("LINEABOVE", (0, 0), (0, 0), 2.5, ROJO), ("LINEABOVE", (2, 0), (2, 0), 2.5, NARANJA),
        ("LINEABOVE", (4, 0), (4, 0), 2.5, AMARILLO), ("LINEABOVE", (6, 0), (6, 0), 2.5, AMARILLO),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        # Las columnas separadoras no llevan relleno ni borde
        ("LEFTPADDING", (1, 0), (1, 0), 0), ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("LEFTPADDING", (3, 0), (3, 0), 0), ("RIGHTPADDING", (3, 0), (3, 0), 0),
        ("LEFTPADDING", (5, 0), (5, 0), 0), ("RIGHTPADDING", (5, 0), (5, 0), 0),
    ]))

    # ---- 3) Cuotero ------------------------------------------------------------------------
    cabecera = ["N°", "Vencim.", "Días", "Saldo inicial", "Amort. capital", "Gastos adm.", "Interés",
                "IVA", "Seg. vida", "Cuota final", "Saldo final"]
    filas = [cabecera]
    for r in resultado.cuotero:
        filas.append([
            str(r.cuota), fecha_dmy(r.vencimiento), str(r.dias), miles(r.saldo_inicial, dec),
            miles(r.amort_capital, dec), miles(r.g_adm, dec), miles(r.interes, dec), miles(r.iva, dec),
            miles(r.seguro, dec), miles(r.cuota_final, dec), miles(r.saldo_final, dec),
        ])
    filas.append(["", "TOTALES", "", "", miles(t.amort_capital, dec), miles(t.g_adm, dec),
                  miles(t.interes, dec), miles(t.iva, dec), miles(t.seguro, dec),
                  miles(t.cuota_final, dec), "0"])

    # Anchos relativos de las 11 columnas, escalados al ancho útil de la página
    relativos = [8, 19, 9, 22, 22, 18, 17, 15, 15, 21, 20]
    escala = ancho_util / (sum(relativos) * mm)
    tabla = Table(filas, colWidths=[a * mm * escala for a in relativos], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 6.8),
        ("TEXTCOLOR", (0, 1), (-1, -2), CARBON),
        # Fila de títulos
        ("BACKGROUND", (0, 0), (-1, 0), CARBON), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        # Cuerpo: N°/fecha/días centrados, importes a la derecha, filas alternadas, solo líneas horizontales
        ("ALIGN", (0, 1), (2, -1), "CENTER"), ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FAFAFA")]),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, GRIS_LINEA),
        ("TOPPADDING", (0, 1), (-1, -2), 2.6), ("BOTTOMPADDING", (0, 1), (-1, -2), 2.6),
        # Columna de cuota final resaltada
        ("BACKGROUND", (9, 1), (9, -2), ROSA_SUAVE), ("FONTNAME", (9, 1), (9, -2), "Helvetica-Bold"),
        ("TEXTCOLOR", (9, 1), (9, -2), ROJO),
        # Fila de totales
        ("BACKGROUND", (0, -1), (-1, -1), CARBON), ("TEXTCOLOR", (0, -1), (-1, -1), AMARILLO),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, -1), (-1, -1), 4), ("BOTTOMPADDING", (0, -1), (-1, -1), 4),
    ]))

    # ---- Composición del documento ----------------------------------------------------------
    elementos: list = [panel, Spacer(1, 4 * mm), tarjetas, Spacer(1, 5 * mm),
                       Paragraph("Cuotero de amortización", seccion), tabla, Spacer(1, 4 * mm)]
    if observaciones:
        elementos.append(Paragraph(f"<b>Observaciones:</b> {esc(observaciones)}", base))
        elementos.append(Spacer(1, 2 * mm))
    elementos.append(Paragraph(
        "Importes en guaraníes (Gs.). El IVA se aplica sobre intereses, gastos administrativos y seguro. "
        "Vencimientos que caen en fin de semana se trasladan al lunes hábil. "
        "T.A.E.: tasa efectiva anual que iguala lo recibido con lo pagado (cuotas en sus fechas reales, act/365).",
        nota))
    # Después de la primera página, usar la plantilla compacta
    elementos.insert(0, NextPageTemplate("siguientes"))

    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        leyenda = f"Para uso interno de {cfg.empresa}"
        doc.build(elementos, canvasmaker=lambda *a, **k: _LienzoNumerado(*a, leyenda=leyenda, **k))
    except Exception as exc:  # reportlab u OS (archivo abierto, sin permisos, disco lleno...)
        raise ErrorPdf("No se pudo generar el PDF. Verifique que el archivo no esté abierto.") from exc
    return destino
