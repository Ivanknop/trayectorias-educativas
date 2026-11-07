import pandas as pd
import pytest
from openpyxl import Workbook

from edu_data.io import (
    detectar_formato,
    diff_columnas,
    leer_csv_oficial,
    leer_hoja,
    listar_hojas,
    unificar_esquema,
)


def test_detectar_formato_oficial(csv_oficial):
    formato = detectar_formato(csv_oficial)
    assert formato["encoding"] in {"cp1252", "latin-1"}
    assert formato["sep"] == ";"
    assert formato["crlf"] is True
    assert formato["encabezado"][0] == "Cod_Unidad"


def test_detectar_formato_utf8_con_bom(tmp_path):
    ruta = tmp_path / "utf8.csv"
    ruta.write_bytes("a,b\nñ,1\n".encode("utf-8-sig"))
    formato = detectar_formato(ruta)
    assert formato == {"encoding": "utf-8-sig", "sep": ",", "crlf": False, "encabezado": ["a", "b"]}


def test_leer_csv_oficial_columnas_y_texto(csv_oficial):
    df = leer_csv_oficial(csv_oficial)
    assert list(df.columns) == ["cod_unidad", "nombre", "cue", "matricula", "mujeres", "tasa"]
    assert df["nombre"].tolist() == ["Región Ñandú", "Córdoba", "Otra"]


def test_leer_csv_oficial_vacio_no_es_cero(csv_oficial):
    df = leer_csv_oficial(csv_oficial)
    assert df["matricula"].dtype == "Int64"
    assert pd.isna(df.loc[1, "matricula"])
    assert df.loc[2, "matricula"] == 0
    assert pd.isna(df.loc[2, "tasa"])
    assert df["tasa"].dtype == "Float64"


def test_leer_csv_oficial_detecta_ceros_a_la_izquierda(csv_oficial):
    df = leer_csv_oficial(csv_oficial)
    assert df["cod_unidad"].dtype == "string"
    assert df["cod_unidad"].tolist() == ["02", "14", "06"]
    assert df.attrs["columnas_texto_por_ceros"] == ["cod_unidad"]
    # Sin ceros a la izquierda y sin declararla clave, sigue siendo numérica
    assert df["mujeres"].dtype == "Int64"


def test_leer_csv_oficial_claves_explicitas(csv_oficial):
    df = leer_csv_oficial(csv_oficial, claves=["CUE"])
    assert df["cue"].dtype == "string"
    assert df["cue"].tolist() == ["123", "456", "789"]


def test_leer_csv_oficial_decimal_coma(tmp_path):
    ruta = tmp_path / "coma.csv"
    ruta.write_text("tasa;n\n1,5;3\n2,25;4\n", encoding="utf-8")
    df = leer_csv_oficial(ruta, decimal=",")
    assert df["tasa"].tolist() == [1.5, 2.25]


def test_unificar_esquema():
    dfs = {
        2020: pd.DataFrame({"a": pd.array([1], dtype="Int64"), "b": ["x"]}),
        2021: pd.DataFrame({"a": pd.array([2], dtype="Int64"), "c": [3.0]}),
    }
    unificados = unificar_esquema(dfs)
    assert list(unificados[2020].columns) == ["a", "b", "c"]
    assert unificados[2020].attrs["columnas_ausentes"] == ["c"]
    assert unificados[2021].attrs["columnas_ausentes"] == ["b"]
    assert pd.isna(unificados[2021].loc[0, "b"])


def test_diff_columnas_ignora_mayusculas():
    dfs = {
        2020: pd.DataFrame(columns=["Departamento", "total"]),
        2021: pd.DataFrame(columns=["departamento", "total", "nueva"]),
    }
    tabla = diff_columnas(dfs)
    assert tabla.loc["departamento", "en_todos"]
    assert tabla.loc["departamento", "grafias"] == "Departamento, departamento"
    assert not tabla.loc["nueva", 2020]


@pytest.fixture
def excel_diccionario(tmp_path):
    libro = Workbook()
    hoja = libro.active
    hoja.title = "base"
    hoja.append(["Diccionario de variables - Relevamiento X"])
    hoja.append([])
    hoja.append(["Variable", "Descripción", "Tipo"])
    hoja.append(["matricula", "Alumnos matriculados", "numérico"])
    hoja.append(["cod", "Código de unidad", "texto"])
    libro.create_sheet("indice").append(["Hojas", "base"])
    ruta = tmp_path / "diccionario.xlsx"
    libro.save(ruta)
    return ruta


def test_listar_hojas(excel_diccionario):
    hojas = listar_hojas(excel_diccionario)
    assert hojas["hoja"].tolist() == ["base", "indice"]
    assert hojas.loc[0, "filas"] == 4


def test_leer_hoja_detecta_encabezado(excel_diccionario):
    df = leer_hoja(excel_diccionario, "base")
    assert list(df.columns) == ["Variable", "Descripción", "Tipo"]
    assert df["Variable"].tolist() == ["matricula", "cod"]
