import pandas as pd

from edu_data.validacion_base import (
    Alerta,
    alerta_para,
    atipicos_robustos,
    coherencia,
    saltos_interanuales,
)


def test_saltos_interanuales(serie):
    saltos = saltos_interanuales(serie, "valor", "unidad", umbral=0.20)
    assert saltos[["unidad", "periodo"]].values.tolist() == [["B", 2021], ["B", 2022]]
    assert saltos.iloc[0]["periodo_anterior"] == 2020


def test_saltos_ignora_base_cero():
    t = pd.DataFrame({"u": ["A", "A"], "periodo": [1, 2], "v": [0, 10]})
    assert saltos_interanuales(t, "v", "u").empty


def test_atipicos_robustos(serie):
    atipicos = atipicos_robustos(serie, "valor", "unidad")
    assert atipicos[["unidad", "periodo"]].values.tolist() == [["B", 2021]]


def test_coherencia():
    t = pd.DataFrame(
        {
            "u": ["A"] * 4,
            "egresados": [90, 91, 89, 60],
            "promovidos": [100, 100, 100, 100],
        }
    )
    resultado = coherencia(t, "egresados", "promovidos", "u", umbral_pct=0.10)
    assert resultado.index.tolist() == [3]


ALERTAS = [
    Alerta(periodos=[2021], texto="Cae 15 % y rebota 27 %", unidades=["B"], indicadores=["valor"]),
    Alerta(periodos=[2020], texto="Shock general", filtros={"sector": "privado"}),
    Alerta(periodos=[2022], texto="Unidad grande", unidades=["C"], afecta_total=True),
]


def test_alerta_por_unidad_e_indicador():
    assert alerta_para(ALERTAS, 2021, "valor", unidades="B") == "Cae 15 % y rebota 27 %"
    assert alerta_para(ALERTAS, 2021, "otro", unidades="B") is None
    assert alerta_para(ALERTAS, 2021, "valor", unidades=["A"]) is None


def test_alerta_en_total_solo_si_afecta_total():
    assert alerta_para(ALERTAS, 2021, "valor") is None
    assert alerta_para(ALERTAS, 2022, "valor") == "Unidad grande"


def test_alerta_con_filtros():
    assert alerta_para(ALERTAS, 2020, "valor", sector="privado") == "Shock general"
    assert alerta_para(ALERTAS, 2020, "valor", sector="estatal") is None
    # Sin filtrar por sector (total), la alerta del sector privado también aplica
    assert alerta_para(ALERTAS, 2020, "valor") == "Shock general"
