# Verificación de paquetes `run_recipe` — Sprint 04

## API

```python
from pathlib import Path
from vyntrava_data_studio.package_verifier import verify_recipe_package

result = verify_recipe_package(
    Path("receta.json"), Path("clientes"), "cliente_a", "encargo_a"
)
if result.ok:
    print(result.status)  # validado o revision_requerida
else:
    print(result.issues[0].code)
```

La receta debe ser el archivo original de la ejecución. `root` es la raíz de
clientes y `client`/`job` son identificadores, no rutas. La función lee el
manifiesto en `evidencia/manifiesto.json`, los originales declarados y todas
las salidas declaradas; no ejecuta transformaciones ni escribe archivos.
`PackageVerification` contiene `ok`, `status` y una tupla de
`VerificationIssue(code)`. Actualmente devuelve la primera incidencia en
orden estable. `status` es `None` si falla la verificación.

## Controles

- Exige JSON de manifiesto sin claves duplicadas, constantes fuera de JSON,
  estructura excesivamente profunda o tamaño superior a 64 MiB.
- Contrasta id, versión y SHA-256 de receta; ids de entrada y salida, formato,
  hoja o codificación y delimitador según versión; SHA-256 de cada original y
  salida; nombres exactos y ausencia de archivos ajenos en `salidas/` y
  `evidencia/`.
- Comprueba estructura de parámetros, aprobaciones, validaciones y análisis,
  y coherencia del estado `validado` o `revision_requerida` con incidencias.
  Un estado `bloqueado` no constituye paquete publicado.
- Usa las protecciones del workspace para cliente, encargo, rutas, archivos
  regulares, symlinks y junctions. Los nombres y contenidos no se incluyen en
  los resultados ni en los códigos.

## Códigos

| Código | Significado |
| --- | --- |
| `invalid_path` | Identificador, ruta o enlace rechazado. |
| `invalid_recipe` | La receta no se puede leer o validar. |
| `missing_manifest` | No hay manifiesto publicado; incluye ejecuciones bloqueadas. |
| `invalid_manifest` | JSON, estructura o estado incoherente. |
| `recipe_hash_mismatch` | Cambiaron los bytes de la receta. |
| `missing_input` | Falta un original declarado. |
| `input_hash_mismatch` | Cambiaron los bytes de un original. |
| `missing_output` | Falta una salida declarada. |
| `output_hash_mismatch` | Cambiaron los bytes de una salida. |
| `unexpected_file` | Hay un archivo ajeno en salidas o evidencia. |

`ok=True` acredita integridad local de archivos y consistencia del manifiesto
respecto de la receta entregada. **No acredita corrección de negocio:** un
revisor debe contrastar resultados con oráculos independientes. Tampoco
acredita autenticidad criptográfica del paquete: el manifiesto no está firmado
y un actor capaz de sustituir archivos y hashes podría fabricar un paquete
coherente. La firma HMAC de aprobaciones de deduplicación se registra, pero
esta API no posee la clave ni verifica esa firma. El estado
`revision_requerida` conserva su obligación de revisión humana.

La identidad de cliente y encargo se obtiene de la ruta solicitada; el
manifiesto existente no contiene un identificador de cliente/encargo firmado.
El llamador debe seleccionar el espacio correcto. Los controles de rutas y
hash no eliminan carreras frente a reemplazos concurrentes: serializar
escritores y verificadores del mismo encargo.
