"""Lectura y perfil de las bases de Trayectoria del Relevamiento Anual (RA, Educación Común)."""

import re
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DIR_RAW = RAIZ / "data" / "raw"
DIR_OUTPUTS = RAIZ / "outputs"

CLAVES = ["provincia", "departamento", "sector", "ambito"]

# Sufijo = año de estudio. 1314 agrupa 13° y 14° (técnica/artística); 20 = sin año definido.
SUFIJOS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "1314", "20"]

BLOQUES = [
    "inicial",
    "entrados",
    "scp",
    "ssp",
    "ultimo",
    "promovidos",
    "promovidos_ex",
    "promovidos_mas_2mat",
    "nopromo",
    "regulares",
    "otros",
]

EGRESADOS = [
    "primaria_egresados",
    "primaria_m_egresados",
    "secundaria_egresados",
    "secundaria_m_egresados",
]

# Estructura oficial del nivel primario (Ministerio de Educación); coincide con los datos.
PRIMARIA_7_ANIOS = {
    "Chaco",
    "Ciudad de Buenos Aires",
    "Jujuy",
    "La Rioja",
    "Mendoza",
    "Misiones",
    "Neuquén",
    "Río Negro",
    "Salta",
    "Santa Cruz",
    "Santa Fe",
    "Santiago del Estero",
}


def columnas_estandar() -> list[str]:
    """Esquema común a todos los años: claves, bloques × sexo × año de estudio y egresados."""
    conteos = [f"{pre}{b}_{suf}" for b in BLOQUES for pre in ["", "m_"] for suf in SUFIJOS]
    return CLAVES + conteos + EGRESADOS


# Cada archivo informa el ciclo lectivo anterior: el quiebre de la pandemia (ciclo 2020)
# aparece en el archivo 2021. Los egresados también se corren (todo el archivo).
DESFASE_CICLO = 1
ARCHIVOS = list(range(2011, 2026))


def ciclo_de(anio_archivo: int) -> int:
    return anio_archivo - DESFASE_CICLO


def archivo_de(ciclo: int) -> int:
    return ciclo + DESFASE_CICLO


CICLOS = [ciclo_de(a) for a in ARCHIVOS]


def ruta_trayectoria(anio_archivo: int) -> Path:
    return DIR_RAW / f"{anio_archivo} Trayectoria - agregada(in).csv"


def leer_trayectoria(anio_archivo: int) -> pd.DataFrame:
    """Devuelve la base con el esquema estándar, vacíos como NA y conteos como Int64.

    Las columnas que no existen en el archivo de ese año se agregan vacías y quedan en
    `df.attrs["columnas_ausentes"]`.
    """
    df = pd.read_csv(
        ruta_trayectoria(anio_archivo),
        sep=";",
        encoding="latin-1",
        dtype=str,
        keep_default_na=False,
    )
    df.columns = df.columns.str.strip().str.lower()
    for col in CLAVES:
        df[col] = df[col].str.strip()
    # 2021 trae una fila (BA, Enmascarado, Privado) sin ámbito.
    df[CLAVES] = df[CLAVES].replace("", "Sin dato")
    # El origen trae "1º" mal codificado como "1§" en algunos departamentos.
    df["departamento"] = df["departamento"].str.replace("§", "º", regex=False)
    conteos = [c for c in df.columns if c not in CLAVES]
    for col in conteos:
        df[col] = pd.to_numeric(df[col].str.strip().replace("", pd.NA)).astype("Int64")
    estandar = columnas_estandar()
    extra = sorted(set(df.columns) - set(estandar))
    if extra:
        raise ValueError(f"{anio_archivo}: columnas fuera del esquema estándar: {extra}")
    ausentes = [c for c in estandar if c not in df.columns]
    df = df.reindex(columns=estandar)
    df[ausentes] = df[ausentes].astype("Int64")
    df.insert(0, "anio_archivo", anio_archivo)
    df.insert(0, "ciclo", ciclo_de(anio_archivo))
    df.attrs["columnas_ausentes"] = ausentes
    return df


def separar_columna(col: str) -> tuple[str, str, str] | None:
    """Parte una columna de conteo en (bloque, sexo, año de estudio)."""
    m = re.fullmatch(r"(m_)?([a-z_0-9]+?)_(\d+)", col)
    if not m or m.group(2) not in BLOQUES:
        return None
    return m.group(2), "mujeres" if m.group(1) else "total", m.group(3)


def perfil_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla por columna: tipo, n válidos, n vacíos, % vacío, ceros, suma y máximo."""
    filas = []
    for col in df.columns:
        s = df[col]
        es_num = pd.api.types.is_numeric_dtype(s)
        partes = separar_columna(col)
        filas.append(
            {
                "variable": col,
                "bloque": partes[0] if partes else col,
                "sexo": partes[1] if partes else "",
                "anio_estudio": partes[2] if partes else "",
                "existe_en_origen": col not in df.attrs.get("columnas_ausentes", []),
                "tipo": str(s.dtype),
                "n_validos": int(s.notna().sum()),
                "n_vacios": int(s.isna().sum()),
                "pct_vacios": round(s.isna().mean() * 100, 2),
                "n_ceros": int((s == 0).sum()) if es_num else None,
                "suma": int(s.sum()) if es_num else None,
                "maximo": int(s.max()) if es_num and s.notna().any() else None,
                "n_distintos": int(s.nunique()),
            }
        )
    return pd.DataFrame(filas)


def verificar_identidades(df: pd.DataFrame) -> pd.DataFrame:
    """Cuenta filas que violan: inicial+entrados-scp-ssp=ultimo y ultimo=suma de resultados."""
    z = df.fillna(0)
    resultado = []
    for suf in SUFIJOS:
        flujo = (
            z[f"inicial_{suf}"]
            + z[f"entrados_{suf}"]
            - z[f"scp_{suf}"]
            - z[f"ssp_{suf}"]
            - z[f"ultimo_{suf}"]
        )
        promos = (
            z[f"promovidos_{suf}"]
            + z[f"promovidos_ex_{suf}"]
            + z[f"promovidos_mas_2mat_{suf}"]
            + z[f"nopromo_{suf}"]
        )
        resultado.append(
            {
                "anio_estudio": suf,
                "filas_falla_flujo": int((flujo != 0).sum()),
                "filas_falla_resultado": int((z[f"ultimo_{suf}"] - promos != 0).sum()),
                "filas_mujeres_mayor_total": int(
                    (z[f"m_inicial_{suf}"] > z[f"inicial_{suf}"]).sum()
                ),
            }
        )
    return pd.DataFrame(resultado)


if __name__ == "__main__":
    ciclo = int(sys.argv[1]) if len(sys.argv) > 1 else CICLOS[-1]
    base = leer_trayectoria(archivo_de(ciclo))
    DIR_OUTPUTS.mkdir(exist_ok=True)
    perfil_nulos(base).to_csv(DIR_OUTPUTS / f"perfil_trayectoria_ciclo_{ciclo}.csv", index=False)
    print(f"ciclo {ciclo} (archivo {archivo_de(ciclo)}): {base.shape[0]} filas x {base.shape[1]}")
    print(verificar_identidades(base).to_string(index=False))
