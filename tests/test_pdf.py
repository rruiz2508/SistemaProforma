from datetime import date

from proformas.calculo import ParametrosProforma, calcular_proforma
from proformas.config import cargar_config
from proformas.pdf import generar_pdf, nombre_archivo_seguro


def test_nombre_archivo_seguro():
    assert nombre_archivo_seguro("../../Windows/x") == "WINDOWS_X"
    assert nombre_archivo_seguro("José Ñandú") == "JOSE_NANDU"
    assert nombre_archivo_seguro("???") == "PROFORMA"
    assert "/" not in nombre_archivo_seguro("a/b\\c:d")
    assert len(nombre_archivo_seguro("x" * 200)) <= 40


def test_generar_pdf(tmp_path):
    r = calcular_proforma(ParametrosProforma(
        capital=10_000_000, tasa_anual=24, cuotas=120, fecha_desembolso=date(2026, 11, 24),
        primer_vencimiento=date(2026, 12, 24)))
    destino = tmp_path / "x" / "p.pdf"
    out = generar_pdf(destino, r, cargar_config(), nro_operacion="20261124001", fecha_emision="24/11/2026 10:00",
                      nombre="Juan <Pérez> & Cía", documento="4.567.890", telefono="0981 555-123",
                      observaciones="Capital operativo")
    datos = out.read_bytes()
    assert datos.startswith(b"%PDF") and len(datos) > 3000
