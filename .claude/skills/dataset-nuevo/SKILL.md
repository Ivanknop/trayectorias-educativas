---
name: dataset-nuevo
description: Procedimiento para incorporar un dataset educativo nuevo (CSV o Excel oficiales).
  Usar cuando aparece un archivo nuevo en data/raw/ o el usuario pide revisar, describir o
  perfilar un dataset.
---

# Incorporar un dataset nuevo

Objetivo: entender el dataset y dejarlo documentado y leíble de forma reproducible.
Todavía no se analiza ni se grafica.

## 1. Inventario
- Listar `data/raw/` con tamaño y fecha. Agrupar por serie (mismo nombre, distinto período).
- Por archivo: `file <archivo>` y `edu_data.io.detectar_formato(ruta)` (encoding, separador,
  CRLF, encabezado). No asumir UTF-8.
- Excel: `edu_data.io.listar_hojas(ruta)` y revisar cada hoja (los diccionarios oficiales
  suelen traer una pestaña por base). Leer con `leer_hoja(ruta, hoja)`.

## 2. Esquema entre períodos
- `edu_data.io.diff_columnas({periodo: df, ...})`: columnas que aparecen, desaparecen o cambian
  de mayúsculas.
- Detectar patrones de nombre (prefijos de sexo, sufijos de grado o año, bloques). Escribirlos
  como constantes o regex, no como listas a mano.
- `edu_data.io.unificar_esquema(dfs)`: ausentes → NA, registradas en `attrs`.

## 3. Lectura reproducible
- Escribir el lector en `src/edu_data/<base>.py` usando `edu_data.io.leer_csv_oficial`
  (`claves=` para las claves sin ceros a la izquierda; `decimal=","` si corresponde).
- Revisar `df.attrs["columnas_texto_por_ceros"]`: confirmar que son códigos y no números.
- Buscar errores de encoding de origen en los textos (caracteres raros repetidos) y corregirlos
  en el lector, con un comentario.

## 4. Vacíos y ceros
- `edu_data.perfil.perfil_columnas(df)`: vacíos y ceros por columna.
- Decidir con evidencia si vacío = "no aplica / sin oferta" o "dato perdido". Señal típica: una
  columna con vacíos y sin ningún cero → el vacío marca ausencia de oferta.
- Documentar la decisión. Vacío ≠ 0 en todo el pipeline.

## 5. Unidad de análisis y claves
- ¿Fila = estudiante, escuela, sección, agregado? Verificar la unicidad de la clave.
- Revisar los valores de las dimensiones: categorías enmascaradas, "sin datos", totales mezclados
  con detalle.
- ¿Ponderadores, valores plausibles o pesos replicados? Aplicar las reglas de CLAUDE.md.

## 6. Identidades contables
- Buscar relaciones que deberían cerrar: total = suma de partes, flujos (inicial + entradas −
  salidas = final), subconjunto ≤ total.
- `edu_data.perfil.verificar_identidades(df, reglas)` en todos los períodos. Informar
  `attrs["resumen"]`: las filas `no_evaluable` (con NA) se reportan aparte de las que fallan.
- Si cierran, decirlo: da confianza. Si no, listar las filas que fallan.

## 7. Período de referencia
- ¿El año del archivo es el período que informa? Buscar un shock conocido (p. ej. pandemia 2020:
  suelen caer repitencia, abandono y movilidad) y ver en qué archivo aparece.
- Si hay desfase, codificarlo como constante (`DESFASE_...`) con la evidencia en un comentario.

## 8. Diccionario
- Cruzar cada variable con el diccionario oficial. Listar las que no tienen definición.
- Pedir al usuario lo que falte en la **primera** respuesta, no al final.

## 9. Documentación
- `data/README.md`: fuente, URL, fecha de descarga, período que informa, unidad, encoding,
  ponderador, notas.
- `data/diccionario_<base>.md` a partir de `data/_plantilla_diccionario.md`.

## 10. Entrega
- Resumen corto: qué es, unidad, períodos, calidad (identidades, vacíos), preguntas abiertas.
- No generar gráficos en este paso. Seguir con la skill `validar-calidad` si se va a analizar.
