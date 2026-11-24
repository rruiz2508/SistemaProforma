"""Generación del PDF del cuotero con reportlab."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .calculo import ResultadoProforma
from .config import Config
from .formato import fecha_dmy, gs, miles

ROJO = colors.HexColor("#D11D27")
AMARILLO = colors.HexColor("#F7D100")
NARANJA = colors.HexColor("#F16522")
CARBON = colors.HexColor("#18181B")
GRIS = colors.HexColor("#F4F4F5")
MARGEN = 14 * mm


class ErrorPdf(Exception):
    """No se pudo generar el PDF."""


def nombre_archivo_seguro(texto: str) -> str:
    """Solo [A-Z0-9_]: evita path traversal y caracteres inválidos en Windows."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^A-Z0-9]+", "_", sin_tildes.upper()).strip("_")
    return (limpio or "PROFORMA")[:40]


def _tira_tricolor(c, y: float, ancho: float) -> None:
    w = ancho - 2 * MARGEN
    x = MARGEN
    for color, frac in ((ROJO, 0.45), (AMARILLO, 0.30), (NARANJA, 0.25)):
        c.setFillColor(color)
        c.rect(x, y, w * frac, 1.3 * mm, stroke=0, fill=1)
        x += w * frac


def _logo(c, x: float, y: float) -> None:
    """Logotipo vectorial simplificado (trazos rojo, amarillo y naranja) + texto."""
    c.saveState()
    c.setLineCap(1)
    c.setLineJoin(1)
    c.setLineWidth(1.6 * mm)
    s = 0.16 * mm

    def p(px, py):
        return x + px * s, y + (140 - py) * s

    c.setStrokeColor(ROJO)
    t = c.beginPath()
    t.moveTo(*p(72, 36)); t.lineTo(*p(26, 82)); t.lineTo(*p(88, 144))
    c.drawPath(t, stroke=1, fill=0)
    c.line(*p(57, 113), *p(93, 77))
    c.setStrokeColor(AMARILLO)
    c.line(*p(55.5, 83.5), *p(121.5, 17.5))
    t = c.beginPath()
    t.moveTo(*p(89.5, 17.5)); t.lineTo(*p(121.5, 17.5)); t.lineTo(*p(121.5, 49.5))
    c.drawPath(t, stroke=1, fill=0)
    c.setStrokeColor(NARANJA)
    c.line(*p(85.5, 115.5), *p(108.5, 92.5))
    c.restoreState()
    c.setFillColor(CARBON)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x + 26 * mm, y + 15 * mm, "FUNDACIÓN")
    c.drawString(x + 26 * mm, y + 9 * mm, "INDUSTRIAL")


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
    """Escribe el PDF en `destino` y devuelve la ruta."""
    p = resultado.params
    dec = resultado.decimales
    ancho, alto = A4

    def en_pagina(c, doc):
        _tira_tricolor(c, alto - 12 * mm, ancho)
        if doc.page == 1:
            _logo(c, MARGEN, alto - 40 * mm)
            c.setFillColor(CARBON)
            c.setFont("Helvetica-Bold", 13)
            c.drawRightString(ancho - MARGEN, alto - 22 * mm, "PROFORMA DE PRÉSTAMO")
            c.setFont("Helvetica", 8.5)
            c.setFillColor(colors.HexColor("#52525B"))
            sub = f"Operación N° {nro_operacion} · " if nro_operacion else ""
            c.drawRightString(ancho - MARGEN, alto - 27 * mm, f"{sub}Fecha de emisión: {fecha_emision}")
            c.drawRightString(
                ancho - MARGEN, alto - 32 * mm,
                f"RUC: {cfg.ruc} · {cfg.direccion} · Tel.: {cfg.telefono}",
            )
        _tira_tricolor(c, 8 * mm, ancho)
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#71717A"))
        c.drawCentredString(ancho / 2, 12 * mm, f"Para uso interno de {cfg.empresa}. Página {doc.page}")

    doc = SimpleDocTemplate(
        str(destino), pagesize=A4, leftMargin=MARGEN, rightMargin=MARGEN,
        topMargin=46 * mm, bottomMargin=18 * mm,
        title=f"Proforma {nro_operacion}", author=cfg.empresa,
    )
    st = ParagraphStyle("c", fontName="Helvetica", fontSize=8.5, leading=11)
    stb = ParagraphStyle("cb", parent=st, fontName="Helvetica-Bold")

    def esc(t: str) -> str:
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    datos = [
        [Paragraph("SOLICITANTE:", stb), Paragraph(esc(nombre.upper()), st),
         Paragraph("CAPITAL:", stb), Paragraph(gs(p.capital), st)],
        [Paragraph("C.I. / RUC:", stb), Paragraph(esc(documento), st),
         Paragraph("PLAZO / TAN / TAE:", stb),
         Paragraph(f"{p.cuotas} cuotas · {miles(p.tasa_anual, 1)}% · TAE {miles(resultado.tae_pct, 2)}%", st)],
        [Paragraph("TELÉFONO:", stb), Paragraph(esc(telefono), st),
         Paragraph("DESEMBOLSO / 1ER VTO.:", stb),
         Paragraph(f"{fecha_dmy(p.fecha_desembolso)} · {fecha_dmy(resultado.cuotero[0].vencimiento)}", st)],
        [Paragraph("CUOTA MENSUAL:", stb),
         Paragraph(f'<font color="#D11D27"><b>{gs(resultado.cuota_final, dec)}</b></font>', st),
         Paragraph("GASTOS ADM. + IVA:", stb), Paragraph(gs(resultado.g_adm_total, dec), st)],
    ]
    t_datos = Table(datos, colWidths=[32 * mm, 52 * mm, 44 * mm, 54 * mm])
    t_datos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))

    cab = ["N°", "Vencim.", "Días", "Saldo Inicial", "Amort. Capital", "Gastos Adm.", "Interés",
           "IVA", "Seg. Vida", "Cuota Final", "Saldo Final"]
    filas = [cab]
    for r in resultado.cuotero:
        filas.append([
            str(r.cuota), fecha_dmy(r.vencimiento), str(r.dias), miles(r.saldo_inicial, dec),
            miles(r.amort_capital, dec), miles(r.g_adm, dec), miles(r.interes, dec),
            miles(r.iva, dec), miles(r.seguro, dec), miles(r.cuota_final, dec), miles(r.saldo_final, dec),
        ])
    t = resultado.totales
    filas.append(["", "TOTALES", "", "", miles(t.amort_capital, dec), miles(t.g_adm, dec),
                  miles(t.interes, dec), miles(t.iva, dec), miles(t.seguro, dec),
                  miles(t.cuota_final, dec), "0"])
    anchos = [8, 19, 9, 22, 22, 18, 17, 15, 15, 21, 20]
    escala = (ancho - 2 * MARGEN) / (sum(anchos) * mm)
    tabla = Table(filas, colWidths=[a * mm * escala for a in anchos], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 6.6),
        ("BACKGROUND", (0, 0), (-1, 0), CARBON), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (2, -1), "CENTER"), ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (9, 1), (9, -2), "Helvetica-Bold"), ("TEXTCOLOR", (9, 1), (9, -2), ROJO),
        ("BACKGROUND", (0, -1), (-1, -1), CARBON), ("TEXTCOLOR", (0, -1), (-1, -1), AMARILLO),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D4D4D8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FAFAFA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    resumen = Paragraph(
        f"<b>Total a pagar:</b> {gs(t.cuota_final, dec)} &nbsp;·&nbsp; <b>Seguro nivelado:</b> "
        f"{gs(resultado.seguro_nivelado, dec)}/mes &nbsp;·&nbsp; <b>Plazo total:</b> {resultado.plazo_dias_total} días",
        st,
    )
    elementos = [t_datos, Spacer(1, 4 * mm), tabla, Spacer(1, 4 * mm), resumen]
    if observaciones:
        elementos += [Spacer(1, 2 * mm), Paragraph(f"<b>Observaciones:</b> {esc(observaciones)}", st)]

    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        doc.build(elementos, onFirstPage=en_pagina, onLaterPages=en_pagina)
    except Exception as exc:  # reportlab/OS: se reporta de forma genérica
        raise ErrorPdf("No se pudo generar el PDF. Verifique que el archivo no esté abierto.") from exc
    return destino
