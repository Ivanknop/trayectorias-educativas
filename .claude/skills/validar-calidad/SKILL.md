---
name: validar-calidad
description: Controles de pertinencia de datos educativos y registro de alertas. Usar después
  de construir o actualizar una base procesada, antes de reportar resultados, y cuando el
  usuario pregunte si los datos están bien.
---

# Validar la calidad de los datos

## Controles (`edu_data.validacion_base`, `edu_data.perfil`)
1. **Estructurales** por período: filas, claves vacías o duplicadas, columnas ausentes,
   identidades (`verificar_identidades`).
2. **Saltos interanuales** por unidad y corte: `saltos_interanuales(t, valor, grupo, periodo,
   umbral)`. Umbrales orientativos: stocks (matrícula) ±10 %, flujos (egresos) ±20 %.
3. **Atípicos de la propia serie**: `atipicos_robustos(t, valor, grupo, z=3)` (mediana y MAD por
   grupo). Atrapa oscilaciones de carga y cambios de régimen.
4. **Coherencia entre indicadores relacionados**: `coherencia(t, a, b, grupo, umbral_pct)`, p. ej.
   egresados vs. promovidos del último año, o matrícula t+1 vs. promovidos t.
5. **Patrones de carga**: series que alternan pérdida y ganancia grandes (p. ej. +20 % / −16 %)
   suelen ser problemas de carga, no dinámica real.

## Revisión
- Para cada señal, mirar el detalle: ¿shock real (pandemia, cambio normativo) o problema de carga?
- Distinguir lo que **afecta el total** (unidades grandes o todas a la vez) de lo local.
- No corregir sin pedido. Si se corrige, conservar el original (`<indicador>_informado`) y
  documentarlo.

## Registro de alertas
Cada alerta revisada se agrega a una lista `ALERTAS` en un único módulo del proyecto
(p. ej. `src/edu_data/alertas.py`):

```python
from edu_data.validacion_base import Alerta

ALERTAS = [
    Alerta(
        periodos=[2021],
        unidades=["X"],
        indicadores=["matricula"],
        texto="Cae 15 % y rebota 27 % al año siguiente: probable problema de carga",
    ),
]
```

- `texto`: una línea en lenguaje llano y con números.
- `unidades=None` aplica a todas; `afecta_total=True` la muestra también en el total.
- `filtros={"sector": "privado"}` restringe a un corte.
- Las visualizaciones consultan `alerta_para(ALERTAS, periodo, indicador, unidades, **filtros)` y
  marcan el punto.

## Reporte
- En la respuesta al usuario: alertas nuevas con datos concretos, ordenadas por impacto.
- Guardar cada control en `outputs/validacion_<control>.csv`.
