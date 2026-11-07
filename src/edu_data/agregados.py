"""Formato largo y agregación flexible de las bases de Trayectoria."""

import sys
from collections.abc import Iterable

import numpy as np
import pandas as pd

from edu_data.trayectoria import (
    BLOQUES,
    CICLOS,
    CLAVES,
    DIR_OUTPUTS,
    PRIMARIA_7_ANIOS,
    RAIZ,
    SUFIJOS,
    archivo_de,
    leer_trayectoria,
)

RUTA_LARGO = RAIZ / "data" / "processed" / "trayectoria_largo.parquet"

DIMENSIONES = [
    "ciclo",
    "provincia",
    "departamento",
    "sector",
    "ambito",
    "nivel",
    "anio_estudio",
    "sexo",
]

SEXOS = {"total": "", "mujeres": "m_", "varones": "v_"}

# promovidos_efectivos = promovidos + promovidos_ex + promovidos_mas_2mat: comparable entre años.
# ultimo_con_resultado: matrícula final solo donde hay resultados (excluye casi todo el sufijo 20).
INDICADORES_DERIVADOS = ["promovidos_efectivos", "ultimo_con_resultado"]

TASAS = {
    "tasa_abandono": ("ssp", ["inicial", "entrados"]),
    "tasa_salida_con_pase": ("scp", ["inicial", "entrados"]),
    "tasa_repitencia": ("nopromo", ["ultimo_con_resultado"]),
    "tasa_promocion": ("promovidos_efectivos", ["ultimo_con_resultado"]),
}


def _agregar_varones_y_derivados(df: pd.DataFrame) -> pd.DataFrame:
    nuevas = {}
    for suf in SUFIJOS:
        for bloque in BLOQUES:
            total, muj = f"{bloque}_{suf}", f"m_{bloque}_{suf}"
            if total in df:
                nuevas[f"v_{bloque}_{suf}"] = df[total] - df[muj].fillna(0)
    for nivel in ["primaria", "secundaria"]:
        nuevas[f"{nivel}_v_egresados"] = df[f"{nivel}_egresados"] - df[
            f"{nivel}_m_egresados"
        ].fillna(0)
    df = pd.concat([df, pd.DataFrame(nuevas, index=df.index)], axis=1)

    nuevas = {}
    for pre in SEXOS.values():
        for suf in SUFIJOS:
            promo = df[f"{pre}promovidos_{suf}"]
            extra = df[f"{pre}promovidos_ex_{suf}"].fillna(0)
            extra = extra + df[f"{pre}promovidos_mas_2mat_{suf}"].fillna(0)
            nuevas[f"{pre}promovidos_efectivos_{suf}"] = promo + extra
            nuevas[f"{pre}ultimo_con_resultado_{suf}"] = df[f"{pre}ultimo_{suf}"].where(
                promo.notna()
            )
    return pd.concat([df, pd.DataFrame(nuevas, index=df.index)], axis=1)


def _mapa_columnas(columnas: Iterable[str]) -> pd.DataFrame:
    filas = []
    bloques = BLOQUES + INDICADORES_DERIVADOS
    for col in columnas:
        for sexo, pre in SEXOS.items():
            for nivel in ["primaria", "secundaria"]:
                if col == f"{nivel}_{pre}egresados":
                    filas.append((col, "egresados", sexo, "", nivel))
            for bloque in bloques:
                for suf in SUFIJOS:
                    if col == f"{pre}{bloque}_{suf}":
                        filas.append((col, bloque, sexo, suf, None))
    return pd.DataFrame(
        filas, columns=["variable", "indicador", "sexo", "anio_estudio", "nivel_fijo"]
    )


def _asignar_nivel(provincia: pd.Series, anio_estudio: pd.Series) -> np.ndarray:
    grado = pd.to_numeric(anio_estudio.replace({"1314": "13"}), errors="coerce")
    ultimo_primaria = np.where(provincia.isin(PRIMARIA_7_ANIOS), 7, 6)
    return np.select(
        [anio_estudio.eq("20"), grado <= ultimo_primaria, grado > ultimo_primaria],
        ["sin_definir", "primaria", "secundaria"],
        default=None,
    )


def _corregir_egresados_primaria(largo: pd.DataFrame) -> pd.DataFrame:
    """Egresados de primaria = promovidos del último grado (6° o 7° según la estructura oficial).

    Desde 2013 coinciden con lo informado (cociente 1,000); antes, lo informado está incompleto en
    muchas provincias. El valor informado se conserva como indicador `egresados_informados`.
    """
    es_prim = (largo.indicador == "egresados") & (largo.nivel == "primaria")
    largo.loc[es_prim, "indicador"] = "egresados_informados"
    ultimo = np.where(largo.provincia.isin(PRIMARIA_7_ANIOS), "7", "6")
    promovidos_ultimo = (largo.indicador == "promovidos_efectivos") & (largo.anio_estudio == ultimo)
    estimados = largo[promovidos_ultimo].copy()
    estimados["indicador"] = "egresados"
    estimados["anio_estudio"] = ""
    estimados["nivel"] = "primaria"
    return pd.concat([largo, estimados], ignore_index=True)


def a_formato_largo(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por agregado × año de estudio × sexo × indicador. Descarta vacíos (sin oferta)."""
    df = _agregar_varones_y_derivados(df.drop(columns="anio_archivo"))
    mapa = _mapa_columnas(df.columns)
    largo = (
        df.melt(id_vars=["ciclo", *CLAVES], value_vars=mapa.variable.tolist(), var_name="variable")
        .dropna(subset=["value"])
        .merge(mapa, on="variable")
        .rename(columns={"value": "valor"})
    )
    largo["nivel"] = largo.nivel_fijo.fillna(
        pd.Series(_asignar_nivel(largo.provincia, largo.anio_estudio), index=largo.index)
    )
    largo["valor"] = largo.valor.astype("int64")
    largo = _corregir_egresados_primaria(largo[[*DIMENSIONES, "indicador", "valor"]])
    for col in DIMENSIONES[1:] + ["indicador"]:
        largo[col] = largo[col].astype("category")
    return largo


def construir_largo(ciclos: Iterable[int] = CICLOS) -> pd.DataFrame:
    """Base larga de los ciclos pedidos (por defecto todos), indexada por ciclo lectivo."""
    archivos = [archivo_de(c) for c in ciclos]
    largo = pd.concat([a_formato_largo(leer_trayectoria(a)) for a in archivos], ignore_index=True)
    for col in DIMENSIONES[1:] + ["indicador"]:
        largo[col] = largo[col].astype(str).astype("category")
    RUTA_LARGO.parent.mkdir(parents=True, exist_ok=True)
    largo.to_parquet(RUTA_LARGO, index=False)
    return largo


def cargar_largo() -> pd.DataFrame:
    return pd.read_parquet(RUTA_LARGO) if RUTA_LARGO.exists() else construir_largo()


def _como_lista(valor) -> list | None:
    if valor is None:
        return None
    return [valor] if isinstance(valor, str | int) else list(valor)


def resumir(
    largo: pd.DataFrame,
    por: Iterable[str] = (),
    ciclo=None,
    provincia=None,
    departamento=None,
    sector=None,
    ambito=None,
    nivel=None,
    anio_estudio=None,
    sexo=None,
    indicadores: Iterable[str] | None = None,
    tasas: bool = True,
) -> pd.DataFrame:
    """Suma indicadores por las dimensiones de `por`; el resto se agrega (total).

    Cada filtro acepta un valor o una lista. Sin filtros ni `por` devuelve el total país por año.
    `ciclo` siempre queda como dimensión: nunca se suman ciclos entre sí.
    `sexo` por defecto es "total"; si "sexo" está en `por`, se usan total, mujeres y varones.
    Las tasas se calculan como cociente de sumas, después de agregar.
    """
    por = list(por)
    if "ciclo" not in por:
        por = ["ciclo", *por]
    desconocidas = set(por) - set(DIMENSIONES)
    if desconocidas:
        raise ValueError(f"Dimensiones no válidas: {desconocidas}. Opciones: {DIMENSIONES}")
    if sexo is None and "sexo" not in por:
        sexo = "total"

    filtros = {
        "ciclo": ciclo,
        "provincia": provincia,
        "departamento": departamento,
        "sector": sector,
        "ambito": ambito,
        "nivel": nivel,
        "anio_estudio": anio_estudio,
        "sexo": sexo,
    }
    mascara = pd.Series(True, index=largo.index)
    for dim, valor in filtros.items():
        valores = _como_lista(valor)
        if valores is not None:
            mascara &= largo[dim].isin(valores)

    necesarios = set(indicadores) if indicadores else None
    if necesarios is not None and tasas:
        for num, den in TASAS.values():
            if num in necesarios:
                necesarios |= {num, *den}
    sub = largo[mascara]
    if necesarios is not None:
        sub = sub[sub.indicador.isin(necesarios)]

    tabla = sub.pivot_table(
        index=por,
        columns="indicador",
        values="valor",
        aggfunc="sum",
        observed=True,
        fill_value=0,
    )
    tabla.columns.name = None

    if tasas:
        for nombre, (num, den) in TASAS.items():
            if num in tabla and all(d in tabla for d in den):
                denominador = sum(tabla[d] for d in den).replace(0, np.nan)
                tabla[nombre] = (tabla[num] / denominador * 100).round(2)
    if indicadores:
        pedidas = [c for c in indicadores if c in tabla]
        tasas_ok = [t for t, (n, _) in TASAS.items() if tasas and n in indicadores and t in tabla]
        tabla = tabla[pedidas + tasas_ok]
    return tabla.reset_index()


CLAVES_CONTINUIDAD = ["provincia", "sector", "ambito", "sexo"]


def continuidad(largo: pd.DataFrame) -> pd.DataFrame:
    """Pase de año de estudio g (ciclo t) a g+1 (ciclo t+1), por provincia × sector × ámbito × sexo.

    esperados = promovidos de g en t + no promovidos de g+1 en t (recursan g+1).
    En 12° los no promovidos adeudan materias y no recursan: no se cuentan como esperados.
    reales = matrícula inicial de g+1 en t+1. perdida = esperados − reales (negativo: entran más).
    El pase se asigna al ciclo y al nivel de destino (el pase 6°→7° o 7°→8° cuenta en secundaria).
    Sexo solo mujeres/varones; 13°–14° y sin año definido quedan afuera.
    """
    grados = [str(g) for g in range(1, 13)]
    base = largo[
        largo.indicador.isin(["promovidos_efectivos", "nopromo", "inicial"])
        & largo.anio_estudio.isin(grados)
        & largo.sexo.isin(["mujeres", "varones"])
    ]
    t = base.pivot_table(
        index=[*CLAVES_CONTINUIDAD, "anio_estudio", "ciclo"],
        columns="indicador",
        values="valor",
        aggfunc="sum",
        observed=True,
        fill_value=0,
    ).reset_index()
    t["grado"] = t.anio_estudio.astype(str).astype(int)
    for col in CLAVES_CONTINUIDAD:
        t[col] = t[col].astype(str)

    origen = t[[*CLAVES_CONTINUIDAD, "grado", "ciclo", "promovidos_efectivos"]].copy()
    origen["grado"] += 1
    origen["ciclo"] += 1
    recursan = t[[*CLAVES_CONTINUIDAD, "grado", "ciclo", "nopromo"]].copy()
    recursan.loc[recursan.grado == 12, "nopromo"] = 0
    recursan["ciclo"] += 1
    destino = t[[*CLAVES_CONTINUIDAD, "grado", "ciclo", "inicial"]]

    claves = [*CLAVES_CONTINUIDAD, "grado", "ciclo"]
    c = origen.merge(recursan, on=claves, how="outer").merge(destino, on=claves, how="outer")
    c = c[(c.grado >= 2) & (c.grado <= 12) & c.ciclo.between(min(CICLOS) + 1, max(CICLOS))]
    c = c.fillna({"promovidos_efectivos": 0, "nopromo": 0, "inicial": 0})
    c["esperados"] = (c.promovidos_efectivos + c.nopromo).astype("int64")
    c["reales"] = c.inicial.astype("int64")
    c["perdida"] = c.esperados - c.reales
    ultimo_primaria = np.where(c.provincia.astype(str).isin(PRIMARIA_7_ANIOS), 7, 6)
    c["nivel"] = np.where(c.grado <= ultimo_primaria, "primaria", "secundaria")
    c["anio_estudio"] = c.grado.astype(str)
    columnas = ["nivel", "anio_estudio", "ciclo", "esperados", "reales", "perdida"]
    return c[[*CLAVES_CONTINUIDAD, *columnas]]


CORTES = {
    "total": [],
    "sector": ["sector"],
    "ambito": ["ambito"],
    "sector_ambito": ["sector", "ambito"],
}


def tabla_provincial(largo: pd.DataFrame, incluir_pais: bool = True) -> pd.DataFrame:
    """Provincia × nivel × corte (total, sector, ámbito, sector×ámbito) × sexo, por año."""
    partes = []
    geografias = [["provincia"], []] if incluir_pais else [["provincia"]]
    for geo in geografias:
        for corte, dims in CORTES.items():
            t = resumir(largo, por=["ciclo", *geo, "nivel", *dims, "sexo"])
            t.insert(1, "corte", corte)
            partes.append(t)
    tabla = pd.concat(partes, ignore_index=True)
    tabla["provincia"] = tabla["provincia"].astype(object).fillna("Total país")
    for col in ["sector", "ambito"]:
        tabla[col] = tabla[col].astype(object).fillna("Total")
    orden = ["ciclo", "provincia", "nivel", "corte", "sector", "ambito", "sexo"]
    resto = [c for c in tabla.columns if c not in orden]
    return tabla[orden + resto].sort_values(orden, ignore_index=True)


if __name__ == "__main__":
    ciclos = [int(a) for a in sys.argv[1:]] or CICLOS
    largo = construir_largo(ciclos)
    tabla = tabla_provincial(largo)
    DIR_OUTPUTS.mkdir(exist_ok=True)
    tabla.to_csv(DIR_OUTPUTS / "trayectoria_provincias.csv", index=False)
    print(f"largo: {len(largo):,} filas → {RUTA_LARGO}")
    print(f"tabla provincial: {tabla.shape} → {DIR_OUTPUTS / 'trayectoria_provincias.csv'}")
