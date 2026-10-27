# ADEL-S01-006-FINAL-REV01 — revisión independiente

**Fecha:** 2026-10-27. **Rol:** revisor independiente del cierre ADEL-S01-006-FINAL. **Decisión técnica:** favorable para el alcance diagnóstico de Sprint 01, con dos pruebas de symlink sin ejecutar por restricción del sistema. **Decisión formal de sprint:** pendiente de aceptación expresa del responsable según PLAN.md §8; este informe no la sustituye.

## Material y método

Se revisaron SPEC.md §§4–8, PLAN.md §§3–4 y 01.1–01.6, código de `src/`, las cinco suites en `tests/`, la guía operativa y los informes ADEL-S01-001 a 006, incluidos FIX01/FIX02, STAB01, DELIM01-FIX01, TRACE01 y FINAL. El expediente `ADEL-QG-001` no está disponible. Esta copia del proyecto no contiene `.git`, por lo que no se pudo verificar el commit `74312886422d7e09c6c2ec8d20245958846f84dc` ni ejecutar `git diff --check`. La revisión se refiere a los archivos presentes en esta copia y no atribuye a este revisor las ejecuciones RED/GREEN/REFACTOR históricas.

Se creó `.review_venv` desde cero y se instalaron las siete dependencias de `uv.lock` con `UV_CACHE_DIR` local y `uv sync --locked --system-certs`. El intento sin red falló porque faltaba `pygments` en la caché nueva; el intento con la caché global falló por acceso denegado. El entorno nuevo informó `pytest 9.1.1`. Desde la raíz del proyecto se ejecutó:

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.review_uv_cache'
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) '.review_venv'
uv sync --locked --system-certs
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.review_venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -rs --basetemp=.\review_clean_pytest_tmp
```

**Resultado:** 132 aprobadas, 2 omitidas, 0 fallos en 5,95 s. Se repitió la suite con `.venv`: 132 aprobadas, 2 omitidas, 0 fallos en 5,11 s. En ambas, las omisiones fueron `tests/test_workspace.py:149` y `:162`: el sistema no permitió crear symlinks. Las pruebas de junction sí se ejecutaron. Por tanto, el comportamiento real ante symlinks no queda acreditado por ejecución en este equipo.

## Contraste independiente

Se recalculó el oráculo a partir de los bytes del fixture Piloto A con el lector CSV de la biblioteca estándar, sin usar `diagnose`: SHA-256 `583c2403e3425065bf3c1da265a018f9570e9cc03d28a099f4d4ec86f93c882d`; 6 filas, 4 columnas, 1 duplicado exacto, 3 vacíos literales y 1 celda solo espacios. El SHA-256 de `tests/test_vertical_slice.py` es `1A829354A31C0DF5264447974A0D900E41AD359CAD8A4FAEAB707AAE380350FB`, igual al consignado en FINAL.

La inspección de `workspace.py`, `importer.py`, `delivery.py` y las pruebas de integración confirma que la ruta cruzada se rechaza antes de abrir el original ajeno, la receta y capacidades se validan antes de leer CSV, el original se compara por bytes/hash, los fallos de CSV no publican un manifiesto válido y `verify_delivery` comprueba estructura y hashes del paquete. Las pruebas también ejercitan errores sin contenido de celdas ni rutas privadas. No se identificó un hallazgo bloqueante nuevo en el alcance de Sprint 01.

## Dictamen y pendientes

**Confirmación del revisor:** la evidencia técnica del corte presente es suficiente para el diagnóstico CSV de Sprint 01, con la reserva explícita de las dos pruebas de symlink omitidas. Quedan como límites conocidos la publicación no atómica del resumen y manifiesto, la posibilidad de cambios concurrentes de rutas, y que `completo-verificado` no recalcula el diagnóstico ni autentica al escritor. Tampoco se verificaron las fronteras exactas de 64 MiB y 64 niveles del JSON publicado. El producto sigue limitado a datos sintéticos hasta aprobar la política de datos reales de SPEC.md §7.

**Estado formal:** PLAN.md §8 exige aceptación del responsable después de la revisión. Esa aceptación no consta aquí; por ello, Sprint 01 y su 20% no se acreditan en este informe. El responsable debe registrar su decisión expresa, con conocimiento de las dos omisiones, antes de marcar el sprint como terminado.
