"""Lectura de archivos oficiales: formato, CSV con encodings locales, esquemas y Excel."""

import csv
import re
from collections.abc import Hashable, Iterable
from pathlib import Path

import pandas as pd

ENCODINGS = ("utf-8", "cp1252", "latin-1")
SEPARADORES = ";,\t|"

_CEROS_IZQUIERDA = re.compile(r"^0\d+$")
_ENTERO = re.compile(r"^-?\d+$")
_DECIMAL = re.compile(r"^-?\d*\.\d+$|^-?\d+\.?$")


def _decodificar(muestra: bytes) -> tuple[str, str]:
    for encoding in ENCODINGS:
        try:
            return encoding, muestra.decode(encoding)
        except UnicodeDecodeError as error:
            # La muestra puede cortar un carácter multibyte al final: no invalida el encoding
            if encoding == "utf-8" and error.start >= len(muestra) - 3:
                return encoding, muestra[: error.start].decode(encoding)
    raise ValueError("No se pudo decodificar con ningún encoding conocido")


def detectar_formato(ruta: str | Path, n_bytes: int = 200_000) -> dict:
    """Encoding, separador, finales de línea y encabezado de un CSV, a partir de una muestra."""
    muestra = Path(ruta).read_bytes()[:n_bytes]
    bom = muestra.startswith(b"\xef\xbb\xbf")
    encoding, texto = _decodificar(muestra[3:] if bom else muestra)
    lineas = texto.splitlines()
    try:
        sep = csv.Sniffer().sniff("\n".join(lineas[:20]), delimiters=SEPARADORES).delimiter
    except csv.Error:
        sep = max(SEPARADORES, key=lambda s: lineas[0].count(s)) if lineas else ","
    return {
        "encoding": "utf-8-sig" if bom else encoding,
        "sep": sep,
        "crlf": b"\r\n" in muestra,
        "encabezado": [c.strip() for c in lineas[0].split(sep)] if lineas else [],
    }


def _tipar_columna(serie: pd.Series, decimal: str) -> pd.Series:
    valores = serie.dropna()
    if valores.empty:
        return serie.astype("string")
    if valores.str.match(_CEROS_IZQUIERDA).any():
        return serie.astype("string")
    if valores.str.match(_ENTERO).all():
        return serie.astype("Int64")
    normalizados = serie.str.replace(decimal, ".", regex=False) if decimal != "." else serie
    if normalizados.dropna().str.match(_DECIMAL).all():
        return normalizados.astype("Float64")
    return serie.astype("string")


def leer_csv_oficial(
    ruta: str | Path,
    sep: str | None = None,
    encoding: str | None = None,
    claves: Iterable[str] = (),
    vacios: Iterable[str] = ("",),
    decimal: str = ".",
) -> pd.DataFrame:
    """Lee un CSV oficial: minúsculas, strip, vacíos → NA, conteos → Int64.

    Las `claves` y las columnas con ceros a la izquierda quedan como texto.
    """
    formato = detectar_formato(ruta)
    sep = sep or formato["sep"]
    encoding = encoding or formato["encoding"]
    crudo = pd.read_csv(ruta, sep=sep, encoding=encoding, dtype=str, keep_default_na=False)
    crudo.columns = [c.strip().lower() for c in crudo.columns]

    # Los vacíos se comparan después del strip: " " y "" son el mismo vacío
    vacios = {v.strip() for v in vacios} | {""}
    claves = {c.lower() for c in claves}
    df = pd.DataFrame(index=crudo.index)
    texto_por_ceros = []
    for columna in crudo.columns:
        serie = crudo[columna].str.strip().astype("string")
        serie = serie.mask(serie.isin(vacios))
        if columna in claves:
            df[columna] = serie
            continue
        df[columna] = _tipar_columna(serie, decimal)
        if df[columna].dtype == "string" and serie.dropna().str.match(_CEROS_IZQUIERDA).any():
            texto_por_ceros.append(columna)

    df.attrs["formato"] = {**formato, "sep": sep, "encoding": encoding}
    df.attrs["columnas_texto_por_ceros"] = texto_por_ceros
    return df


def unificar_esquema(
    dfs: dict[Hashable, pd.DataFrame], columnas: list[str] | None = None
) -> dict[Hashable, pd.DataFrame]:
    """Lleva cada período al esquema común; ausentes → NA, en attrs["columnas_ausentes"]."""
    if columnas is None:
        columnas = list(dict.fromkeys(c for df in dfs.values() for c in df.columns))
    tipos = {}
    for df in dfs.values():
        for columna in df.columns:
            tipos.setdefault(columna, df[columna].dtype)

    unificados = {}
    for periodo, df in dfs.items():
        ausentes = [c for c in columnas if c not in df.columns]
        nuevo = df.reindex(columns=columnas)
        for columna in ausentes:
            if columna in tipos:
                nuevo[columna] = nuevo[columna].astype(tipos[columna])
        nuevo.attrs = {**df.attrs, "columnas_ausentes": ausentes}
        unificados[periodo] = nuevo
    return unificados


def diff_columnas(dfs: dict[Hashable, pd.DataFrame]) -> pd.DataFrame:
    """Presencia de cada columna por período (sin distinguir mayúsculas) y sus grafías."""
    filas = {}
    for periodo, df in dfs.items():
        for columna in df.columns:
            fila = filas.setdefault(str(columna).strip().lower(), {"grafias": set()})
            fila[periodo] = True
            fila["grafias"].add(str(columna))
    tabla = pd.DataFrame.from_dict(filas, orient="index")
    periodos = list(dfs)
    tabla[periodos] = tabla.reindex(columns=periodos).fillna(False).astype(bool)
    tabla["grafias"] = tabla["grafias"].map(lambda g: ", ".join(sorted(g)))
    tabla["en_todos"] = tabla[periodos].all(axis=1)
    return tabla[[*periodos, "en_todos", "grafias"]].sort_values("en_todos", kind="stable")


def listar_hojas(ruta_excel: str | Path, n_filas: int = 3) -> pd.DataFrame:
    """Nombre, dimensiones y primeras filas no vacías de cada hoja de un Excel."""
    hojas = pd.read_excel(ruta_excel, sheet_name=None, header=None, dtype=str)
    filas = []
    for nombre, hoja in hojas.items():
        hoja = hoja.dropna(how="all").dropna(axis=1, how="all")
        primeras = [" | ".join(f.dropna()) for _, f in hoja.head(n_filas).iterrows()]
        filas.append(
            {
                "hoja": nombre,
                "filas": len(hoja),
                "columnas": hoja.shape[1],
                "primeras_filas": "\n".join(primeras),
            }
        )
    return pd.DataFrame(filas)


def _es_numero(valor: str) -> bool:
    return bool(_ENTERO.match(valor) or _DECIMAL.match(valor))


def _detectar_fila_encabezado(hoja: pd.DataFrame) -> int:
    # Las hojas oficiales suelen traer títulos arriba: se busca la primera fila "ancha" de textos
    completas = hoja.notna().sum(axis=1)
    for posicion, (_, fila) in enumerate(hoja.iterrows()):
        valores = [str(v).strip() for v in fila.dropna()]
        textos = sum(not _es_numero(v) for v in valores)
        if completas.iloc[posicion] >= completas.max() / 2 and textos > len(valores) / 2:
            return posicion
    return 0


def leer_hoja(
    ruta_excel: str | Path, hoja: str | int, fila_encabezado: int | None = None
) -> pd.DataFrame:
    """Lee una hoja como texto; si no se indica, detecta la fila de encabezado (base 0)."""
    crudo = pd.read_excel(ruta_excel, sheet_name=hoja, header=None, dtype=str)
    crudo = crudo.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    if fila_encabezado is None:
        fila_encabezado = _detectar_fila_encabezado(crudo)
    encabezado = [str(c).strip() for c in crudo.iloc[fila_encabezado]]
    df = crudo.iloc[fila_encabezado + 1 :].reset_index(drop=True)
    df.columns = encabezado
    df.attrs["fila_encabezado"] = fila_encabezado
    return df.astype("string")
