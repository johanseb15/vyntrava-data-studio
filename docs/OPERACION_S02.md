# Operación de limpieza CSV v1 — Sprint 02

Crear un espacio sintético con `originales/`, `trabajo/`, `salidas/` y `evidencia/`. Importar `run_recipe` de `vyntrava_data_studio.sprint02`. Llamarlo con ruta de receta, raíz de clientes, id de cliente e id de encargo. Los argumentos opcionales son `confirmed_delimiters`, `overrides`, `approvals` y `approval_key`.

Una aprobación de `eliminar_duplicados_exactos` se pasa como `approvals={id: comprobante}`. El comprobante contiene `id`, `responsable`, `receta_sha256`, `entradas_sha256` (mapa de id de entrada a SHA-256) y `firma`. Para firmar, serializar los cuatro primeros campos como JSON UTF-8 con `sort_keys=True`, `separators=(",", ":")` y `ensure_ascii=False`; calcular HMAC-SHA256 con la clave entregada por el operador. No guardar la clave en receta, reporte o manifiesto. Una firma inválida devuelve `DeliveryError("approval_required")` sin publicar salidas.

El retorno `RecipeRun` incluye `status`, rutas de `outputs`, `manifest_path` y conteos de `validations`. `bloqueado` deja las rutas vacías y `manifest_path=None`; `revision_requerida` exige revisión humana. `validado` indica únicamente que no hubo incidencias configuradas. Ninguno de esos estados constituye aprobación de negocio.

No reutilizar un encargo con archivos publicados. La publicación de varios archivos puede interrumpirse entre renombrados; en tal caso conservar la evidencia para inspección y repetir en otro encargo. Este corte no dispone aún de un verificador independiente del paquete de Sprint 02; la comprobación integral de manifiesto y salidas corresponde a Sprint 04. El flujo existente `run_diagnostic` y su verificador siguen correspondiendo solo a paquetes de diagnóstico de Sprint 01.
