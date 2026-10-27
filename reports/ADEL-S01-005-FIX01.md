# ADEL-S01-005-FIX01 — Cierre de validaciones técnicas

**Alcance:** revisión del corte vertical de Sprint 01 y de la aceptación de rutas de la tarea 01.2. Datos y nombres de prueba exclusivamente sintéticos. La revisión independiente integral de 01.6 y la aceptación del responsable siguen pendientes.

## Hallazgo y corrección

La revisión detectó que `RecipeError(read_error)` y `WorkspaceError(inaccessible_path)` encadenaban la excepción de sistema. Aunque sus mensajes eran genéricos, una traza ordinaria mostraba la ruta completa. `load_recipe` y `_status` ahora suprimen esa causa al presentar el error controlado. `CsvError` ya suprimía las causas de lectura; `DeliveryError` presenta códigos sin rutas.

| Caso | RED | GREEN |
|---|---|---|
| Receta ausente con nombre sintético privado | `pytest tests/test_recipes.py::test_missing_recipe_error_trace_does_not_reveal_path -q --basetemp=.pytest_tmp/fix01_red` → 1 fallo: la traza incluía el nombre | Mismo caso con `fix01_green` → 1 aprobada |
| Entrada inaccesible con nombre sintético privado | `pytest tests/test_workspace.py::test_inaccessible_input_error_trace_does_not_reveal_path -q --basetemp=.pytest_tmp/fix01_workspace_red` → 1 fallo: la traza incluía el nombre | Mismo caso con `fix01_workspace_green` → 1 aprobada |

Los comandos RED/GREEN anteriores se ejecutaron con `.venv/Scripts/python.exe -m` como prefijo de `pytest`. Las dos pruebas afirman el código estable del error y examinan `traceback.format_exception` para comprobar que no se publica el nombre.

## Contraste de requisitos

- **Piloto A, oráculo manual:** seis registros de datos y cuatro encabezados. La tercera fila repite exactamente la segunda; email está vacío en filas 2 y 3, nombre en fila 6 y ciudad contiene solo espacios en fila 4. Resultado: 1 duplicado, 3 vacíos literales y 1 celda solo espacios. El resumen y el manifiesto del test de integración comprueban esos conteos, hashes y ausencia de dos valores de celda sintéticos.
- **Original y aislamiento:** `read_csv` abre en modo `rb`; el corte vertical vuelve a resolver la entrada y comprueba SHA-256 antes y después. La prueba añadida `test_cross_client_recipe_route_is_rejected_before_foreign_read` coloca un CSV sintético en otro cliente, intenta una ruta de receta cruzada y comprueba `RecipeError(invalid_path)` antes de cualquier apertura del original ajeno o creación de salidas. `resolve_output` no acepta `originales`; el test de competencia conserva una salida creada por otro proceso. Esto satisface la aceptación técnica de 01.2 en el entorno probado.
- **Fiabilidad de evidencia:** los hashes SHA-256 de `tests/test_importer.py` y `tests/test_diagnostics.py` coinciden con ADEL-S01-003/004: `30037970ece18e318584912d2090cfdd73ceabdfd2b9265ef90858ba0a4597aa5` y `1943c3904d6c8e10fcb93ceae1e8772a7e77cb6ddff5add5f2f23b42a35c0f6a`. `tests/test_vertical_slice.py` cambió por la prueba de cruce; su hash actual es `cb4eb81a5b4697c5b49be7de4f03ac59db5106a85c72d7816132862139967032`. Los hashes actuales de `tests/test_workspace.py` y `tests/test_recipes.py` son `a260da99c0b7f99c0ecd4d4bf1b8b636a9f9bb1fc231d716edbacf31eab1405a` y `09d8d559c88599ab234224f0ac799db33b8ba3f12cfea5e020303eddd35c5ab6`.

## Ejecución y límites

La suite en el árbol de trabajo terminó con **95 aprobadas y 2 omitidas** (`.venv/Scripts/python.exe -m pytest -q -rs --basetemp=.pytest_tmp/fix01_final`). Una copia aislada de `src/`, `tests/`, `SPEC.md`, `PLAN.md` y los archivos de proyecto, ejecutada con `PYTHONPATH` apuntando a esa copia y el entorno Python existente, terminó también con **95 aprobadas y 2 omitidas** (`.pytest_tmp/fix01_snapshot_final`). Las dos omisiones corresponden a creación de symlinks no permitida en este equipo; las pruebas de junction sí se ejecutan. `git diff --check` no informó errores de formato.

La copia aislada verifica el código separado del árbol de trabajo, pero reutiliza `.venv`; no equivale a instalar dependencias en un entorno nuevo. La protección de rutas frente a sustitución concurrente de directorios sigue limitada por el contrato de `SPEC.md` §6. La revisión de 01.6 debe ejecutar las suites desde un entorno limpio autorizado, registrar hallazgos y obtener la confirmación de un revisor distinto del implementador antes de acreditar Sprint 01.

**Revisión separada:** un agente de revisión solo lectura señaló como hallazgo **bloqueante** la filtración de ruta en `WorkspaceError` y como hallazgo de evidencia la falta de una prueba integrada que mostrara rechazo de una ruta cruzada antes de leer el archivo ajeno. Responsable: Codex. Estado: ambos **corregidos y confirmados** por el revisor. El revisor recalculó a mano el oráculo del Piloto A (6 filas, 4 columnas, 1 duplicado, 3 vacíos literales y 1 celda solo espacios), examinó preservación de bytes y hash, rechazó la ruta cruzada antes de abrir el original ajeno y verificó las dos pruebas de trazas privadas. Ejecutó toda la suite sobre una copia aislada con el `.venv` existente: `$env:PYTHONPATH = (Resolve-Path .\src).Path; ..\..\.venv\Scripts\python.exe -m pytest -q -rs --basetemp=.\pytest_runs\full_suite_01` → **95 aprobadas, 2 omitidas**.

**Bloqueo de entorno limpio:** el mismo revisor creó `.pytest_tmp/independent_01_6/.venv` desde cero. `uv sync --offline --locked` no pudo acceder a `C:\Users\soporte\AppData\Local\uv\cache` (`Acceso denegado`, error 5). `python -m pip install --no-index pytest` tampoco encontró una distribución local. Se mantiene abierto el primer criterio de 01.6 hasta repetir la suite con dependencias instaladas en un entorno nuevo autorizado. Responsable de habilitar el entorno: operación del proyecto; estado: **pendiente**. La aceptación final del responsable y la confirmación de cierre del revisor también permanecen pendientes.

**Decisión FIX01:** validaciones técnicas y privacidad de los dos errores corregidas; cierre de Sprint 01 **pendiente** por 01.6. Responsable de las correcciones: Codex. Revisor de cierre de 01.6: por designar.
