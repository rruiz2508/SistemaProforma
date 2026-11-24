"""Importación de respaldos (repositorio)."""
import sqlite3

import pytest

from proformas.db import ErrorBaseDatos, RepositorioProformas


def datos(**cambios):
    base = dict(
        nombre_cliente="Juan Pérez", documento="4.567.890", telefono="0981 555-123", observaciones="",
        fecha_desembolso="2026-11-24", primer_vencimiento="2026-12-24", primer_vto_nominal=None,
        capital=10_000_000, tasa_anual=24.0, cuotas=12, iva_pct=10.0, pct_gastos=2.0, tasa_seguro=0.25,
        redondeo_entero=1, cuota_base_gastos=974262.0, seguro_mensual=15670.0, cuota_final=991072.0,
        total_pagar=11892864.0,
    )
    base.update(cambios)
    return base


@pytest.fixture
def repo(tmp_path):
    r = RepositorioProformas(tmp_path / "t.db")
    yield r
    r.cerrar()


def _respaldo_con(tmp_path, *registros, nombre="resp.db"):
    r = RepositorioProformas(tmp_path / nombre)
    for d in registros:
        r.crear(d)
    r.cerrar()
    return tmp_path / nombre


def test_combinar_en_base_vacia(repo, tmp_path):
    ruta = _respaldo_con(tmp_path, datos(nombre_cliente="Ana Gómez"), datos(nombre_cliente="Luis Díaz"))
    res = repo.importar(ruta, "combinar")
    assert (res.importadas, res.duplicadas, res.invalidas) == (2, 0, 0)
    assert {p.nombre_cliente for p in repo.listar()} == {"Ana Gómez", "Luis Díaz"}


def test_combinar_no_duplica(repo, tmp_path):
    ruta = _respaldo_con(tmp_path, datos(nombre_cliente="Ana Gómez"))
    repo.importar(ruta, "combinar")
    res = repo.importar(ruta, "combinar")
    assert (res.importadas, res.duplicadas) == (0, 1)
    assert len(repo.listar()) == 1


def test_combinar_conflicto_de_nro_operacion_genera_nuevo(repo, tmp_path):
    ruta = _respaldo_con(tmp_path, datos(nombre_cliente="Ana Gómez", documento="1.111.222"))
    repo.crear(datos(nombre_cliente="Otro Cliente"))  # mismo N° del día pero distinto registro
    res = repo.importar(ruta, "combinar")
    assert res.importadas == 1
    assert len({p.nro_operacion for p in repo.listar()}) == 2


def test_reemplazar_hace_copia_previa(repo, tmp_path):
    repo.crear(datos(nombre_cliente="Actual Uno"))
    ruta = _respaldo_con(tmp_path, datos(nombre_cliente="Del Respaldo"))
    previa = tmp_path / "backups" / "antes.db"
    previa.parent.mkdir()
    res = repo.importar(ruta, "reemplazar", copia_previa=previa)
    assert [p.nombre_cliente for p in repo.listar()] == ["Del Respaldo"]
    assert res.copia_previa == previa and previa.exists()
    copia = RepositorioProformas(previa)
    assert [p.nombre_cliente for p in copia.listar()] == ["Actual Uno"]
    copia.cerrar()


def test_archivo_que_no_es_sqlite(repo, tmp_path):
    malo = tmp_path / "texto.db"
    malo.write_text("esto no es una base de datos")
    with pytest.raises(ErrorBaseDatos):
        repo.importar(malo)
    with pytest.raises(ErrorBaseDatos):
        repo.importar(tmp_path / "no_existe.db")


def test_sqlite_ajeno_sin_tabla_o_columnas(repo, tmp_path):
    for nombre, ddl in (("ajeno.db", "CREATE TABLE otra (x INTEGER)"),
                        ("viejo.db", "CREATE TABLE proformas (id INTEGER, nombre_cliente TEXT)")):
        con = sqlite3.connect(tmp_path / nombre)
        con.execute(ddl)
        con.commit()
        con.close()
        with pytest.raises(ErrorBaseDatos):
            repo.importar(tmp_path / nombre)


def test_el_mismo_archivo_en_uso(repo):
    with pytest.raises(ErrorBaseDatos):
        repo.importar(repo.ruta)


def test_descarta_filas_invalidas_sin_romper(repo, tmp_path):
    ruta = _respaldo_con(tmp_path, datos(nombre_cliente="Buena Fila"), datos(nombre_cliente="Fila Mala"),
                         datos(nombre_cliente="Otra Mala"), datos(nombre_cliente="Tercera Mala"))
    con = sqlite3.connect(ruta)
    con.execute("UPDATE proformas SET capital = 'abc' WHERE nombre_cliente = 'Fila Mala'")
    con.execute("UPDATE proformas SET fecha_desembolso = 'ayer' WHERE nombre_cliente = 'Otra Mala'")
    con.execute("UPDATE proformas SET nombre_cliente = '<script>x</script>' WHERE nombre_cliente = 'Tercera Mala'")
    con.commit()
    con.close()
    res = repo.importar(ruta, "combinar")
    assert (res.importadas, res.invalidas) == (1, 3)
    assert [p.nombre_cliente for p in repo.listar()] == ["Buena Fila"]


def test_modo_desconocido(repo, tmp_path):
    with pytest.raises(ValueError):
        repo.importar(_respaldo_con(tmp_path, datos()), "otro")
