"""Perfil de columnas e identidades contables de un dataset."""

import pandas as pd


def perfil_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Tipo, válidos, vacíos, ceros, suma, máximo y distintos por columna."""
    ausentes = set(df.attrs.get("columnas_ausentes", []))
    filas = []
    for columna in df.columns:
        serie = df[columna]
        numerica = pd.api.types.is_numeric_dtype(serie) and not pd.api.types.is_bool_dtype(serie)
        filas.append(
            {
                "columna": columna,
                "tipo": str(serie.dtype),
                "validos": int(serie.notna().sum()),
                "vacios": int(serie.isna().sum()),
                "pct_vacios": round(100 * serie.isna().mean(), 2) if len(serie) else 0.0,
                "ceros": int((serie == 0).sum()) if numerica else pd.NA,
                "suma": serie.sum() if numerica else pd.NA,
                "maximo": serie.max() if numerica else pd.NA,
                "distintos": int(serie.nunique()),
                "existe_en_origen": columna not in ausentes,
            }
        )
    return pd.DataFrame(filas).set_index("columna")


def verificar_identidades(
    df: pd.DataFrame, reglas: dict[str, str], tolerancia: float = 0
) -> pd.DataFrame:
    """Filas que no dan 0 en cada regla: "falla" o "no_evaluable" (algún término NA).

    Conteos por regla en attrs["resumen"].
    """
    resultados = []
    resumen = {}
    for nombre, expresion in reglas.items():
        residuo = pd.to_numeric(df.eval(expresion, engine="python"), errors="coerce")
        residuo = pd.Series(residuo, index=df.index).astype("Float64")
        no_evaluable = residuo.isna()
        falla = ~no_evaluable & (residuo.abs() > tolerancia)
        resumen[nombre] = {
            "ok": int((~no_evaluable & ~falla).sum()),
            "falla": int(falla.sum()),
            "no_evaluable": int(no_evaluable.sum()),
        }
        for estado, mascara in (("falla", falla), ("no_evaluable", no_evaluable)):
            mascara = mascara.fillna(False).astype(bool)
            resultados.append(
                pd.DataFrame(
                    {
                        "regla": nombre,
                        "fila": df.index[mascara],
                        "estado": estado,
                        "residuo": residuo[mascara].to_numpy(),
                    }
                )
            )
    salida = pd.concat(resultados, ignore_index=True)
    salida.attrs["resumen"] = resumen
    return salida
