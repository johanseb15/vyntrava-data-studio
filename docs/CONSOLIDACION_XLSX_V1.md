# Primer flujo de consolidación XLSX

Este corte experimental amplía la receta `1.1.0` con la regla `unir_filas`. Usa el importador XLSX, las validaciones, el publicador CSV y el verificador de paquetes existentes. Su prueba de integración está en `tests/test_xlsx_consolidation.py` y emplea únicamente datos ficticios.

La receta declara dos libros `.xlsx` con hojas visibles y esquemas. La regla apunta a la entrada que recibirá las filas y a una `otra_entrada`:

```json
{"id":"unir","op":"unir_filas","entrada":"lote_a","params":{"otra_entrada":"lote_b"}}
```

El motor conserva el orden: filas de `lote_a` y después filas de `lote_b`. Exige encabezados literalmente iguales al unir; no los normaliza, no deduplica y no elimina filas con incidencias. La salida `tabla_csv` usa `fuente: "lote_a"`. El `resumen_json` registra las filas añadidas, las incidencias y `procedencia` con SHA-256, formato y hoja de los libros unidos. `evidencia/manifiesto.json` registra los hashes de ambas entradas y de todas las salidas. `verify_recipe_package` comprueba la integridad local de esos archivos sin reejecutar la receta.

Si los encabezados difieren, `run_recipe` devuelve `DeliveryError("schema_mismatch")` antes de publicar CSV, resumen o manifiesto. Una referencia inexistente o igual a la entrada destino falla durante la validación de la receta. Los originales no se modifican.

El estado `revision_requerida` exige revisión humana antes de cualquier entrega. Este corte no autoriza datos reales, no acredita corrección comercial ni sustituye una política de normalización de encabezados. El script de evidencia `operations-evidence/ADEL-OPERATIONS-002/data-run-demo.py` genera una ejecución ficticia reproducible con el motor y verifica su paquete.
