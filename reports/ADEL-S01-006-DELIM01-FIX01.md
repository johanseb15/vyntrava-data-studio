# ADEL-S01-006-DELIM01-FIX01 — confirmación de ambigüedad CSV

**Fecha:** 2026-10-27. **Alcance:** política de delimitadores de SPEC.md §5, sobre el árbol de trabajo existente. Los cambios previos en `delivery.py`, `importer.py` y sus tests se conservaron.

**Causa:** `read_csv` solo señalaba la interpretación alternativa cuando el delimitador seleccionado producía una columna. Si ambos separadores producían tablas rectangulares de varias columnas, aceptaba el declarado sin presentar la duda exigida por SPEC.md §5.

**RED:** se cambió el test parametrizado de coma y punto y coma para exigir `delimiter_ambiguous` antes de confirmar. `.venv/Scripts/python.exe -m pytest tests/test_importer.py -q -p no:cacheprovider --basetemp=$env:TEMP\ds_delim_red` terminó con **2 fallos esperados, 32 aprobadas**: `Failed: DID NOT RAISE CsvError` en ambos casos.

**GREEN:** el importador valida primero la lectura seleccionada y señala una segunda lectura plausible. Devuelve `delimiter_mismatch` si la seleccionada tiene una sola columna, o `delimiter_ambiguous` si ambas tienen varias. Una confirmación explícita del mismo delimitador permite continuar; `run_diagnostic` transmite esa confirmación por entrada y conserva el delimitador efectivo en el manifiesto. Una prueba de integración comprueba que no se publican salidas antes de confirmar y que el resumen confirmado conserva cuatro columnas.

**Verificación:** suite focalizada de importador y corte vertical: **74 aprobadas**. Suite completa con `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=$env:TEMP\ds_delim_full -rs`: **132 aprobadas, 2 omitidas** (`tests/test_workspace.py:149,162`, symlinks no disponibles). La confirmación explícita supone una revisión humana del CSV; el motor no prueba cuál interpretación es semánticamente correcta y no detecta todos los delimitadores incorrectos.

**Estado:** corrección técnica registrada. La revisión independiente y aceptación de PLAN.md §01.6 siguen pendientes; Sprint 01 no se acredita con este informe.
