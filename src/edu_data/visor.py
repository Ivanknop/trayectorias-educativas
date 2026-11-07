"""Visor estático on demand: índice → mapa de provincias → panel con líneas por ciclo.

Los datos se exportan al grano mínimo (provincia × nivel × sector × ámbito × sexo × ciclo) y el
navegador suma según los botones elegidos. Las tasas se calculan después de sumar.
"""

import html
import json
import shutil
from pathlib import Path

import pandas as pd
import plotly

from edu_data.agregados import TASAS, cargar_largo, construir_largo, continuidad, resumir
from edu_data.geo import cargar_provincias_svg
from edu_data.trayectoria import CICLOS, DIR_OUTPUTS
from edu_data.validacion import ALERTAS, alerta_para

DIR_VISOR = DIR_OUTPUTS / "visor"
DIR_PLANTILLAS = Path(__file__).parent / "plantillas"
TOTAL_PAIS = "Total país"
NIVELES = ["primaria", "secundaria"]

CONTEOS = [
    "inicial",
    "entrados",
    "ssp",
    "nopromo",
    "promovidos_efectivos",
    "ultimo_con_resultado",
    "egresados",
]
# Pases de año (agregados.continuidad): solo existen desde el ciclo 2011.
CONTEOS_CONTINUIDAD = ["esperados", "perdida"]

# Indicador del visor → conteo que muestra en "Cantidad" y tasa de agregados.TASAS (None: sin tasa).
# `alertas`: nombres con los que ALERTAS se refiere a este indicador.
INDICADORES = {
    "repitencia": {
        "etiqueta": "Repitencia",
        "cantidad": "nopromo",
        "tasa": "tasa_repitencia",
        "unidad": "no promovidos",
        "descripcion": "Alumnos que terminan el ciclo sin ser promovidos y deben recursar el año.",
        "formula_texto": "Tasa = no promovidos / matrícula al último día de clases × 100.",
        "alertas": ["nopromo", "tasa_repitencia"],
    },
    "abandono": {
        "etiqueta": "Abandono",
        "cantidad": "ssp",
        "tasa": "tasa_abandono",
        "unidad": "salidos sin pase",
        "descripcion": "Alumnos que dejan la escuela durante el ciclo sin pedir pase a otra.",
        "formula_texto": "Tasa = salidos sin pase / (matrícula inicial + entrados) × 100.",
        "alertas": ["ssp", "tasa_abandono"],
    },
    "promocion": {
        "etiqueta": "Promoción",
        "cantidad": "promovidos_efectivos",
        "tasa": "tasa_promocion",
        "unidad": "promovidos",
        "descripcion": "Promovidos al cierre, tras examen o con materias pendientes.",
        "formula_texto": "Tasa = promovidos / matrícula al último día de clases × 100.",
        "alertas": ["promovidos_efectivos", "tasa_promocion", "promovidos_ex"],
    },
    "matricula": {
        "etiqueta": "Matrícula",
        "cantidad": "inicial",
        "tasa": None,
        "unidad": "alumnos",
        "descripcion": "Alumnos matriculados al inicio del ciclo lectivo.",
        "formula_texto": "",
        "alertas": ["inicial"],
    },
    "egreso": {
        "etiqueta": "Egreso",
        "cantidad": "egresados",
        "tasa": None,
        "unidad": "egresados",
        "descripcion": (
            "Alumnos que terminan el nivel en el ciclo. En primaria se toman los promovidos del "
            "último grado (6° o 7° según la estructura oficial), porque lo informado "
            "está incompleto en 2010–2012."
        ),
        "formula_texto": "",
        "alertas": ["egresados"],
    },
    "perdida": {
        "etiqueta": "Pérdida entre años",
        "cantidad": "perdida",
        "tasa": None,
        "formula": {"numerador": "perdida", "denominadores": ["esperados"]},
        "primer_ciclo": CICLOS[0] + 1,
        "unidad": "alumnos que no se reinscriben",
        "descripcion": (
            "Alumnos que promovieron (o debían recursar) y no aparecen inscriptos al año "
            "siguiente: abandono entre ciclos, pase a adultos u otra modalidad. Negativo: "
            "llegan más de los esperados (desde otra provincia, sector o ámbito)."
        ),
        "formula_texto": (
            "Tasa = (esperados − inscriptos) / esperados × 100; esperados = promovidos del año "
            "anterior + recursantes. El valor de cada ciclo es el pase desde el ciclo previo."
        ),
        "alertas": ["perdida"],
    },
    "privado": {
        "etiqueta": "Estatal → privado",
        "cantidad": "saldo_privado",
        "tasa": None,
        "formula": {"especial": "participacion_privada"},
        "primer_ciclo_cantidad": CICLOS[0] + 1,
        "fija_sector": True,
        "unidad": "alumnos",
        "unidad_cantidad": "saldo neto del sector privado",
        "unidad_tasa": "% de la matrícula en el sector privado",
        "descripcion": (
            "Cantidad: alumnos que gana (positivo) o pierde (negativo) el sector privado en los "
            "pases de año; aproxima el desplazamiento desde el estatal. Tasa: participación del "
            "privado en la matrícula inicial."
        ),
        "formula_texto": "Saldo = inscriptos − esperados en el privado. Tasa = matrícula privada / "
        "matrícula total × 100.",
        "alertas": ["saldo_privado", "inicial"],
    },
}


def _celdas(largo: pd.DataFrame, por_provincia: bool) -> pd.DataFrame:
    geo = ["provincia"] if por_provincia else []
    t = resumir(
        largo,
        por=[*geo, "nivel", "sector", "ambito", "sexo"],
        nivel=NIVELES,
        sexo=["mujeres", "varones"],
        indicadores=CONTEOS,
        tasas=False,
    )
    if not por_provincia:
        t.insert(1, "provincia", TOTAL_PAIS)
    return t


def _celdas_continuidad(largo: pd.DataFrame) -> pd.DataFrame:
    claves = ["provincia", "nivel", "sector", "ambito", "sexo", "ciclo"]
    c = continuidad(largo)
    por_prov = c.groupby(claves, as_index=False)[CONTEOS_CONTINUIDAD].sum()
    pais = c.groupby(claves[1:], as_index=False)[CONTEOS_CONTINUIDAD].sum()
    pais.insert(0, "provincia", TOTAL_PAIS)
    return pd.concat([por_prov, pais], ignore_index=True)


def _alertas(provincias: list[str]) -> dict:
    """Clave "provincia|nivel|indicador" → {ciclo: texto}. nivel "ambos" = primaria + secundaria."""
    salida = {}
    for prov in provincias:
        for nivel in [*NIVELES, "ambos"]:
            for clave, meta in INDICADORES.items():
                por_ciclo = {}
                for ciclo in CICLOS:
                    textos = {
                        alerta_para(
                            ciclo,
                            nombre,
                            None if prov == TOTAL_PAIS else prov,
                            None if nivel == "ambos" else nivel,
                        )
                        for nombre in meta["alertas"]
                    } - {""}
                    if textos:
                        por_ciclo[ciclo] = " · ".join(sorted(textos))
                if por_ciclo:
                    salida[f"{prov}|{nivel}|{clave}"] = por_ciclo
    return salida


def datos_visor(largo: pd.DataFrame | None = None) -> dict:
    """Estructura que consume el visor. Conteos enteros por ciclo; 0 cuando no hay alumnos."""
    largo = cargar_largo() if largo is None else largo
    claves = ["provincia", "nivel", "sector", "ambito", "sexo", "ciclo"]
    t = pd.concat([_celdas(largo, True), _celdas(largo, False)], ignore_index=True)
    for col in claves[:-1]:
        t[col] = t[col].astype(str)
    t = t.set_index(claves)[CONTEOS].join(_celdas_continuidad(largo).set_index(claves), how="outer")
    conteos = CONTEOS + CONTEOS_CONTINUIDAD
    t = t[conteos].unstack("ciclo").reindex(columns=CICLOS, level="ciclo").fillna(0).astype(int)

    celdas = {}
    for (prov, nivel, sector, ambito, sexo), fila in t.iterrows():
        destino = celdas.setdefault(prov, {}).setdefault(nivel, {})
        destino[f"{sector}|{ambito}|{sexo}"] = {c: fila[c].tolist() for c in conteos}

    provincias = sorted(p for p in celdas if p != TOTAL_PAIS)
    return {
        "ciclos": CICLOS,
        "provincias": provincias,
        "total_pais": TOTAL_PAIS,
        "valores": {
            "sector": ["Estatal", "Privado"],
            "ambito": ["Urbano", "Rural"],
            "sexo": ["mujeres", "varones"],
        },
        "indicadores": {
            k: {
                **{c: v for c, v in m.items() if c != "alertas"},
                "formula": m.get("formula") or _formula(m["tasa"]),
            }
            for k, m in INDICADORES.items()
        },
        "celdas": celdas,
        "alertas": _alertas([TOTAL_PAIS, *provincias]),
    }


def _formula(tasa: str | None) -> dict | None:
    if tasa is None:
        return None
    numerador, denominadores = TASAS[tasa]
    return {"numerador": numerador, "denominadores": denominadores}


def _tramos(ciclos: list[int]) -> str:
    """[2011, 2012, 2015] → "2011–2012, 2015"."""
    tramos, inicio = [], ciclos[0]
    for previo, actual in zip(ciclos, [*ciclos[1:], None], strict=True):
        if actual is None or actual != previo + 1:
            tramos.append(str(inicio) if inicio == previo else f"{inicio}–{previo}")
            inicio = actual
    return ", ".join(tramos)


def _tramos_html(ciclos: list[int]) -> str:
    """Cada tramo sin cortes internos; el salto de línea solo va entre tramos."""
    return ", ".join(f"<span class='sin-corte'>{t}</span>" for t in _tramos(ciclos).split(", "))


def _lista_alertas_html() -> str:
    """Filas del cuadro de avisos de calidad, ordenadas por ciclo."""
    filas = []
    for a in sorted(ALERTAS, key=lambda a: (a["ciclos"][0], a["ciclos"][-1])):
        donde = "Todas" if a["provincias"] is None else ", ".join(a["provincias"])
        nivel = a.get("nivel") or "Ambos"
        filas.append(
            f"<tr><td>{_tramos_html(a['ciclos'])}</td><td>{html.escape(nivel.capitalize())}</td>"
            f"<td>{html.escape(donde)}</td><td>{html.escape(a['texto'])}</td></tr>"
        )
    return "\n".join(filas)


def _lista_indicadores_html() -> str:
    filas = []
    for m in INDICADORES.values():
        tasa = f" {m['formula_texto']}" if m["formula_texto"] else ""
        filas.append(
            f"<li><strong>{m['etiqueta']}</strong>: {html.escape(m['descripcion'])}"
            f"<span class='tenue'>{html.escape(tasa)}</span></li>"
        )
    return "\n".join(filas)


def construir_sitio(largo: pd.DataFrame | None = None) -> Path:
    """Escribe outputs/visor/: index.html, mapa.html, datos.js, geo.js, estilos, script y plotly."""
    DIR_VISOR.mkdir(parents=True, exist_ok=True)
    datos = datos_visor(largo)
    geo = cargar_provincias_svg()
    faltan = set(datos["provincias"]) - {p["nombre"] for p in geo["provincias"]}
    if faltan:
        raise ValueError(f"Provincias sin geometría en el mapa: {sorted(faltan)}")

    (DIR_VISOR / "datos.js").write_text(
        "window.DATOS = " + json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + ";"
    )
    (DIR_VISOR / "geo.js").write_text(
        "window.GEO = " + json.dumps(geo, ensure_ascii=False, separators=(",", ":")) + ";"
    )
    for archivo in ["visor.css", "visor.js", "mapa.html"]:
        shutil.copy(DIR_PLANTILLAS / archivo, DIR_VISOR / archivo)
    plotly_js = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    shutil.copy(plotly_js, DIR_VISOR / "plotly.min.js")

    indice = (DIR_PLANTILLAS / "index.html").read_text()
    indice = (
        indice.replace("{{CICLO_INICIO}}", str(CICLOS[0]))
        .replace("{{CICLO_FIN}}", str(CICLOS[-1]))
        .replace("{{INDICADORES}}", _lista_indicadores_html())
        .replace("{{ALERTAS}}", _lista_alertas_html())
    )
    (DIR_VISOR / "index.html").write_text(indice)
    return DIR_VISOR


if __name__ == "__main__":
    destino = construir_sitio(construir_largo())
    peso = sum(f.stat().st_size for f in destino.iterdir()) / 1024 / 1024
    print(f"Visor en {destino} ({peso:.1f} MB). Abrir {destino / 'index.html'}")
