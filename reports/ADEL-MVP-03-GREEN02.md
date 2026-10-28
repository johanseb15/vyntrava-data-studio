# ADEL-MVP-03-GREEN02 — entrada XLSX y receta 1.1

**Fecha:** 2026-10-28
**Alcance:** aceptar una hoja visible `.xlsx` en recetas `1.1.0`, convertirla a la tabla textual compartida y ejecutar el flujo existente de validación y análisis.

## Cambios

- El contrato de receta admite `{id, ruta, formato: "xlsx", hoja}` solo en la menor `1.1`; CSV conserva su contrato `1.0`.
- El lector comprueba archivo regular y tamaño, estructura ZIP y límites declarados, hoja visible, encabezados, filas, celdas, fórmulas, errores, enlaces, fechas, macros, celdas combinadas y filas o columnas ocultas.
- El motor conserva el hash del original antes y después de la lectura y antes de publicar. El manifiesto `1.1` registra formato y hoja para XLSX; el manifiesto `1.0` conserva su forma previa.
- Los tests cubren lectura, rechazo de características ambiguas, versión de receta y ejecución de un análisis sintético desde XLSX.

## Evidencia

- `.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp/green02` → **154 passed, 2 skipped**.
- `git diff --check` → sin errores; Git solo informó conversión futura de finales de línea LF a CRLF.
- El test de extremo a extremo produjo `27.50`, registró la hoja `Ventas` y comprobó que el original conservó sus bytes.

## Límites del paso

El gráfico PNG, el oráculo completo del Piloto B en XLSX, documentación operativa y aceptación formal permanecen pendientes. Los dos tests omitidos son controles de symlink condicionados por el entorno. El diseño `ADEL-S03-001.md` figura como propuesta pendiente de aprobación; este paso no acredita el cierre del Sprint 03.
