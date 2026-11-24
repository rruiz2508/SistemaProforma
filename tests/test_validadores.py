import pytest

from proformas.validadores import (
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


@pytest.mark.parametrize("valor", ["", "   ", "abc", "10a", "$100", "-5", "0", "0.0", "１２３", "1e5",
                                   "999999999999999999"])
def test_capital_rechaza_invalidos(valor):
    with pytest.raises(ErrorValidacion) as e:
        validar_capital(valor)
    assert e.value.campo == "capital" and e.value.mensaje


@pytest.mark.parametrize("valor,esperado", [("10.000.000", 10_000_000), ("1", 1), (" 5000 ", 5000)])
def test_capital_valido(valor, esperado):
    assert validar_capital(valor) == esperado


@pytest.mark.parametrize("valor", ["", "abc", "0", "121", "-1", "1.5", "12m"])
def test_cuotas_rechaza(valor):
    with pytest.raises(ErrorValidacion):
        validar_cuotas(valor)


def test_cuotas_valida():
    assert validar_cuotas("12") == 12
    assert validar_cuotas("120") == 120


@pytest.mark.parametrize("valor", ["", "   ", "abc", "000000", "111111", "123", "12345678901234567890",
                                   "0981-abc", "0981;555", "+++"])
def test_telefono_rechaza(valor):
    with pytest.raises(ErrorValidacion) as e:
        validar_telefono(valor)
    assert e.value.campo == "telefono"


@pytest.mark.parametrize("valor", ["0981 555-123", "+595 981 555123", "(021) 605 700"])
def test_telefono_valido(valor):
    assert validar_telefono(valor)


@pytest.mark.parametrize("valor", ["", "  ", "ab", "<script>", "Robert'); DROP TABLE x;--", "x" * 121])
def test_nombre_rechaza(valor):
    with pytest.raises(ErrorValidacion):
        validar_nombre(valor)


def test_nombre_valido_normaliza_espacios():
    assert validar_nombre("  Juan   Carlos Pérez ") == "Juan Carlos Pérez"
    assert validar_nombre("Ñandú S.A.") == "Ñandú S.A."


@pytest.mark.parametrize("valor", ["", "abc", "0", "00000", "4.56.789", "4567890-12", "A@123456", "AB12"])
def test_documento_rechaza(valor):
    with pytest.raises(ErrorValidacion):
        validar_documento(valor)


@pytest.mark.parametrize("valor,esperado", [("4567890", "4.567.890"), ("4.567.890-1", "4.567.890-1"),
                                            ("ab123456", "AB123456")])
def test_documento_valido(valor, esperado):
    assert validar_documento(valor) == esperado


def test_decimal_rechaza_letras_negativos_y_rangos():
    for malo in ["", "abc", "-1", "1,2,3", "5%"]:
        with pytest.raises(ErrorValidacion):
            validar_decimal("tan", "la tasa", malo, 0, 200)
    with pytest.raises(ErrorValidacion):
        validar_decimal("tan", "la tasa", "250", 0, 200)
    assert validar_decimal("tan", "la tasa", "24,5", 0, 200) == 24.5


@pytest.mark.parametrize("valor", ["", "31/02/2026", "2026-11-24", "abc", "32/01/2026", "01/01/1999"])
def test_fecha_rechaza(valor):
    with pytest.raises(ErrorValidacion):
        validar_fecha("f", "la fecha", valor)


def test_fecha_valida():
    assert validar_fecha("f", "la fecha", "24/11/2026").year == 2026


def test_observaciones_limite_y_control():
    assert validar_observaciones("") == ""
    with pytest.raises(ErrorValidacion):
        validar_observaciones("x" * 301)
    with pytest.raises(ErrorValidacion):
        validar_observaciones("hola\x00mundo")
