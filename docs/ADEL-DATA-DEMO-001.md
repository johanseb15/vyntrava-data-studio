# ADEL-DATA-DEMO-001 — consolidación XLSX sintética

Esta es una demostración local con datos **ficticios**. Se apoya en la receta `1.1.0`, el fixture de integración `tests/test_xlsx_consolidation.py`, `run_recipe` y `verify_recipe_package` ya integrados en `master`. No introduce otro motor.

## Ejecución local

Desde la raíz de este worktree, usar el Python 3.12 del entorno ya instalado y ejecutar **una vez por ruta nueva**:

```powershell
$python = 'C:\Vyntrava\RadarDelDragon\lab\repos\vyntrava-data-studio\.venv\Scripts\python.exe'
& $python examples\adel_data_demo_001.py C:\Vyntrava\operations-evidence\ADEL-DATA-DEMO-001\mi-paquete-sintetico
```

El comando no sobrescribe una ruta existente. Crea `DATOS_SINTETICOS.txt`, `receta.json`, dos XLSX en `clientes/cliente_demo/encargo_demo/originales/`, `salidas/consolidado.csv`, `salidas/resumen.json` y `evidencia/manifiesto.json`. Imprime rutas, estado, cuatro hashes y el resultado de `verify_recipe_package`. El CSV tiene cuatro filas, en orden de origen. La fila `004` lleva `cantidad=0` para mostrar una incidencia controlada.

`revision_requerida` significa que una alerta no bloqueante quedó registrada y que **una persona debe revisar el paquete antes de cualquier entrega**. El resultado no está aprobado automáticamente. Si los encabezados de los dos libros difieren, el motor devuelve `schema_mismatch` y no publica salidas. Esta demo no usa datos reales, no normaliza encabezados, no garantiza aptitud comercial y no se publica.

## Guion interno de 90 segundos

| Tiempo | Mostrar y decir |
|---|---|
| 0–15 s | **Problema.** «Dos planillas con el mismo esquema llegaron por separado. Queremos una sola vista sin perder la pista de cada archivo». |
| 15–30 s | **Entrada.** Abrir `lote_a.xlsx` y `lote_b.xlsx`. «Son datos inventados: dos filas en cada libro. La segunda planilla incluye una cantidad cero para probar la alerta». |
| 30–45 s | **Consolidado.** Abrir `consolidado.csv`. «El motor de recetas unió las filas en orden: cuatro registros, con encabezados iguales». |
| 45–60 s | **Alerta.** Abrir `resumen.json`. «La validación detectó una incidencia de cantidad; el registro no se descartó silenciosamente». |
| 60–75 s | **Trazabilidad.** Abrir `manifiesto.json`. «Los SHA-256 identifican las dos fuentes y las dos salidas. El verificador independiente comprobó que el paquete sigue íntegro». |
| 75–90 s | **Revisión humana.** Señalar `revision_requerida`. «La alerta obliga a una persona a revisar antes de entregar. Es una demo local, no un resultado aprobado ni un producto terminado». |

La próxima decisión es revisar el paquete y el guion internamente. No contactar prospectos, subir archivos ni habilitar una demo pública con este corte.
