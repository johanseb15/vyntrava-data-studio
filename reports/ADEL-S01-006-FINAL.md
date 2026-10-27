# ADEL-S01-006-FINAL — cierre integral de Sprint 01

**Fecha:** 2026-10-27. **Corte revisado:** `74312886422d7e09c6c2ec8d20245958846f84dc` más los cambios presentes en el árbol de trabajo. **Decisión:** **NO GO para acreditar el cierre de Sprint 01 y su 20%**. La implementación supera la verificación técnica disponible, pero PLAN.md §01.6 exige la ejecución y confirmación de un revisor distinto del implementador, además de la aceptación del responsable. Ninguna de esas dos decisiones consta en este corte. Este informe no las suplanta.

## Alcance y trazabilidad

Se contrastaron SPEC.md §§4–8, PLAN.md §§3–4 y 01.1–01.6, el código y las pruebas actuales, la guía [OPERACION_CSV_V1](../docs/OPERACION_CSV_V1.md) y los informes ADEL-S01-001 a 005, FIX01/FIX02, [STAB01](ADEL-S01-006-STAB01.md), [DELIM01-FIX01](ADEL-S01-006-DELIM01-FIX01.md) y [TRACE01](ADEL-S01-006-TRACE01.md). `ADEL-QG-001` no está disponible en el repositorio; no se le atribuyen criterios. Los registros RED/GREEN/REFACTOR históricos permanecen en esos informes. Este cierre ejecutó pruebas actuales, no repitió sus fases RED.

| Criterio de Sprint 01 | Evidencia actual | Estado |
| --- | --- | --- |
| Receta JSON v1 validada y capacidades futuras rechazadas antes de leer | `tests/test_recipes.py` y pruebas de corte vertical; contrato en SPEC.md §4 | Verificado en suite actual |
| Rutas del encargo y rechazo de cruces | `tests/test_workspace.py` y `test_cross_client_recipe_route_is_rejected_before_foreign_read`; dos casos de symlink omitidos por el entorno | Parcial por omisiones |
| CSV hasta 10 MiB, codificación, formato, comillas, ancho y delimitador | `tests/test_importer.py`; ambigüedad de dos lecturas plausibles requiere confirmación explícita | Verificado en suite actual |
| Diagnóstico de filas, columnas, duplicados, ausencias, espacios y tipo inferido | `tests/test_diagnostics.py`; oráculo sintético Piloto A | Verificado en suite actual |
| Original intacto, resumen reproducible, hashes y publicación comprobable | `tests/test_vertical_slice.py`; `verify_delivery` distingue `completo-verificado`, `incompleto`, `inconsistente` y `no-verificable` | Verificado en suite actual |
| Revisión independiente y aceptación del responsable | PLAN.md §01.6 y §8; no hay confirmación final del revisor sobre el corte actual | Pendiente; bloquea cierre |

## Evidencia ejecutada en este corte

Desde la raíz del proyecto se ejecutó la suite completa contra el árbol de trabajo actual, primero con `.venv/Scripts/python.exe` y después con `.pytest_tmp/fix02_clean_env/Scripts/python.exe`, entorno que FIX02 había instalado previamente desde `uv.lock`. En ambos casos se estableció `PYTHONPATH` a `src` y se usaron `-q -p no:cacheprovider -rs` con directorios `--basetemp` distintos (`.pytest_tmp/final_20261027` y `.pytest_tmp/final_locked_20261027`). **Ambas ejecuciones: 132 aprobadas, 2 omitidas, 0 fallos**; las omisiones son `tests/test_workspace.py:149,162` por indisponibilidad de symlinks. La segunda ejecución reutilizó el entorno de FIX02: no representa una instalación nueva ni una revisión independiente en esta tarea. `git diff --check` terminó sin errores de formato; Git advirtió una futura conversión LF/CRLF de cuatro archivos modificados.

El fixture Piloto A actual tiene SHA-256 `583c2403e3425065bf3c1da265a018f9570e9cc03d28a099f4d4ec86f93c882d`. El oráculo documentado y comprobado por la integración es **6 filas, 4 columnas, 1 duplicado exacto, 3 celdas vacías literales y 1 celda solo espacios**. La prueba comprueba bytes y SHA-256 del original antes y después, hash del resumen, ausencia de valores sintéticos en resumen/manifiesto y reproducción de los mismos bytes de resumen en otro espacio. El SHA-256 actual de `tests/test_vertical_slice.py` es `1A829354A31C0DF5264447974A0D900E41AD359CAD8A4FAEAB707AAE380350FB`; los hashes históricos de esa suite no identifican este corte.

## Límites y pendientes de decisión

1. **Revisor independiente:** una persona o agente distinto del implementador debe recibir el contrato, el fixture y su hash, los registros RED/GREEN/REFACTOR y este corte; ejecutar la suite desde un entorno limpio autorizado, comprobar las omisiones y registrar hallazgos, correcciones y confirmación. La revisión previa de FIX01 y el entorno creado por FIX02 no sustituyen esa confirmación sobre el corte actual.
2. **Aceptación del responsable:** tras la confirmación independiente, registrar la decisión expresa sobre PLAN.md §01.6 y §8. Solo entonces corresponde marcar la tarea y acreditar el 20% técnico del sprint.
3. **Límites técnicos conocidos:** los dos archivos publicados no son atómicos en conjunto; un resumen huérfano es `incompleto`. `completo-verificado` comprueba estructura y hashes al leer, no recalcula el diagnóstico ni autentica a un escritor coordinado. La publicación usa semántica de `os.rename` verificada en Windows y rechaza POSIX. Las rutas pueden cambiar concurrentemente después de comprobarse. Los límites de 64 MiB y 64 niveles de JSON publicado no tienen pruebas de frontera exacta en este corte. Los symlinks quedaron omitidos; las pruebas de junction sí corrieron. Ninguna de estas verificaciones autoriza datos reales sin la política de acceso, retención, eliminación y cifrado de SPEC.md §7.

**Resultado operativo:** el diagnóstico CSV puede pasar a revisión técnica cuando `verify_delivery` devuelve `completo-verificado` y se comprueban cliente, encargo y original. Sprint 01 permanece **pendiente de cierre formal**. No se modificó PLAN.md ni se asignó el 20%, porque faltan las decisiones exigidas por su propia definición de terminado.
