# Operación CSV v1 — diagnóstico de Sprint 01

## Preparación

Usar un espacio separado por encargo, con `originales/`, `trabajo/`, `salidas/` y `evidencia/` ya creados. Conservar el CSV original y la receta JSON exacta; la verificación compara sus SHA-256 con el manifiesto. Trabajar con un solo escritor por encargo y mantener permisos de acceso adecuados. Este corte admite CSV y una única salida `resumen_json` de diagnóstico; las reglas, validaciones, análisis y entregas comerciales aún no implementados se rechazan.

Durante desarrollo y auditoría usar exclusivamente el Piloto A sintético. Antes de datos reales se requieren decisiones de acceso, retención, borrado y cifrado conforme a SPEC.md. No poner valores de celdas ni secretos en nombres, errores o reportes.

## Ejecución y verificación

Desde un entorno Python con el paquete disponible, invocar `run_diagnostic(recipe_path, root, client, job, confirmed_delimiters=None)` de `vyntrava_data_studio.delivery`. Si la receta no declara delimitador, pasar una confirmación explícita por id de entrada. El resultado devuelve rutas del resumen y manifiesto; **no** implica aprobación de negocio.

El importador usa el delimitador declarado o confirmado, sin cambiarlo silenciosamente. Si el otro delimitador también produce encabezados no vacíos y únicos y registros rectangulares de varias columnas, la ejecución se detiene: devuelve `delimiter_mismatch` cuando el seleccionado produce una sola columna, o `delimiter_ambiguous` cuando ambos producen varias columnas. Tras revisar el CSV, el operador puede repetir la ejecución con `confirmed_delimiters` y el mismo delimitador declarado; una confirmación distinta se rechaza. La confirmación explícita queda registrada en el manifiesto como delimitador efectivo. Esta regla no detecta todos los delimitadores incorrectos; revisar el CSV y su declaración contra SPEC.md §5 ante una duda. No modificar el original ni cambiar la confirmación a ciegas para forzar la ejecución.

Antes de consumir cualquier resultado, invocar `verify_delivery(recipe_path, root, client, job)` con la misma receta y el mismo espacio. Aceptar únicamente `completo-verificado` como paquete íntegro para revisión humana. La función no modifica archivos y devuelve solo uno de estos estados:

| Estado | Significado | Acción |
| --- | --- | --- |
| `completo-verificado` | Receta y originales coinciden por SHA-256 con el manifiesto; la estructura y referencias del manifiesto y resumen, el hash del resumen y los archivos esperados se comprobaron; no hay temporales de diagnóstico. No acredita autenticidad frente a escritura coordinada ni exactitud matemática recalculada. | Revisar cliente, encargo, controles y resultados de negocio antes de cualquier entrega. |
| `incompleto` | Falta el manifiesto y `evidencia/` está vacío; puede existir un resumen huérfano o temporales en `trabajo/`. | Retener evidencia y revisar interrupción; preparar un nuevo encargo para reejecutar. |
| `inconsistente` | Hay un manifiesto inválido, un artefacto esperado ausente o incongruente, hash o referencia distinta, archivos ajenos en salidas/evidencia, o temporal de diagnóstico junto a un paquete publicado. Incluye JSON publicado mayor de 64 MiB o más profundo que 64 niveles. | NO GO; aislar el encargo para revisión y preparar uno nuevo si se necesita repetir. |
| `no-verificable` | Un error de acceso o de comprobación de rutas impide clasificar el paquete con confianza; la ausencia de un original esperado se clasifica como `inconsistente`. | NO GO; resolver la causa y verificar de nuevo sin alterar artefactos. |

La mera existencia de `evidencia/manifiesto.json` nunca basta. El criterio operativo es verificar inmediatamente antes de consumir. Una verificación pasada puede quedar obsoleta si otro proceso cambia archivos después; coordinar el único escritor y controlar permisos.

Si falta el manifiesto y hay cualquier archivo en `evidencia/`, el estado es `inconsistente`, aunque el resumen esté ausente o huérfano. Cada JSON publicado tiene un límite de verificación de 64 MiB (67.108.864 bytes) y 64 niveles de anidamiento; superarlo produce `inconsistente` cuando el manifiesto está presente y se llega a leer ese artefacto. Con manifiesto ausente, prevalece la clasificación `incompleto` o `inconsistente` según el contenido de `evidencia/`. Estos límites no cambian el máximo de entrada CSV de 10 MiB (10.485.760 bytes) de SPEC.md. Un paquete que supere el límite JSON requiere revisión operativa, no una aceptación manual del estado.

## Interrupciones, reintentos y recuperación

El motor prepara dos archivos privados en `trabajo/`, vuelve a comprobar los hashes de receta y originales, publica primero el resumen y después el manifiesto. Un error al crear, escribir o cerrar temporales puede dejar archivos parciales. Una interrupción después del primer renombrado deja un resumen huérfano. Un fallo al publicar el manifiesto puede dejar también un temporal. Conservar estos archivos para inspección; no borrar ni renombrar automáticamente y no tratar el resumen huérfano como entrega válida.

Revisar el estado, registrar hashes y causa técnica sin datos sensibles y detener la entrega. Si se requiere repetir, crear **otro encargo** con originales y receta preservados, y volver a ejecutar allí. Un reintento en el mismo encargo puede colisionar con salidas previas; nunca sobrescribir ni reutilizar un nombre publicado para “recuperar” el paquete.

En Windows se comprobó que `os.rename` rechaza un destino existente en este entorno. El flujo está habilitado solo en Windows; en POSIX la semántica puede reemplazar el destino y la publicación se rechaza hasta disponer de una garantía de no sobrescritura. Los dos renombrados no son atómicos en conjunto. La verificación no es firma ni protección absoluta frente a un escritor malicioso que pueda modificar archivos y hashes de forma coordinada. Los controles de ruta tampoco eliminan las carreras frente a cambios concurrentes de directorios.

## GO / NO GO

**GO para iniciar la revisión técnica del diagnóstico:** `completo-verificado`, cliente y encargo correctos y originales preservados. La revisión humana de controles y resultados de negocio sigue siendo necesaria antes de cualquier entrega. **NO GO para entrega o aprobación:** cualquier otro estado, validación bloqueante pendiente, duda sobre identidad o permisos, o capacidad comercial no implementada. Este ciclo no acredita por sí solo el cierre de Sprint 01; requiere validación independiente en entorno limpio y aceptación del revisor según PLAN.md §01.6.
