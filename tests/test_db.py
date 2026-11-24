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


def test_crear_y_obtener(repo):
    p = repo.crear(datos())
    assert p.id == 1 and p.nombre_cliente == "Juan Pérez"
    assert len(p.nro_operacion) == 11 and p.nro_operacion.endswith("001")
    assert repo.obtener(p.id) == p


def test_nro_operacion_secuencial_diario(repo):
    a = repo.crear(datos())
    b = repo.crear(datos())
    assert a.nro_operacion[:8] == b.nro_operacion[:8]
    assert int(b.nro_operacion[8:]) == int(a.nro_operacion[8:]) + 1


def test_listar_y_buscar(repo):
    repo.crear(datos(nombre_cliente="Ana Gómez", documento="1.111.222", telefono="0971 000-111"))
    repo.crear(datos(nombre_cliente="Luis Díaz", documento="3.333.444"))
    assert len(repo.listar()) == 2
    assert [p.nombre_cliente for p in repo.listar("ana")] == ["Ana Gómez"]
    assert len(repo.listar("3.333")) == 1
    assert len(repo.listar("0971")) == 1
    assert repo.listar("zzz") == []


def test_busqueda_con_comodines_es_literal(repo):
    repo.crear(datos())
    assert repo.listar("%") == []
    assert repo.listar("_") == []


def test_actualizar(repo):
    p = repo.crear(datos())
    nuevo = repo.actualizar(p.id, datos(nombre_cliente="Otro Nombre", capital=5_000_000))
    assert nuevo.nombre_cliente == "Otro Nombre" and nuevo.capital == 5_000_000
    assert nuevo.nro_operacion == p.nro_operacion


def test_actualizar_inexistente(repo):
    with pytest.raises(ErrorBaseDatos):
        repo.actualizar(999, datos())


def test_eliminar(repo):
    p = repo.crear(datos())
    assert repo.eliminar(p.id) is True
    assert repo.obtener(p.id) is None
    assert repo.eliminar(p.id) is False


def test_sql_injection_es_dato(repo):
    malo = "Robert'); DROP TABLE proformas;--"
    p = repo.crear(datos(nombre_cliente=malo))
    assert repo.obtener(p.id).nombre_cliente == malo
    assert len(repo.listar(malo)) == 1
    assert len(repo.listar("' OR 1=1 --")) == 0
    assert len(repo.listar()) == 1  # la tabla sigue existiendo


def test_restricciones_check(repo):
    with pytest.raises(ErrorBaseDatos):
        repo.crear(datos(capital=-1))
    with pytest.raises(ErrorBaseDatos):
        repo.crear(datos(cuotas=500))
    with pytest.raises(ErrorBaseDatos):
        repo.crear(datos(nombre_cliente="   "))


def test_respaldo(repo, tmp_path):
    repo.crear(datos())
    destino = repo.respaldar(tmp_path / "copia.db")
    copia = RepositorioProformas(destino)
    assert len(copia.listar()) == 1
    copia.cerrar()


def test_memoria():
    r = RepositorioProformas(":memory:")
    r.crear(datos())
    assert len(r.listar()) == 1
