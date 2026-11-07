import pandas as pd

from edu_data.perfil import perfil_columnas, verificar_identidades


def _base():
    return pd.DataFrame(
        {
            "total": pd.array([10, 5, 8, None], dtype="Int64"),
            "mujeres": pd.array([4, 2, 3, 1], dtype="Int64"),
            "varones": pd.array([6, 2, None, 2], dtype="Int64"),
            "cod": pd.array(["01", "02", "03", "04"], dtype="string"),
        }
    )


def test_perfil_columnas():
    df = _base()
    df.attrs["columnas_ausentes"] = ["varones"]
    perfil = perfil_columnas(df)
    assert perfil.loc["total", "vacios"] == 1
    assert perfil.loc["total", "suma"] == 23
    assert perfil.loc["mujeres", "ceros"] == 0
    assert pd.isna(perfil.loc["cod", "ceros"])
    assert not perfil.loc["varones", "existe_en_origen"]


def test_verificar_identidades_separa_falla_de_no_evaluable():
    resultado = verificar_identidades(_base(), {"sexo": "total - mujeres - varones"})
    assert resultado.attrs["resumen"]["sexo"] == {"ok": 1, "falla": 1, "no_evaluable": 2}
    fallas = resultado[resultado["estado"] == "falla"]
    assert fallas["fila"].tolist() == [1]
    assert fallas["residuo"].tolist() == [1.0]
    no_evaluables = resultado[resultado["estado"] == "no_evaluable"]
    assert no_evaluables["fila"].tolist() == [2, 3]
    assert no_evaluables["residuo"].isna().all()


def test_verificar_identidades_con_tolerancia():
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [1.0005, 2.5]})
    resultado = verificar_identidades(df, {"igual": "a - b"}, tolerancia=0.001)
    assert resultado["fila"].tolist() == [1]
