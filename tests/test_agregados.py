import pytest

from edu_data.agregados import resumir
from edu_data.trayectoria import SUFIJOS, archivo_de, leer_trayectoria


@pytest.mark.parametrize("ciclo", [2010, 2020, 2024])
def test_totales_coinciden_con_archivo(largo, ciclo):
    crudo = leer_trayectoria(archivo_de(ciclo))
    for bloque in ["inicial", "ssp", "nopromo"]:
        esperado = int(sum(crudo[f"{bloque}_{s}"].sum() for s in SUFIJOS))
        obtenido = resumir(largo, ciclo=ciclo, indicadores=[bloque], tasas=False)[bloque].iloc[0]
        assert obtenido == esperado
    egr = resumir(largo, ciclo=ciclo, nivel="secundaria", indicadores=["egresados"])
    assert egr.egresados.iloc[0] == crudo.secundaria_egresados.sum()


def test_mujeres_mas_varones_igual_total(largo):
    t = resumir(largo, por=["sexo"], indicadores=["inicial"], tasas=False)
    p = t.pivot(index="ciclo", columns="sexo", values="inicial")
    assert (p.mujeres + p.varones == p.total).all()


def test_ciclo_siempre_es_dimension(largo):
    t = resumir(largo, indicadores=["inicial"], tasas=False)
    assert list(t.ciclo) == list(range(2010, 2025))


def test_continuidad_reproduce_calculo_manual(largo):
    from edu_data.agregados import continuidad

    c = continuidad(largo)
    t = resumir(
        largo,
        por=["anio_estudio"],
        ciclo=[2023, 2024],
        anio_estudio=["10", "11"],
        indicadores=["promovidos_efectivos", "nopromo", "inicial"],
        tasas=False,
    ).set_index(["ciclo", "anio_estudio"])
    esperados = t.loc[(2023, "10"), "promovidos_efectivos"] + t.loc[(2023, "11"), "nopromo"]
    reales = t.loc[(2024, "11"), "inicial"]
    fila = c[(c.ciclo == 2024) & (c.anio_estudio == "11")][["esperados", "reales"]].sum()
    assert fila.esperados == esperados
    assert fila.reales == reales


def test_continuidad_no_cuenta_recursantes_de_12(largo):
    from edu_data.agregados import continuidad

    c = continuidad(largo)
    doce = c[(c.ciclo == 2024) & (c.anio_estudio == "12")].sum(numeric_only=True)
    assert abs(doce.perdida / doce.esperados) < 0.02


def test_egresados_primaria_son_promovidos_del_ultimo_grado(largo):
    from edu_data.trayectoria import PRIMARIA_7_ANIOS

    for prov in ["Córdoba", "Salta"]:
        ultimo = "7" if prov in PRIMARIA_7_ANIOS else "6"
        egr = resumir(
            largo,
            ciclo=2010,
            provincia=prov,
            nivel="primaria",
            indicadores=["egresados"],
            tasas=False,
        ).egresados.iloc[0]
        prom = resumir(
            largo,
            ciclo=2010,
            provincia=prov,
            anio_estudio=ultimo,
            indicadores=["promovidos_efectivos"],
            tasas=False,
        )
        assert egr == prom.promovidos_efectivos.iloc[0]


def test_egresados_informados_conservan_el_archivo(largo):
    crudo = leer_trayectoria(archivo_de(2015))
    inf = resumir(largo, ciclo=2015, nivel="primaria", indicadores=["egresados_informados"])
    assert inf.egresados_informados.iloc[0] == crudo.primaria_egresados.sum()
