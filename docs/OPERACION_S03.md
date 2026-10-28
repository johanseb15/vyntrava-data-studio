# Operación sintética de Sprint 03

Esta guía describe la API local `run_recipe` de `vyntrava_data_studio.sprint02` para CSV y XLSX, análisis y gráfico PNG. El resultado requiere revisión humana antes de cualquier entrega. Usar encargos sintéticos separados y conservar los bytes de receta y originales.

## Preparar entradas y espacio

Crear `clientes/<cliente>/<encargo>/originales/`, `trabajo/`, `salidas/` y `evidencia/` antes de ejecutar. `cliente` y `encargo` son identificadores internos, no rutas libres. Colocar cada archivo de entrada en `originales/`; el motor lee esa carpeta y no reescribe sus archivos. Mantener un solo escritor por encargo y no reutilizar un encargo que ya tenga salidas publicadas.

Para CSV, declarar `formato: "csv"`, `ruta` con extensión `.csv`, `codificacion: "utf-8"` o `"utf-8-sig"` y, preferentemente, `delimitador: ","` o `";"`. Si se omite el delimitador, pasarlo explícitamente mediante `confirmed_delimiters={"ventas": ";"}`. El lector no cambia el separador silenciosamente. La fila inicial es el encabezado y las filas siguientes deben ser rectangulares. Un CSV con BOM requiere `utf-8-sig`.

Para Excel, usar receta `1.1.0` y una entrada como `{"id": "ventas", "ruta": "ventas.xlsx", "formato": "xlsx", "hoja": "Ventas"}`. `hoja` debe nombrar literalmente una hoja visible; no hay selección automática. En XLSX no se declaran `codificacion` ni `delimitador`; en CSV no se declara `hoja`. Preparar encabezados de texto únicos en la primera fila y fechas del piloto como texto ISO. El importador rechaza fórmulas, errores, hipervínculos, fechas nativas, celdas combinadas y filas o columnas ocultas del área usada. Consultar [OPERACION_XLSX_V1.md](OPERACION_XLSX_V1.md) para la política de precisión numérica y sus límites.

## Configurar y ejecutar la receta

La receta es JSON UTF-8 con exactamente las claves superiores `id`, `version`, `tipo_encargo`, `entradas`, `esquema`, `parametros`, `reglas`, `validaciones`, `analisis` y `salidas`. CSV usa el contrato `1.0.x` o `1.1.x`; XLSX requiere `1.1.x` (usar `1.1.0` en el piloto). `esquema` declara columnas esperadas por id de entrada y `extras: "rechazar"` o `"permitir"`. Los ids y las referencias deben existir; `load_recipe` de `vyntrava_data_studio.recipes` permite validar la receta antes de ejecutar y devuelve errores `RecipeError` con `code` y `location`.

`run_recipe(recipe_path, root, client, job, confirmed_delimiters=None, overrides=None, approvals=None, approval_key=None)` recibe rutas `Path` para receta y raíz. `overrides` solo sustituye parámetros ya declarados y del mismo tipo. El motor aplica diagnóstico inicial, reglas en orden, validaciones en orden y análisis en orden. Entre las reglas disponibles están `diagnosticar`, `recortar_espacios` y `eliminar_duplicados_exactos`. Las validaciones disponibles son `columnas_requeridas`, `no_vacio`, `email_simple`, `decimal_positivo` y `entero_positivo`, cada una con severidad `advertir` o `bloquear`.

`suma_producto` usa `params.cantidad` y `params.precio`, y opcionalmente `params.grupo`; multiplica con `Decimal` y informa `filas_incluidas`, `filas_excluidas`, `exclusiones`, `unidades`, `total` y, si se agrupa, `grupos`. `conteo` cuenta filas válidas para las columnas que utiliza y puede agrupar por una columna. Una fila con incidencia en una columna usada se excluye de ese análisis; `numero_invalido` identifica un valor numérico rechazado. No interpretar una exclusión como importe cero. Los resultados centesimales se presentan con dos decimales; si los importes requieren más precisión, se conserva en las cadenas decimales del análisis, sin redondeo intermedio.

En `salidas`, `resumen_json` escribe el reporte, `tabla_csv` usa como `fuente` un id de entrada y `grafico_png` usa como `fuente` el id de un `suma_producto` agrupado. La ruta del gráfico termina en `.png`. El PNG es RGB de 900 × 500, muestra fechas o etiquetas de grupo, importes y barras, y se genera sin metadatos variables. La repetición con entradas idénticas en el mismo entorno y versiones de dependencias conserva sus bytes; entre plataformas, comprobar los valores y el contenido visual.

## Aprobaciones y estados

La regla `eliminar_duplicados_exactos` requiere `params.aprobacion` y un comprobante en `approvals` bajo ese id. El comprobante contiene `id`, `responsable`, `receta_sha256`, `entradas_sha256` (mapa de id de entrada a SHA-256 del original) y `firma`. Firmar con HMAC-SHA256 el JSON UTF-8 de los cuatro primeros campos usando `sort_keys=True`, `separators=(",", ":")` y `ensure_ascii=False`; pasar la clave como bytes en `approval_key`. Una firma o hash incorrecto causa `DeliveryError("approval_required")`. Cambiar receta u original exige una nueva aprobación. La firma acredita posesión de clave, no identidad personal; no guardar la clave en receta, reporte o manifiesto.

`RecipeRun.status` puede ser:

| Estado | Significado operativo |
| --- | --- |
| `validado` | No hubo incidencias configuradas; aún requiere revisión de negocio. |
| `revision_requerida` | Hubo incidencias `advertir`; revisar antes de cualquier entrega. |
| `bloqueado` | Hubo incidencias `bloquear`; `outputs` queda vacío y `manifest_path` es `None`. No se publica resumen, gráfico ni manifiesto. |

`RecipeRun.validations` informa incidencias y severidad por validación. Para los otros dos estados, `outputs` contiene rutas por id de salida y `manifest_path` apunta a `evidencia/manifiesto.json`.

## Revisar y verificar la entrega

Antes de entregar, confirmar cliente y encargo, revisar incidencias, exclusiones, totales y gráfico con un cálculo independiente, y comparar SHA-256 de cada original, receta y salida con `manifiesto.json`. El manifiesto registra estado, receta y versión, versión de motor, parámetros, delimitadores, hashes de entradas, aprobaciones usadas, validaciones, análisis y hashes de salidas. Para entradas XLSX registra también formato y hoja. Comprobar que no haya archivos ajenos en `salidas/` o `evidencia/`.

No hay todavía un verificador integral de paquetes de Sprint 03. `verify_delivery` de `vyntrava_data_studio.delivery` corresponde al diagnóstico de Sprint 01; no usar su resultado como acreditación de una ejecución `run_recipe`. La publicación de varias salidas y manifiesto no es atómica como conjunto. Ante interrupción o publicación parcial, conservar los artefactos para inspección y preparar otro encargo para repetir, sin sobrescribir resultados existentes.

## Errores y límites habituales

`RecipeError` señala versión, campos, tipos, rutas u operaciones inválidas antes de abrir entradas. Revisar la ubicación JSON indicada. Los CSV pueden fallar por codificación, encabezado, registros, tamaño o delimitador ambiguo; confirmar el separador contra el archivo, sin cambiarlo a ciegas. `XlsxError` expone `code` y, cuando corresponde, hoja, fila y columna; consultar la guía XLSX antes de corregir un `numeric_precision`. Los errores de aprobación, cambio de original o receta y publicación llegan como `DeliveryError` con un código técnico; conservar la evidencia y no forzar un reintento sobre el mismo encargo.

El valor numérico almacenado en Excel prevalece sobre el formato visual. El importador admite hasta 15 dígitos significativos del valor recibido; para más precisión, capturar el dato como texto desde el origen. No puede recuperar dígitos que Excel ya haya perdido. El motor no ejecuta fórmulas ni macros. La política completa de XLSX y la precaución sobre pérdida previa están en [OPERACION_XLSX_V1.md](OPERACION_XLSX_V1.md). El flujo local de publicación está habilitado en Windows; los controles de ruta y hash no eliminan carreras frente a cambios concurrentes, y HMAC no sustituye una revisión humana.

## Reproducir los pilotos sintéticos

El Piloto A de diagnóstico CSV y su verificador se describen en [OPERACION_CSV_V1.md](OPERACION_CSV_V1.md). Para el Piloto B, usar las seis filas sintéticas de `SPEC.md` §8 en CSV UTF-8 con BOM y `;`, o la misma tabla textual en una hoja visible `Ventas` de un `.xlsx` separado. Las fechas y precios de Excel deben ser texto. Crear encargos distintos y recetas equivalentes; `1.0.0` sirve para CSV y `1.1.0` para XLSX. Firmar por separado cada combinación de receta y original.

Configurar deduplicación exacta aprobada, `entero_positivo` sobre `cantidad` con severidad `advertir`, y `suma_producto` agrupado por `fecha`; añadir `resumen_json` y `grafico_png` cuya fuente sea el id del análisis. El oráculo es: 6 filas iniciales, 1 duplicada, 5 tras deduplicar, 1 incidencia de cantidad, 4 filas incluidas, 1 excluida, 8 unidades y total `42.50`; grupos `2026-01-05: 27.50`, `2026-01-06: 10.00`, `2026-01-07: 5.00`. El estado esperado es `revision_requerida`. Una receta equivalente con severidad `bloquear` devuelve `bloqueado` sin publicar. Los casos automatizados `tests/test_sprint03_red.py`, `tests/test_charts.py` y `tests/test_importer_xlsx.py` muestran las estructuras de entrada y las comprobaciones actuales.
