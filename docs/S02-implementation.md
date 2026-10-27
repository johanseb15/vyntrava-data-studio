# Sprint 02 — diseño e implementación

Objetivo: ejecutar recetas CSV v1 de limpieza y validación sobre datos sintéticos, con resultados reproducibles y sin publicar datos cuando una validación bloquea.

Enfoque: conservar `run_diagnostic` para Sprint 01 y añadir `run_recipe` como corte de Sprint 02. Las reglas se aplican en orden sobre tablas inmutables. Una eliminación de duplicados requiere un comprobante HMAC-SHA256 firmado con una clave que aporta el operador, vinculado al hash de receta y a todos los originales. El resultado de una validación bloqueante se devuelve al operador en memoria; ninguna salida se publica. Las advertencias quedan en el resumen para revisión. `tabla_csv` se habilita para los datos procesados. Análisis y gráficos permanecen en Sprint 03 según SPEC.md.

El comprobante contiene `id`, `responsable`, `receta_sha256`, `entradas_sha256` y `firma`. La firma es HMAC-SHA256 del JSON canónico de los cuatro primeros campos. El secreto no se escribe en archivos ni manifiestos. Los archivos de salida se publican solo después de verificar otra vez los hashes de receta y originales. Los nuevos artefactos usan los mismos controles de ruta de Sprint 01.

Pruebas: piloto A con conteos manuales antes y después; aprobación ausente, alterada o ligada a otros hashes; parámetros inválidos; validaciones bloqueantes y advertencias; repetición exacta; original intacto; regresión de Sprint 01.
