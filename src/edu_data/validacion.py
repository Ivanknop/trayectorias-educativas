"""Controles de pertinencia de las bases de Trayectoria. Señalan sospechas, no corrigen."""

import sys

import numpy as np
import pandas as pd

from edu_data.agregados import cargar_largo, resumir
from edu_data.trayectoria import (
    CICLOS,
    CLAVES,
    DIR_OUTPUTS,
    PRIMARIA_7_ANIOS,
    archivo_de,
    leer_trayectoria,
    verificar_identidades,
)

# Umbrales de alerta. Son criterios de revisión, no de exclusión.
UMBRAL_SALTO_MATRICULA = 10.0  # % de variación interanual de la matrícula inicial
UMBRAL_SALTO_EGRESADOS = 20.0  # % de variación interanual de egresados
UMBRAL_DESVIO_COHERENCIA = 20.0  # % de desvío del cociente egresados/promovidos vs su mediana


# Problemas detectados y revisados a mano. provincias=None: todas; indicadores=None: todos.
# afecta_total: el problema pesa en el total país (si no, solo se marca en la provincia).
ALERTAS = [
    {
        "ciclos": [2021],
        "provincias": None,
        "indicadores": ["perdida", "saldo_privado"],
        "afecta_total": True,
        "texto": "Pase 2020→2021 afectado por la promoción acompañada de la pandemia",
    },
    {
        "ciclos": [2011, 2012, 2015, 2016, 2019, 2020],
        "provincias": ["Catamarca"],
        "indicadores": ["perdida", "saldo_privado"],
        "nivel": "secundaria",
        "texto": "Pases de año inconsistentes: alterna pérdidas y ganancias grandes",
    },
    {
        "ciclos": [2019, 2020],
        "provincias": ["Chubut"],
        "indicadores": ["perdida", "saldo_privado"],
        "nivel": "secundaria",
        "texto": "Pérdida de 9 % seguida de ganancia de 3 %: probable inconsistencia de matrícula",
    },
    {
        "ciclos": [2011, 2013],
        "provincias": ["La Rioja"],
        "indicadores": ["perdida", "saldo_privado"],
        "nivel": "secundaria",
        "texto": "Pases de año con saltos atípicos (8 % y −7 %)",
    },
    {
        "ciclos": [2020],
        "provincias": None,
        "indicadores": [
            "entrados",
            "scp",
            "ssp",
            "tasa_abandono",
            "tasa_salida_con_pase",
            "nopromo",
            "tasa_repitencia",
            "promovidos_efectivos",
            "promovidos_ex",
            "tasa_promocion",
        ],
        "afecta_total": True,
        "texto": "Pandemia: movilidad, abandono y repitencia caen bruscamente",
    },
    {
        "ciclos": [2010],
        "provincias": [
            "Santiago del Estero",
            "Jujuy",
            "Misiones",
            "Río Negro",
            "Salta",
            "San Juan",
        ],
        "indicadores": ["egresados"],
        "nivel": "secundaria",
        "afecta_total": True,
        "texto": "Egresados de secundaria bajos (suben 23–263 % en 2011; total país +16 %)",
    },
    {
        "ciclos": [2011],
        "provincias": ["Catamarca"],
        "indicadores": None,
        "nivel": "secundaria",
        "texto": "Matrícula secundaria cae 15 % y rebota 27 % el ciclo siguiente (cobertura)",
    },
    {
        "ciclos": [2019, 2020, 2021, 2022, 2023],
        "provincias": ["Santa Cruz"],
        "indicadores": ["nopromo", "tasa_repitencia", "tasa_promocion"],
        "nivel": "secundaria",
        "texto": "Repitencia secundaria cae de ~29 % a 4–11 % y vuelve a 27 % en 2024",
    },
    {
        "ciclos": [2024],
        "provincias": ["Buenos Aires"],
        "indicadores": ["nopromo", "promovidos_ex", "tasa_repitencia", "tasa_promocion"],
        "nivel": "secundaria",
        "afecta_total": True,
        "texto": "Cambio de régimen: nueva categoría de promovidos con materias pendientes; "
        "la repitencia cae a la mitad",
    },
    {
        "ciclos": [2020, 2021],
        "provincias": ["Entre Ríos"],
        "indicadores": ["ssp", "tasa_abandono"],
        "nivel": "primaria",
        "texto": "Abandono en primaria se cuadruplica dos años y vuelve al nivel previo",
    },
]


def alerta_para(ciclo, indicador, provincias=None, nivel=None) -> str:
    """Texto de las alertas que aplican. `provincias=None` = agregado que incluye a todas."""
    textos = []
    for a in ALERTAS:
        if ciclo not in a["ciclos"]:
            continue
        if a["indicadores"] is not None and indicador not in a["indicadores"]:
            continue
        if a.get("nivel") and nivel not in (None, a["nivel"]):
            continue
        if a["provincias"] is not None:
            if provincias is None and not a.get("afecta_total"):
                continue
            if provincias is not None and not set(_como_lista(provincias)) & set(a["provincias"]):
                continue
        textos.append(a["texto"])
    return " · ".join(textos)


def _como_lista(valor) -> list:
    return [valor] if isinstance(valor, str) else list(valor)


def control_estructural(ciclos=CICLOS) -> pd.DataFrame:
    """Por año: filas, identidades contables, claves vacías y columnas ausentes en el origen."""
    filas = []
    for ciclo in ciclos:
        df = leer_trayectoria(archivo_de(ciclo))
        ident = verificar_identidades(df)
        claves_vacias = df[CLAVES].eq("").any(axis=1)
        filas.append(
            {
                "ciclo": ciclo,
                "anio_archivo": archivo_de(ciclo),
                "filas": len(df),
                "provincias": df.provincia.nunique(),
                "departamentos": df.departamento.nunique(),
                "filas_enmascaradas": int(df.departamento.eq("Enmascarado").sum()),
                "filas_sin_datos": int(df.departamento.eq("Sin datos").sum()),
                "filas_clave_vacia": int(claves_vacias.sum()),
                "claves_duplicadas": int(df.duplicated(CLAVES).sum()),
                "fallas_flujo": int(ident.filas_falla_flujo.sum()),
                "fallas_resultado_sin_suf20": int(
                    ident.loc[ident.anio_estudio != "20", "filas_falla_resultado"].sum()
                ),
                "fallas_mujeres_mayor_total": int(ident.filas_mujeres_mayor_total.sum()),
                "columnas_ausentes": len(df.attrs["columnas_ausentes"]),
            }
        )
    return pd.DataFrame(filas)


def saltos_interanuales(
    largo: pd.DataFrame, indicador: str, umbral: float, nivel=("primaria", "secundaria")
) -> pd.DataFrame:
    """Provincia × nivel × año con variación interanual mayor al umbral (en %)."""
    t = resumir(largo, por=["provincia", "nivel"], nivel=list(nivel), indicadores=[indicador])
    t = t.sort_values(["provincia", "nivel", "ciclo"])
    t["anterior"] = t.groupby(["provincia", "nivel"], observed=True)[indicador].shift()
    t["variacion_pct"] = ((t[indicador] / t.anterior.replace(0, np.nan) - 1) * 100).round(1)
    alerta = t.variacion_pct.abs().gt(umbral) | (t[indicador].eq(0) & t.anterior.gt(0))
    return t.loc[alerta, ["ciclo", "provincia", "nivel", "anterior", indicador, "variacion_pct"]]


def coherencia_egresados(largo: pd.DataFrame) -> pd.DataFrame:
    """Egresados vs promovidos del último año del nivel, comparado con la mediana de la provincia.

    Primaria: último año 6° o 7° según la provincia. Secundaria: 12° más 13°–14°.
    """
    prom = resumir(largo, por=["provincia", "anio_estudio"], indicadores=["promovidos_efectivos"])
    ultimo_prim = np.where(prom.provincia.isin(PRIMARIA_7_ANIOS), "7", "6")
    prom["nivel"] = np.select(
        [prom.anio_estudio.eq(ultimo_prim), prom.anio_estudio.isin(["12", "1314"])],
        ["primaria", "secundaria"],
        default="",
    )
    prom = (
        prom[prom.nivel != ""]
        .groupby(["ciclo", "provincia", "nivel"], observed=True)
        .promovidos_efectivos.sum()
        .reset_index()
    )
    # Primaria: se compara lo informado; el indicador `egresados` ya es promovidos del último grado.
    egr = resumir(largo, por=["provincia", "nivel"], indicadores=["egresados"])
    informados = resumir(
        largo, por=["provincia"], nivel="primaria", indicadores=["egresados_informados"]
    ).assign(nivel="primaria")
    egr = egr.merge(informados, on=["ciclo", "provincia", "nivel"], how="left")
    es_prim = egr.nivel == "primaria"
    egr.loc[es_prim, "egresados"] = egr.loc[es_prim, "egresados_informados"]
    egr = egr.drop(columns="egresados_informados")
    t = prom.merge(egr, on=["ciclo", "provincia", "nivel"], how="left")
    t["cociente"] = (t.egresados / t.promovidos_efectivos.replace(0, np.nan)).round(3)
    mediana = t.groupby(["provincia", "nivel"], observed=True).cociente.transform("median")
    t["desvio_pct"] = ((t.cociente / mediana - 1) * 100).round(1)
    alerta = t.desvio_pct.abs().gt(UMBRAL_DESVIO_COHERENCIA) | t.egresados.fillna(0).eq(0)
    return t[alerta].sort_values(["provincia", "nivel", "ciclo"])


def tasas_atipicas(largo: pd.DataFrame, tasa: str = "tasa_repitencia", z: float = 3.0):
    """Provincia × nivel × año cuya tasa se aleja más de `z` desvíos robustos de su propia serie."""
    num = {
        "tasa_repitencia": "nopromo",
        "tasa_abandono": "ssp",
        "tasa_promocion": "promovidos_efectivos",
    }[tasa]
    t = resumir(
        largo, por=["provincia", "nivel"], nivel=["primaria", "secundaria"], indicadores=[num]
    )
    g = t.groupby(["provincia", "nivel"], observed=True)[tasa]
    mediana = g.transform("median")
    mad = g.transform(lambda s: (s - s.median()).abs().median()).replace(0, np.nan)
    t["z_robusto"] = ((t[tasa] - mediana) / (1.4826 * mad)).round(1)
    t["mediana_serie"] = mediana.round(2)
    columnas = ["ciclo", "provincia", "nivel", tasa, "mediana_serie", "z_robusto"]
    return t.loc[t.z_robusto.abs().gt(z), columnas]


def reporte(ciclos=CICLOS) -> dict[str, pd.DataFrame]:
    largo = cargar_largo()
    largo = largo[largo.ciclo.isin(ciclos)]
    salidas = {
        "estructural": control_estructural(ciclos),
        "saltos_matricula": saltos_interanuales(largo, "inicial", UMBRAL_SALTO_MATRICULA),
        "saltos_egresados": saltos_interanuales(largo, "egresados", UMBRAL_SALTO_EGRESADOS),
        "coherencia_egresados": coherencia_egresados(largo),
        "repitencia_atipica": tasas_atipicas(largo, "tasa_repitencia"),
        "abandono_atipico": tasas_atipicas(largo, "tasa_abandono"),
    }
    DIR_OUTPUTS.mkdir(exist_ok=True)
    for nombre, tabla in salidas.items():
        tabla.to_csv(DIR_OUTPUTS / f"validacion_{nombre}.csv", index=False)
    return salidas


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    ciclos = [int(a) for a in sys.argv[1:]] or CICLOS
    for nombre, tabla in reporte(ciclos).items():
        print(f"\n### {nombre} ({len(tabla)} filas)\n{tabla.to_string(index=False)}")
