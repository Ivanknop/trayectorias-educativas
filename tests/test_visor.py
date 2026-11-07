import pytest

from edu_data.agregados import resumir
from edu_data.geo import RUTA_GEO_SVG, cargar_provincias_svg
from edu_data.validacion import alerta_para
from edu_data.visor import TOTAL_PAIS, datos_visor


@pytest.fixture(scope="module")
def datos(largo):
    return datos_visor(largo)


def _sumar(celdas, conteo, i, filtro=None):
    return sum(
        v[conteo][i] for clave, v in celdas.items() if filtro is None or filtro(clave.split("|"))
    )


@pytest.mark.parametrize("prov", [TOTAL_PAIS, "Salta", "Buenos Aires"])
def test_celdas_coinciden_con_resumir(largo, datos, prov):
    ciclo, nivel = 2015, "secundaria"
    i = datos["ciclos"].index(ciclo)
    celdas = datos["celdas"][prov][nivel]
    filtro_prov = None if prov == TOTAL_PAIS else prov
    ref = resumir(
        largo,
        ciclo=ciclo,
        provincia=filtro_prov,
        nivel=nivel,
        indicadores=["nopromo", "inicial", "egresados"],
    )
    assert _sumar(celdas, "nopromo", i) == ref.nopromo.iloc[0]
    assert _sumar(celdas, "egresados", i) == ref.egresados.iloc[0]
    tasa = _sumar(celdas, "nopromo", i) / _sumar(celdas, "ultimo_con_resultado", i) * 100
    assert round(tasa, 2) == ref.tasa_repitencia.iloc[0]


def test_desagregado_por_sector_y_sexo(largo, datos):
    i = datos["ciclos"].index(2020)
    celdas = datos["celdas"]["Córdoba"]["primaria"]
    valor = _sumar(celdas, "ssp", i, lambda k: k[0] == "Estatal" and k[2] == "mujeres")
    ref = resumir(
        largo,
        ciclo=2020,
        provincia="Córdoba",
        nivel="primaria",
        sector="Estatal",
        sexo="mujeres",
        indicadores=["ssp"],
        tasas=False,
    )
    assert valor == ref.ssp.iloc[0]


def test_alerta_pandemia_en_ciclo_2020(datos):
    assert alerta_para(2020, "tasa_repitencia")
    assert not alerta_para(2021, "tasa_repitencia")
    assert 2020 in datos["alertas"][f"{TOTAL_PAIS}|secundaria|repitencia"]


def test_todas_las_provincias_tienen_geometria(datos):
    assert RUTA_GEO_SVG.exists(), "Falta el recurso versionado del mapa"
    geo = cargar_provincias_svg()
    assert set(datos["provincias"]) <= {p["nombre"] for p in geo["provincias"]}


def test_saldo_privado_es_menos_perdida_privada(largo, datos):
    from edu_data.agregados import continuidad

    i = datos["ciclos"].index(2023)
    celdas = datos["celdas"][TOTAL_PAIS]["secundaria"]
    perdida_priv = _sumar(celdas, "perdida", i, lambda k: k[0] == "Privado")
    c = continuidad(largo)
    ref = c[(c.ciclo == 2023) & (c.nivel == "secundaria") & (c.sector == "Privado")].perdida.sum()
    assert perdida_priv == ref
    assert datos["indicadores"]["privado"]["fija_sector"]
