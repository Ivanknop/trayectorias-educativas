"""Cartografía de provincias (IGN) preparada como trazos SVG livianos para el visor."""

import json
import sys
import unicodedata
from datetime import date
from pathlib import Path

import geopandas as gpd
import pyogrio
import requests
from shapely.geometry import box

from edu_data.trayectoria import ARCHIVOS, RAIZ, leer_trayectoria

DIR_GEO_RAW = RAIZ / "data" / "raw" / "geo"
RUTA_GEO_RAW = DIR_GEO_RAW / "provincias_ign.geojson"
# Versionado en el repo (82 KB): el GeoJSON del IGN pesa 111 MB y supera el límite de GitHub.
RUTA_GEO_SVG = Path(__file__).parent / "recursos" / "provincias_svg.json"

URL_IGN = (
    "https://wms.ign.gob.ar/geoserver/ign/ows?service=WFS&version=1.0.0&request=GetFeature"
    "&typeName=ign:provincia&outputFormat=application/json"
)

EQUIVALENCIAS = {
    "ciudad autonoma de buenos aires": "Ciudad de Buenos Aires",
    "tierra del fuego, antartida e islas del atlantico sur": "Tierra del Fuego",
}

# Recorte continental + Malvinas: deja afuera el sector antártico e islas lejanas, solo por escala.
RECORTE_LONLAT = box(-74.0, -56.0, -53.0, -21.5)
PROYECCION = "+proj=aea +lat_1=-28 +lat_2=-48 +lat_0=-38 +lon_0=-64 +datum=WGS84 +units=m"
ANCHO_SVG = 420
TOLERANCIA_M = 2500
TOLERANCIA_CABA_M = 30


def descargar_provincias() -> None:
    """Descarga la capa de provincias del IGN a data/raw/geo (solo si no existe)."""
    if RUTA_GEO_RAW.exists():
        print(f"Ya existe {RUTA_GEO_RAW}; no se vuelve a descargar.")
        return
    DIR_GEO_RAW.mkdir(parents=True, exist_ok=True)
    respuesta = requests.get(URL_IGN, timeout=180)
    respuesta.raise_for_status()
    RUTA_GEO_RAW.write_bytes(respuesta.content)
    (DIR_GEO_RAW / "FUENTE.txt").write_text(f"{URL_IGN}\nDescargado: {date.today().isoformat()}\n")
    print(f"Descargado {RUTA_GEO_RAW} ({len(respuesta.content):,} bytes)")


def _clave(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def _nombre_ra(nombre_ign: str, nombres_ra: set[str]) -> str:
    clave = _clave(nombre_ign)
    if clave in EQUIVALENCIAS:
        return EQUIVALENCIAS[clave]
    por_clave = {_clave(n): n for n in nombres_ra}
    if clave not in por_clave:
        raise ValueError(f"Provincia del IGN sin equivalente en el RA: {nombre_ign!r}")
    return por_clave[clave]


def _columna_nombre(gdf: gpd.GeoDataFrame) -> str:
    for col in ["nam", "nombre", "fna", "NAM", "NOMBRE"]:
        if col in gdf.columns:
            return col
    raise ValueError(f"No encuentro la columna de nombre en la capa del IGN: {list(gdf.columns)}")


def _a_trazo(geom, escala: float, x0: float, y1: float) -> str:
    poligonos = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    partes = []
    for pol in poligonos:
        for anillo in [pol.exterior, *pol.interiors]:
            puntos = [f"{(x - x0) * escala:.1f},{(y1 - y) * escala:.1f}" for x, y in anillo.coords]
            partes.append("M" + "L".join(puntos) + "Z")
    return "".join(partes)


def preparar_provincias() -> dict:
    """Normaliza nombres, recorta, simplifica y proyecta. Falla si falta alguna provincia del RA."""
    if not RUTA_GEO_RAW.exists():
        raise FileNotFoundError(
            f"Falta {RUTA_GEO_RAW}. Correr: uv run python -m edu_data.geo descargar"
        )
    # La capa del IGN trae geometrías más grandes que el límite por defecto de GDAL para GeoJSON.
    pyogrio.set_gdal_config_options({"OGR_GEOJSON_MAX_OBJ_SIZE": "0"})
    gdf = gpd.read_file(RUTA_GEO_RAW)
    gdf = gdf.set_crs(4326) if gdf.crs is None else gdf.to_crs(4326)
    nombres_ra = set(leer_trayectoria(ARCHIVOS[-1]).provincia.unique()) - {"Sin dato"}
    gdf["provincia"] = [_nombre_ra(n, nombres_ra) for n in gdf[_columna_nombre(gdf)]]
    gdf = gdf.dissolve("provincia").reset_index()
    faltan = nombres_ra - set(gdf.provincia)
    if faltan:
        raise ValueError(f"Provincias del RA sin geometría: {sorted(faltan)}")

    gdf["geometry"] = gdf.geometry.intersection(RECORTE_LONLAT)
    gdf = gdf.to_crs(PROYECCION)
    caba = gdf[gdf.provincia == "Ciudad de Buenos Aires"].geometry.iloc[0]
    gdf["geometry"] = gdf.geometry.simplify(TOLERANCIA_M, preserve_topology=True)

    x0, y0, x1, y1 = gdf.total_bounds
    escala = ANCHO_SVG / (x1 - x0)
    alto = (y1 - y0) * escala
    provincias = [
        {"nombre": fila.provincia, "d": _a_trazo(fila.geometry, escala, x0, y1)}
        for fila in gdf.itertuples()
        if not fila.geometry.is_empty
    ]

    caba = caba.simplify(TOLERANCIA_CABA_M, preserve_topology=True)
    cx0, cy0, cx1, cy1 = caba.bounds
    lado = 90
    escala_caba = lado / max(cx1 - cx0, cy1 - cy0)
    recuadro = {
        "nombre": "Ciudad de Buenos Aires",
        "d": _a_trazo(caba, escala_caba, cx0, cy1),
        "viewBox": f"-4 -4 {(cx1 - cx0) * escala_caba + 8:.0f} {(cy1 - cy0) * escala_caba + 8:.0f}",
    }
    salida = {
        "fuente": "IGN, capa ign:provincia (WFS)",
        "viewBox": f"0 0 {ANCHO_SVG} {alto:.0f}",
        "provincias": provincias,
        "recuadro_caba": recuadro,
    }
    RUTA_GEO_SVG.parent.mkdir(parents=True, exist_ok=True)
    RUTA_GEO_SVG.write_text(json.dumps(salida, ensure_ascii=False))
    return salida


def cargar_provincias_svg() -> dict:
    if not RUTA_GEO_SVG.exists():
        return preparar_provincias()
    return json.loads(RUTA_GEO_SVG.read_text())


if __name__ == "__main__":
    if "descargar" in sys.argv[1:]:
        descargar_provincias()
    geo = preparar_provincias()
    peso = RUTA_GEO_SVG.stat().st_size
    print(f"{len(geo['provincias'])} provincias → {RUTA_GEO_SVG} ({peso / 1024:.0f} KB)")
