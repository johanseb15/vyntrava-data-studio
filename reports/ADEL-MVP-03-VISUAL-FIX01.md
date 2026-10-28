# ADEL-MVP-03-VISUAL-FIX01 — presentación PNG y operación S03

**Fecha:** 2026-10-28. **Base declarada:** `cebfec4`, con trabajo local previo sin commit. **Alcance de este cambio:** `charts.py`, `tests/test_charts.py`, `docs/OPERACION_S03.md` y este informe. No se modificaron contratos de análisis, Excel, HMAC, recetas ni dependencias en esta intervención.

## Diagnóstico y cambio

El gráfico dibujaba `Importe` en `x=12` y alineaba las marcas monetarias respecto a un eje fijo en `x=90`. El ancho de las marcas no participaba en el cálculo del margen, por lo que el texto podía superponerse. Se midieron las cajas reales con `ImageDraw.textbbox` y se desplazó el eje según el ancho máximo de las marcas y del rótulo, con separación explícita. Se añadió `Ventas por fecha` y espacio superior. Se conservaron lienzo RGB de 900 × 500, barras verdes, colores de texto y cuadrícula, formato decimal de las marcas, orden de grupos y PNG sin metadatos variables. El análisis que produce los importes no se alteró.

La prueba de disposición registra las cajas de todos los textos dibujados, exige que estén dentro de 900 × 500 y comprueba que no se crucen entre sí. Usa tres fechas y un importe de siete cifras para ejercer el margen variable. La prueba previa de píxeles fijos de barras se sustituyó por una comprobación de presencia de barras verdes independiente de su posición; permanecen las pruebas de dimensiones, metadatos, bytes repetibles, hash del manifiesto y preservación del CSV original.

## RED → GREEN → REFACTOR

- **RED:** `tests/test_charts.py` con la prueba de cajas; `.\.venv\Scripts\python.exe -m pytest tests/test_charts.py -q --basetemp=.pytest_tmp/visual_fix_red --tb=short` → 1 fallo esperado por ausencia de `Ventas por fecha`, 2 aprobadas.
- **GREEN:** cálculo de margen por texto y título en `charts.py`; `.\.venv\Scripts\python.exe -m pytest tests/test_charts.py -q --basetemp=.pytest_tmp/visual_fix_green --tb=short` → 3 aprobadas.
- **REFACTOR y regresión:** se mantuvo el dibujo en una única función y se reutilizó la lista de marcas para medir y pintar. `.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp/visual_fix_full --tb=short` → **167 aprobadas, 2 omitidas**, sin fallos. El caso adicional explica el aumento respecto de las 166 aprobadas informadas en aceptación.
- `git diff --check` → código de salida 0, sin errores de espacios; Git mostró avisos de conversión futura LF/CRLF en archivos locales previos. Los archivos de esta intervención aún no están rastreados, por lo que no forman parte de esa comprobación de Git.

## Guía y límites

`docs/OPERACION_S03.md` se redactó desde `run_recipe`, `load_recipe`, el importador XLSX y las pruebas sintéticas. Documenta entradas, versiones, hojas, reglas, análisis, HMAC, estados, hashes y revisión manual; remite a `OPERACION_XLSX_V1.md` para la política detallada de precisión. No atribuye a `verify_delivery` la verificación integral de paquetes S03, pues esa función corresponde al diagnóstico S01.

La disposición automatizada cubre el piloto y un importe amplio representativo; una cantidad arbitraria de grupos o rótulos excepcionalmente largos puede exceder la capacidad física del lienzo fijo. Queda pendiente la **inspección visual independiente** del PNG y del paquete sintético. Este informe no declara terminado Sprint 03 ni constituye aceptación formal. No se realizó commit, push ni publicación.
