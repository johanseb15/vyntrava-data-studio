# ADEL-S02-ACCEPT-REV01 — revisión independiente

**Proyecto:** VYNTRAVA-DATA-001
**Fecha:** 2026-10-27
**Alcance:** Sprint 02, datos sintéticos.
**Dictamen técnico:** favorable para el alcance probado.
**Cierre formal y 25%:** pendiente de aceptación expresa del responsable conforme a PLAN.md §8.

## Evidencia revisada

Se contrastaron SPEC.md §§4–9, PLAN.md §§3–4 y §8, la implementación en `src/vyntrava_data_studio/`, las pruebas y `reports/ADEL-S02-001.md` y `reports/ADEL-S02-002.md`. La copia recibida no contiene `.git`; por ello no se pudo confirmar el hash de corte citado en ADEL-S02-002 ni comparar cambios posteriores.

- Suite repetida en el entorno incluido: `.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp\accept_s02 --tb=short` → **144 passed, 2 skipped**. Las dos omisiones son pruebas de symlinks no disponibles en este entorno. Antes de repetirla se creó `.pytest_tmp`, porque pytest no podía crear el subdirectorio bajo un padre ausente.
- Prueba operativa independiente del piloto A con `TemporaryDirectory`: estado `revision_requerida`; 6 filas iniciales y 5 finales; 3 incidencias `no_vacio` y 1 `email_simple`; dos salidas y un manifiesto. Se verificaron los SHA-256 de receta, original y ambas salidas contra el manifiesto. El hash del original permaneció igual. Todos los controles resultaron verdaderos.
- Inspección del flujo: las reglas se aplican en orden; la eliminación de duplicados exige HMAC vinculado a receta y entradas; una validación bloqueante retorna antes de publicar; se comprueban de nuevo receta y originales antes de publicar.

## Reservas

La publicación de varias salidas y manifiesto no es atómica como conjunto. Las dos pruebas de symlinks quedaron omitidas, aunque la suite sí ejecutó las pruebas de junctions. El verificador persistente de paquetes de Sprint 02 corresponde a Sprint 04. La revisión cubre el paquete sintético recibido y no autoriza datos reales ni acredita identidad personal mediante HMAC.

## Decisión

**Aceptación técnica independiente: favorable.** No se encontraron objeciones nuevas en los controles ejecutados. La aceptación del responsable, exigida por PLAN.md §8 para cerrar Sprint 02 y acreditar su 25%, no consta en esta revisión y debe registrarse por separado.
