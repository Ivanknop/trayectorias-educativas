"""Controles de pertinencia de series (saltos, atípicos, coherencia) y registro de alertas."""

from collections.abc import Sequence
from dataclasses import dataclass, field

import pandas as pd

# Constante de consistencia del MAD con el desvío estándar en una normal
_K_MAD = 0.6745


def _como_lista(grupo: str | Sequence[str]) -> list[str]:
    return [grupo] if isinstance(grupo, str) else list(grupo)


def saltos_interanuales(
    t: pd.DataFrame,
    valor: str,
    grupo: str | Sequence[str],
    periodo: str = "periodo",
    umbral: float = 0.10,
) -> pd.DataFrame:
    """Filas cuya variación contra el período anterior del grupo supera `umbral` (0.10 = 10 %)."""
    grupo = _como_lista(grupo)
    ordenado = t.sort_values([*grupo, periodo]).copy()
    previos = ordenado.groupby(grupo, dropna=False)[[periodo, valor]].shift()
    ordenado["periodo_anterior"] = previos[periodo]
    ordenado["valor_anterior"] = previos[valor]
    base = ordenado["valor_anterior"].astype("Float64")
    ordenado["variacion"] = ordenado[valor].astype("Float64") / base.mask(base == 0) - 1
    marcados = ordenado["variacion"].abs() > umbral
    return ordenado[marcados.fillna(False).astype(bool)]


def atipicos_robustos(
    t: pd.DataFrame, valor: str, grupo: str | Sequence[str], z: float = 3.0
) -> pd.DataFrame:
    """Valores alejados de la propia serie: z robusto (mediana y MAD por grupo) mayor a `z`."""
    grupo = _como_lista(grupo)
    datos = t.copy()
    x = datos[valor].astype("Float64")
    agrupado = x.groupby([datos[g] for g in grupo], dropna=False)
    datos["mediana"] = agrupado.transform("median")
    desvio = (x - datos["mediana"]).abs()
    datos["mad"] = desvio.groupby([datos[g] for g in grupo], dropna=False).transform("median")
    datos["z_robusto"] = _K_MAD * (x - datos["mediana"]) / datos["mad"].mask(datos["mad"] == 0)
    marcados = datos["z_robusto"].abs() > z
    return datos[marcados.fillna(False).astype(bool)]


def coherencia(
    t: pd.DataFrame, a: str, b: str, grupo: str | Sequence[str], umbral_pct: float = 0.10
) -> pd.DataFrame:
    """Filas donde el cociente a/b se aparta más de `umbral_pct` de la mediana de su grupo."""
    grupo = _como_lista(grupo)
    datos = t.copy()
    denominador = datos[b].astype("Float64")
    datos["cociente"] = datos[a].astype("Float64") / denominador.mask(denominador == 0)
    referencia = datos.groupby(grupo, dropna=False)["cociente"].transform("median")
    datos["cociente_mediana"] = referencia
    datos["desvio_pct"] = datos["cociente"] / referencia.mask(referencia == 0) - 1
    marcados = datos["desvio_pct"].abs() > umbral_pct
    return datos[marcados.fillna(False).astype(bool)]


@dataclass
class Alerta:
    """Problema de datos revisado. None en unidades/indicadores = aplica a todos."""

    periodos: list
    texto: str
    unidades: list[str] | None = None
    indicadores: list[str] | None = None
    filtros: dict[str, str] = field(default_factory=dict)
    afecta_total: bool = False

    def aplica(self, periodo, indicador: str, unidades=None, **filtros) -> bool:
        """`unidades=None` es el total: solo aplica si la alerta lo afecta o no tiene unidades."""
        if periodo not in self.periodos:
            return False
        if self.indicadores is not None and indicador not in self.indicadores:
            return False
        if self.unidades is not None:
            if unidades is None:
                if not self.afecta_total:
                    return False
            elif not set(self.unidades) & set(_como_lista(unidades)):
                return False
        return all(filtros.get(k, v) == v for k, v in self.filtros.items())


def alerta_para(
    alertas: Sequence[Alerta], periodo, indicador: str, unidades=None, **filtros
) -> str | None:
    """Textos de las alertas que aplican a un punto de una visualización, o None."""
    textos = [a.texto for a in alertas if a.aplica(periodo, indicador, unidades, **filtros)]
    return " | ".join(textos) if textos else None
