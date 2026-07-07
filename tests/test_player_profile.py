from validators import normalizar_telefono


def test_normalizar_telefono_formatea_primeros_cuatro_digitos():
    assert normalizar_telefono("04141234567") == "0414-1234567"
    assert normalizar_telefono("1234567") == "1234-567"
    assert normalizar_telefono("1234") == "1234"
    assert normalizar_telefono("") == ""
