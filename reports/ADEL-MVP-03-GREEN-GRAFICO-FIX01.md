# ADEL-MVP-03-GREEN-GRAFICO-FIX01 — gráfico PNG

**Fecha:** 2026-10-28. **Alcance:** producir y publicar el gráfico de importes agrupados de `suma_producto`.

## RED → GREEN

- RED: `.\.venv\Scripts\python.exe -m pytest tests/test_charts.py -q --basetemp=.pytest_tmp/grafico_fix01_red --tb=short` → 1 fallo esperado: `unsupported_capability`.
- GREEN: `.\.venv\Scripts\python.exe -m pytest tests/test_charts.py tests/test_recipes.py -q --basetemp=.pytest_tmp/grafico_fix01_green_final --tb=short` → 25 aprobadas.
- Regresión final: `.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp/grafico_fix01_final --tb=short` → **157 aprobadas, 2 omitidas**. Las omisiones corresponden a los controles de symlink condicionados por el entorno.
- `git diff --check` → sin errores de formato.

El gráfico usa el orden de grupos del análisis, lienzo RGB fijo de 900 × 500, barras verdes, etiquetas de fecha, importes y eje «Importe». Se genera sin metadatos variables. La prueba comprueba firma PNG, dimensiones, píxeles de las tres barras, repetición idéntica, hash del manifiesto y conservación del original. La receta rechaza rutas de gráfico que no terminan en `.png` antes de leer entradas.

Pillow 13.0.0 se declaró como dependencia directa y se añadió al paquete local del lock, donde ya figuraba como dependencia de Matplotlib. Se eligió Pillow porque en este entorno Matplotlib no puede importarse: Python recibe `PermissionError` al abrir `.venv/Lib/site-packages/six.py`. El intento de regenerar el lock sin red falló porque la caché accesible no contiene los paquetes del proyecto; se actualizaron las dos entradas locales del lock para la dependencia directa existente.

Este paso cubre el gráfico sintético y su publicación con el flujo actual. El oráculo completo del Piloto B en CSV y XLSX, la guía operativa, la revisión independiente y la aceptación formal siguen pendientes.
