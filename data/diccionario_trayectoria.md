# Base Trayectoria (RA – Educación Común): descripción y diccionario

Serie disponible: **archivos 2011 a 2025 = ciclos lectivos 2010 a 2024** (15 ciclos).
Las secciones 2 a 7 describen los **archivos crudos** y por eso hablan del año del archivo. Desde la sección 8,
todo se expresa en **ciclo lectivo**. La referencia para la descripción es el archivo 2025 (ciclo 2024), el más
completo. Las diferencias entre años están en la sección 7 y los problemas de calidad en la sección 10.

## 1. Qué es

Base usuaria "1.2 Trayectoria" del Relevamiento Anual (RA) de la DiNIEE: alumnos **promovidos, no promovidos
y salidos con y sin pase** de primaria y secundaria común.

- **Es censal**, no muestral: **no hay ponderadores**. Las sumas son totales poblacionales.
- **No está a nivel escuela**: cada fila es un **agregado** de establecimientos.
- **Período de referencia: cada archivo informa el ciclo lectivo anterior** (archivo 2025 → ciclo 2024),
  egresados incluidos.
  - Evidencia: el quiebre de la pandemia (escuelas cerradas y ciclo unificado sin repitencia en 2020) aparece
    en el archivo 2021.
  - Lo confirmó el equipo.
  - El código lo resuelve con `DESFASE_CICLO = 1` y las funciones `ciclo_de`/`archivo_de`
    (`src/edu_data/trayectoria.py`).

## 2. Unidad de análisis y forma

| | Archivo 2025 (ciclo 2024) |
|---|---|
| Filas | 1.210 (clave única, sin duplicados) |
| Columnas | 316 (4 de identificación + 308 conteos por año de estudio + 4 de egresados) |
| Unidad | provincia × departamento × sector × ámbito |
| Provincias | 24 |
| Departamentos | 437 nombres (incluye `Enmascarado` y `Sin datos`) |
| Matrícula inicial total (suma) | 8.730.602 alumnos, 49,4 % mujeres |

Filas por sector y ámbito: Estatal-Rural 458 · Estatal-Urbano 445 · Privado-Urbano 267 · Privado-Rural 40.

## 3. Variables de identificación (texto)

| Variable | Descripción | Valores |
|---|---|---|
| `provincia` | Jurisdicción (nombre, sin código) | 24, ej. `Buenos Aires`, `Ciudad de Buenos Aires` |
| `departamento` | Departamento/partido/comuna (nombre en mayúsculas, sin código INDEC) | 437 |
| `sector` | Sector de gestión | `Estatal`, `Privado` |
| `ambito` | Ámbito del establecimiento | `Urbano`, `Rural` |

- `Enmascarado`: departamentos agrupados por secreto estadístico (base anonimizada). 67 filas, 1,65 % de la
  matrícula. Sirve para totales provinciales, no para análisis departamental.
- `Sin datos`: 2 filas casi vacías (Formosa y Tucumán, Estatal-Rural).
- Para unir con cartografía hará falta una tabla de equivalencias por nombre (no vienen códigos).

## 4. Variables de conteo

Nombre: `[m_]<bloque>_<año de estudio>`.

- Prefijo **`m_`** = solo **mujeres**. Sin prefijo = **total**. Varones = total − mujeres. Nunca hay m > total.
- Sufijo = **año de estudio** en numeración corrida de 1 a 12:

| Sufijo | Significado |
|---|---|
| `1` … `12` | 1° a 12° año de estudio de la escolaridad obligatoria (primaria + secundaria) |
| `1314` | 13° y 14° año juntos (secundarias técnicas/artísticas con años extra) |
| `20` | Alumnos sin año de estudio definido (probablemente plurigrado / trayectos no graduados; a confirmar) |

**Dónde termina la primaria** depende de la provincia. Es la estructura oficial del nivel primario (Ministerio
de Educación, en el marco de la LEN 26.206):

- **Primaria de 6 años (6+6)**: 7° es 1° de secundaria. Buenos Aires, Catamarca, Chubut, Córdoba, Corrientes,
  Entre Ríos, Formosa, La Pampa, San Juan, San Luis, Tierra del Fuego, Tucumán.
- **Primaria de 7 años (7+5)**: 8° es 1° de secundaria. CABA, Chaco, Jujuy, La Rioja, Mendoza, Misiones, Neuquén,
  Río Negro, Salta, Santa Cruz, Santa Fe, Santiago del Estero.

Coincide con lo que muestran los datos: la no promoción y el abandono saltan en el primer año de secundaria,
y los egresados de primaria son los promovidos del último grado. Está en `PRIMARIA_7_ANIOS`
(`src/edu_data/trayectoria.py`). Hace falta para cortar por nivel y para calcular el egreso de primaria.

### Bloques (cada uno se repite por año de estudio, total y mujeres)

| Bloque | En palabras | Uso para el objetivo |
|---|---|---|
| `inicial` | Matrícula al inicio del ciclo lectivo | Denominador base |
| `entrados` | Alumnos que se incorporaron durante el año | Movilidad |
| `scp` | **Salidos con pase**: se fueron a otra escuela con pase | Movilidad, **no** es abandono |
| `ssp` | **Salidos sin pase**: dejaron la escuela sin pedir pase | **Proxy de abandono intraanual** |
| `ultimo` | Matrícula al último día de clases | Denominador de promoción |
| `promovidos` | Promovidos al terminar las clases | Continuidad |
| `promovidos_ex` | Promovidos tras exámenes/instancias complementarias | Continuidad |
| `promovidos_mas_2mat` | Solo 2025. Promovidos con más de 2 materias pendientes (solo secundaria, casi solo Buenos Aires) | Continuidad |
| `nopromo` | **No promovidos**: deberán recursar (repitencia) | Repitencia |
| `regulares` | Sin definición en el material disponible; **no** forma parte de `ultimo` | A confirmar |
| `otros` | Sin definición en el material disponible; **no** forma parte de `ultimo` | A confirmar |

### Egresados (sin año de estudio)

| Variable | En palabras | Suma 2025 |
|---|---|---|
| `primaria_egresados` / `primaria_m_egresados` | Egresados de primaria, total / mujeres | 730.192 / 359.237 |
| `secundaria_egresados` / `secundaria_m_egresados` | Egresados de secundaria, total / mujeres | 461.612 / 246.198 |

## 5. Relaciones entre variables (se cumplen en los 15 años, en todas las filas)

```
inicial + entrados − scp − ssp = ultimo
ultimo = promovidos + promovidos_ex + promovidos_mas_2mat (2025) + nopromo
```

Excepción: sufijo `20`. En 102 filas hay flujo (`inicial`…`ultimo`) pero los resultados están vacíos.

## 6. Tipos de datos y vacíos

- Todos los conteos son **enteros ≥ 0** (no hay decimales ni negativos; máximo 20.747). Se leen como `Int64`.
- Los vacíos vienen como un espacio `' '`. Se convierten en NA.
- **Un vacío es "no hay oferta de ese año" y no un dato perdido**. Ejemplo: en `inicial_12` hay 29 vacíos y
  ningún cero. Son casi todos departamentos Estatal-Rural sin secundaria completa. Hay que tratarlos como 0
  para sumar, pero no contarlos en promedios por fila.
- 35,5 % de los valores no vacíos son 0 (sobre todo en `ssp`, `entrados`, `otros`).

% de filas vacías por bloque (2025):

| Bloques | 1°–6° | 7° | 8°–12° | 13°–14° | sin año (20) |
|---|---|---|---|---|---|
| `inicial`, `entrados`, `scp`, `ssp`, `ultimo` | ~1 % | 1 % | 1,5–2,4 % | 41 % | 91 % |
| `promovidos`, `nopromo`, `regulares`, `otros` | ~1 % | 1 % | 1,5–2,4 % | 41 % | 99,8 % |
| `promovidos_ex` | ~1 % | 27 % | 28–29 % | 59 % | 99,8 % |
| `promovidos_mas_2mat` | 100 % | 74 % | 74 % | 82 % | 100 % |
| egresados | primaria 0,8 % · secundaria 2,2 % | | | | |

Buenos Aires deja `promovidos_ex` vacío en secundaria y usa `promovidos_mas_2mat`. En el resto es al revés.
Por eso, para comparar, conviene sumar **`promovidos_ex + promovidos_mas_2mat`**.

Perfil completo por columna (tipo, válidos, vacíos, ceros, suma, máximo): `outputs/perfil_trayectoria_ciclo_2024.csv`
(`uv run python -m edu_data.trayectoria <ciclo>`).

## 7. Diferencias entre años (para la serie temporal)

| Archivo | 2011–2022 | 2023–2024 | 2025 |
|---|---|---|---|
| Ciclo lectivo | 2010–2021 | 2022–2023 | 2024 |
| Filas | 1.183–1.205 | 1.205–1.209 | 1.210 |
| Columnas | 268 | 288 | 316 |
| Sufijo `20` (sin año definido) | no existe | existe (con datos desde 2024) | sí |
| `promovidos_mas_2mat` | no | no | sí |

- El lector normaliza todos los años al mismo esquema de 316 columnas. Las columnas que no existen en el
  archivo de ese año quedan vacías (NA) y se listan en `df.attrs["columnas_ausentes"]`. El perfil por columna
  las marca con `existe_en_origen = False`. Así, todas las funciones aceptan cualquier año.
- Siempre hay 24 provincias. Los departamentos varían entre 434 y 439 nombres.

- En 2024 el encabezado es `Departamento` (el lector lo pasa a minúscula).
- Cambian unos pocos departamentos entre años (Caleu Caleu/Hucal, Tolhuin, Belgrano/Mitre/Rivadavia en
  Santiago del Estero, Berón de Astrada), además de `Enmascarado` y `Sin datos`. **Comparar por provincia es
  seguro. Comparar por departamento necesita armonizar.**
- En 2023/24, Buenos Aires carga `promovidos_ex` en secundaria. En 2025 lo deja vacío y pasa a usar
  `promovidos_mas_2mat`. Esto refuerza la idea de sumar ambos bloques.
- **Quiebre en Buenos Aires 2025**: sus no promovidos de secundaria caen a menos de la mitad (9° año: 31.457 en
  2023, 32.870 en 2024, 13.988 en 2025) y los promovidos suben. Coincide con el cambio de categorías.
  Probablemente se debe a un cambio en el régimen de promoción y no en las trayectorias. Hay que marcarlo en
  cualquier serie de repitencia, y BA pesa en el total nacional.
- Hay un error de codificación de origen (`1§ DE MAYO` en lugar de `1º DE MAYO`). El lector lo corrige.

## 8. Indicadores que se construyen

- **Abandono intraanual**: `ssp / (inicial + entrados)`.
- **Repitencia**: `nopromo / ultimo_con_resultado`.
- **Promoción efectiva**: `promovidos_efectivos / ultimo_con_resultado`.
- **Movilidad**: `scp` y `entrados`. A nivel agregado se compensan en parte (un pase sale de una fila y entra
  en otra).
- **Egresos**: egresados por nivel. En primaria se toman los promovidos del último grado (sección 9).
- **Pérdida entre años y saldo del sector privado**: con `continuidad()` (sección 9).
- Todo se puede cortar por **sexo** (total/mujeres/varones), **sector**, **ámbito**, **provincia** y
  **nivel**.

## 9. Base agregada y función de consulta (por ciclo lectivo)

`uv run python -m edu_data.agregados` genera:

- `data/processed/trayectoria_largo.parquet`: los 15 ciclos en formato largo (8 millones de filas). Hay una
  fila por ciclo × provincia × departamento × sector × ámbito × nivel × año de estudio × sexo × indicador.
- `outputs/trayectoria_provincias.csv`: tabla provincial lista. Tiene cada provincia más "Total país", por
  nivel. Cortes: total, sector, ámbito y sector × ámbito. Sexos: total, mujeres y varones.

Agregados que se calculan en la construcción:
- `varones` = total − mujeres.
- `nivel`: depende de la estructura 6+6 o 7+5 de cada provincia. 13°–14° es secundaria y el sufijo 20 es
  `sin_definir`.
- `promovidos_efectivos` = promovidos + promovidos_ex + promovidos_mas_2mat.
- **`egresados` de primaria = promovidos del último grado** (6° o 7° según la estructura oficial):
  - Desde 2013, en casi todas las provincias, coincide con lo informado (cociente 1,000).
  - Antes de 2013, lo informado está incompleto en muchas provincias.
  - Lo informado se conserva como `egresados_informados`.
  - Los egresados de secundaria son los informados, sin cambios.
- `ultimo_con_resultado` = matrícula final solo donde hay resultados cargados.

Tasas (%): son cocientes de sumas y se calculan después de agregar.

| Tasa | Fórmula |
|---|---|
| `tasa_abandono` | ssp / (inicial + entrados) |
| `tasa_salida_con_pase` | scp / (inicial + entrados) |
| `tasa_repitencia` | nopromo / ultimo_con_resultado |
| `tasa_promocion` | promovidos_efectivos / ultimo_con_resultado |

```python
from edu_data.agregados import cargar_largo, resumir

L = cargar_largo()
resumir(L)  # total país por ciclo
resumir(L, por=["provincia", "nivel"])
resumir(L, provincia="Buenos Aires", nivel="secundaria", por=["sector", "ambito", "sexo"])
resumir(L, ciclo=2024, por=["provincia", "anio_estudio"], indicadores=["ssp", "inicial"])
```

- `por`: dimensiones que quedan separadas. Opciones: `ciclo`, `provincia`, `departamento`, `sector`,
  `ambito`, `nivel`, `anio_estudio` y `sexo`. Las demás se suman, o sea que el default es el total.
- `ciclo` siempre se separa (nunca se suman ciclos entre sí).
- `sexo` vale `total` por defecto. Si se pasa en `por`, devuelve total, mujeres y varones.
- Filtros: un valor o una lista para cualquier dimensión.
- Sin filtrar `nivel`, `egresados` suma los de primaria y los de secundaria.

### Continuidad entre años: `continuidad(largo)`

Calcula el pase del año de estudio g (ciclo t) a g+1 (ciclo t+1), por provincia × sector × ámbito × sexo:

- `esperados` = promovidos de g en t + no promovidos de g+1 en t (los que recursan g+1).
- `reales` = matrícula inicial de g+1 en t+1.
- `perdida` = esperados − reales. Un valor negativo indica que llegaron más alumnos de los esperados.

Criterios:
- En 12° los no promovidos adeudan materias y no recursan, así que no se cuentan como esperados. Con ese
  criterio, la pérdida de 11° a 12° queda cerca de 0.
- Cada pase se asigna al ciclo y al nivel de destino; el paso de primaria a secundaria cuenta en secundaria.
- Quedan afuera 13°–14° y los alumnos sin año definido. Primer ciclo con datos: 2011.

**No es abandono puro.** Incluye pases a la educación de adultos y a otras modalidades, y cambios de
provincia. Por sector o por ámbito también refleja cambios de escuela (de estatal a privado, de rural a
urbano). Por eso la pérdida del sector privado es negativa cuando el privado recibe alumnos.

## 10. Calidad de datos: controles y alertas (por ciclo)

`uv run python -m edu_data.validacion` corre los controles y deja una tabla por control en
`outputs/validacion_*.csv`:

- **Estructurales**: filas, claves vacías o duplicadas, identidades contables, mujeres > total.
- **Saltos interanuales por provincia y nivel**: matrícula ±10 %, egresados ±20 %.
- **Coherencia de egresados**: egresados contra promovidos del último año del nivel.
- **Tasas atípicas**: repitencia y abandono a más de 3 desvíos robustos de la serie de la provincia.

Resultados, ciclos 2010–2024:

- **Las identidades contables se cumplen en todas las filas de los 15 ciclos.** No hay claves duplicadas ni
  casos de mujeres > total.
- **Ciclo 2020 (pandemia)**: los entrados y los salidos con pase caen a menos de la mitad. El abandono baja de
  2,0 % a 0,6 % y la repitencia secundaria de 15,1 % a 6,0 %. El ciclo 2021 se recupera a medias. Chaco,
  Chubut, Entre Ríos y Jujuy casi no caen en 2020.
- **Egresados de primaria informados, incompletos en 2010–2012** (corregido: ver sección 9):
  - Faltan Buenos Aires, CABA, La Rioja y San Juan en 2010.
  - Catamarca, Chaco, Santa Cruz y Tierra del Fuego tienen valores casi nulos.
  - San Luis y Santiago del Estero cargan alrededor de la mitad, y Buenos Aires, Jujuy y Misiones alrededor del
    85 %.
  - El total país informado de 2010 es de 314 mil; el corregido, de 702 mil.
- **Desfases persistentes entre egresados informados y promovidos de 7°**:
  - Salta: entre 12 % y 21 % menos desde 2018.
  - Santiago del Estero: alrededor de 6 % menos hasta 2020.
  - La Rioja: alrededor de 3 % menos.
  - Mendoza: entre 10 % y 25 % menos hasta 2015.
  - Con la corrección se usan los promovidos. Si la diferencia fuera real (por ejemplo, alumnos que pasan de
    7° a otra modalidad sin recibir certificado), el egreso de esas provincias queda sobreestimado.
- **Egresados de secundaria, ciclo 2010, bajos**: el total país sube 16 % en 2011, mientras el resto de los
  ciclos crece entre 3 % y 6 %.
- **Catamarca, ciclo 2011, secundaria**: la matrícula cae 15 % y rebota 27 % en 2012. Probable falta de
  cobertura.
- **Santa Cruz, secundaria, ciclos 2019–2023**: la repitencia cae de ~29 % a 4–11 % y vuelve a 27 % en 2024.
- **Buenos Aires, ciclo 2024**: cambio de régimen de promoción en secundaria (aparece `promovidos_mas_2mat` y
  la repitencia cae a la mitad). Pesa en el total país.
- **Entre Ríos, primaria, ciclos 2020–2021**: el abandono se cuadruplica y vuelve al nivel previo.
- **Ciclo 2020**: una fila (Buenos Aires, Enmascarado, Privado) viene sin ámbito, con 7 alumnos. Se
  recodifica como `Sin dato`.
- **No son errores, pero hay que tenerlos en cuenta**:
  - La repitencia de 1° grado baja de 8 % (ciclo 2010) a menos de 1 %, por la unidad pedagógica 1°–2°.
  - La proporción de mujeres baja de 50,0 % a 49,4 %.

Las alertas revisadas están en `ALERTAS` (`src/edu_data/validacion.py`), expresadas en ciclos. El visor las
marca solo. Si aparece un problema nuevo, se agrega ahí.

## 11. Visor (gráficos on demand)

`uv run python -m edu_data.visor` construye `outputs/visor/`. Se abre `index.html` con doble clic; funciona
sin servidor y sin internet, porque plotly.js va incluido.

- **`index.html`**: guía. Explica qué datos hay, los indicadores, los cortes y los avisos de calidad, y lleva
  al mapa.
- **`mapa.html`**: mapa de provincias (más el recuadro de CABA y el botón "Total país"). Al tocar una
  provincia se abre su panel:
  - Indicador: Repitencia, Abandono, Promoción, Matrícula o Egreso.
  - Medida: Cantidad o Tasa. Matrícula y Egreso solo como cantidad.
  - Nivel: Primaria, Secundaria o Ambos.
  - Sexo, Ámbito y Sector: Total o Desagregar. Se combinan hasta 8 líneas.
  - Gráfico de líneas: X = ciclo, Y = valor. Banda gris en la pandemia (2020) y cruz en los datos con
    alerta.
  - Tabla de valores debajo.
- **Colores**: siguen a sector × ámbito, con un orden fijo validado. Varones van con línea discontinua.
- **Indicadores agregados después:**
  - **Pérdida entre años**: cantidad = esperados − inscriptos; tasa = sobre los esperados. Se ubica en el
    ciclo de destino.
  - **Estatal → privado**: la cantidad es el saldo neto del privado en los pases de año (positivo: gana
    alumnos); la tasa es la participación privada en la matrícula. El botón Sector queda deshabilitado.
- **Enlaces**: el estado queda en la URL. Por ejemplo,
  `mapa.html#prov=Salta&ind=repitencia&medida=tasa&nivel=secundaria&sexo=desagregar`.
- **Datos**: `datos_visor()` exporta el grano provincia × nivel × sector × ámbito × sexo × ciclo. El navegador
  suma y calcula las tasas después de sumar.
- **Cartografía**: IGN (`uv run python -m edu_data.geo descargar`), recortada al continente más Malvinas y
  simplificada (`src/edu_data/recursos/provincias_svg.json`, versionado).

## Pendientes / a confirmar

1. Pestaña del diccionario de la base Trayectoria: definiciones de `regulares`, `otros`, `promovidos_ex` y del
   sufijo `20`.
2. Fecha de descarga de cada archivo.
3. Salta: los egresados informados de primaria son entre 12 % y 21 % menos que los promovidos de 7° (sección 10).
