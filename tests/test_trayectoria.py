import pytest

from edu_data.trayectoria import (
    ARCHIVOS,
    CICLOS,
    archivo_de,
    ciclo_de,
    columnas_estandar,
    leer_trayectoria,
    verificar_identidades,
)


def test_ciclos_corridos_un_anio():
    assert CICLOS == list(range(2010, 2025))
    assert all(archivo_de(ciclo_de(a)) == a for a in ARCHIVOS)


@pytest.mark.parametrize("anio_archivo", ARCHIVOS)
def test_archivo_esquema_ciclo_e_identidades(anio_archivo):
    df = leer_trayectoria(anio_archivo)
    assert (df.ciclo == anio_archivo - 1).all()
    assert list(df.columns[2:]) == columnas_estandar()
    ident = verificar_identidades(df)
    assert ident.filas_falla_flujo.sum() == 0
    assert ident.loc[ident.anio_estudio != "20", "filas_falla_resultado"].sum() == 0
    assert ident.filas_mujeres_mayor_total.sum() == 0
