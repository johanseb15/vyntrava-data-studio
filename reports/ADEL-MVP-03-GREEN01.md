# ADEL-MVP-03-GREEN01 — Piloto B CSV, análisis GREEN

**Fecha:** 2026-10-28
**Alcance:** habilitar `suma_producto` y `conteo` sobre tablas CSV del motor de recetas; publicar agregados solo cuando no haya incidencias bloqueantes.

## Evidencia RED → GREEN

- RED: `.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp/green01_red tests/test_sprint03_red.py` → 1 fallo esperado: `DeliveryError("unsupported_capability")` ante `analisis`.
- GREEN: `.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp/green01_final` → 146 passed, 2 skipped.
- `git diff --check` → sin errores.

El oráculo sintético del Piloto B produjo 4 filas incluidas, 1 excluida, 8 unidades, total 42.50 y grupos de fecha 27.50, 10.00 y 5.00. Una prueba adicional comprueba exclusiones por columna, `conteo` independiente de la validación de cantidad y precisión decimal superior a dos cifras.

## Límite de este GREEN

El test RED existente usa receta `1.0.0`, por lo que este paso habilita análisis CSV en esa versión. La propuesta de diseño `ADEL-S03-001.md` prevé añadir el resumen de análisis en `1.1.0`; esa discrepancia debe resolverse antes de fijar el contrato final de Sprint 03. Lectura `.xlsx`, `grafico_png`, documentación operativa y aceptación formal siguen fuera de este paso. Los dos tests omitidos son los de symlinks condicionados por el entorno.
