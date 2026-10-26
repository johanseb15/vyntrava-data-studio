# Vyntrava Data Studio — Especificación del producto

**Proyecto:** VYNTRAVA-DATA-001  
**Versión:** 0.3 — Contrato técnico v1 propuesto para aprobación  
**Metodología:** ADEL + Superpowers 7.0.1  
**Estado:** Diseño documental

## 1. Propósito y usuarios

Vyntrava Data Studio es una herramienta **interna** para resolver encargos freelance de datos de distintos clientes mediante un motor Python local, reutilizable y configurable con recetas versionadas. Debe reducir el trabajo repetido sin desarrollar software diferente para cada pedido. Sus usuarios iniciales son las personas de Vyntrava que preparan y verifican entregables.

El flujo objetivo es: recibir archivos de un encargo, seleccionar o adaptar una receta, validar entradas, ejecutar transformaciones y análisis deterministas, revisar controles de calidad y producir un paquete de entrega reproducible. Las tareas habituales se ejecutan con herramientas locales y recetas. Codex se reserva para diseñar, implementar o revisar capacidades complejas compartidas, usando solo datos sintéticos durante el desarrollo.

## 2. Alcance y límites

- Importar CSV primero. Incorporar Excel `.xlsx` en Sprint 03, con política de hojas y formatos propia aprobada antes de implementarlo.
- Diagnosticar filas y columnas, duplicados exactos, valores ausentes, celdas que contienen solo espacios, tipos inferidos y posibles problemas de formato. Un tipo inferido no equivale a certeza semántica.
- Aplicar limpieza y validación deterministas definidas en recetas. Presentar los cambios ambiguos o destructivos para aprobación explícita; no corregirlos en silencio ni inventar valores faltantes.
- Generar estadísticas descriptivas, indicadores configurados, visualizaciones y exportaciones según el encargo, con resultados contrastables frente a ejemplos conocidos.
- Entregar, según la receta, datos procesados, resultados de validación, gráficos o tablas, informe de transformaciones y manifiesto de ejecución.
- Preservar siempre los originales y permitir repetir una ejecución con las mismas entradas, versión de receta, parámetros y versión del motor.

Fuera del primer alcance: PDF, conectores de bases de datos, sugerencias mediante IA, fusiones automáticas, análisis estadístico avanzado, empaquetado de escritorio y publicación pública. El procesamiento determinista no requiere servicios pagos ni APIs externas. La interfaz Streamlit se considera después de demostrar el motor con los dos pilotos.

## 3. Arquitectura modular mínima

1. **Espacio de encargo:** identifica cliente y encargo, define raíces de entrada, trabajo temporal y salida, y comprueba límites de rutas.
2. **Importación:** lee formatos admitidos sin modificar originales; conserva nombres de columnas y orden de filas, y registra cómo interpretó el archivo.
3. **Recetas:** configuración versionada y validable, separada del código del motor.
4. **Diagnóstico y validación:** informa problemas de entrada y controles posteriores, con estados que permiten, advierten o bloquean la entrega.
5. **Transformaciones:** aplica reglas deterministas con parámetros explícitos y trazabilidad mediante conteos y decisiones, sin registrar valores sensibles por defecto.
6. **Análisis y visualización:** calcula indicadores y gráficos configurados por receta, independientemente de Streamlit.
7. **Exportación y manifiesto:** produce salidas y metadatos suficientes para revisar y repetir la entrega.
8. **Interfaz opcional:** Streamlit consume las mismas operaciones del motor cuando se demuestre su utilidad operativa.

Base tecnológica prevista: Python 3.12; pandas y NumPy para procesamiento; pytest para pruebas; uv para dependencias; Git para versiones. Matplotlib o Plotly se elegirán al llegar a visualizaciones según el entregable. Estas elecciones no implican instalaciones en esta fase.

## 4. Contrato JSON de receta v1

La receta es un archivo JSON UTF-8, objeto único, sin comentarios, claves duplicadas ni valores no JSON. Este contrato se aprueba en Sprint 00; su ejecución se incorpora por etapas. El ejemplo define la forma, no crea archivos ni ejecuta operaciones:

```json
{
  "id": "piloto_clientes",
  "version": "1.0.0",
  "tipo_encargo": "limpieza_clientes",
  "entradas": [{"id": "clientes", "ruta": "clientes.csv", "formato": "csv", "codificacion": "utf-8", "delimitador": ","}],
  "esquema": {"clientes": {"columnas": ["id", "nombre", "email", "ciudad"], "extras": "rechazar"}},
  "parametros": {},
  "reglas": [{"id": "r1", "op": "diagnosticar", "entrada": "clientes", "params": {}}],
  "validaciones": [{"id": "v1", "op": "columnas_requeridas", "entrada": "clientes", "params": {"columnas": ["id", "nombre", "email", "ciudad"]}, "severidad": "bloquear"}],
  "analisis": [],
  "salidas": [{"id": "diagnostico", "tipo": "resumen_json", "ruta": "diagnostico.json"}]
}
```

**Forma y validación estática.** Son obligatorias exactamente las diez claves de nivel superior mostradas; se rechazan claves adicionales. `id`, identificadores internos y nombres de parámetro usan `[a-z][a-z0-9_]*` (1–64 caracteres), únicos en su colección. `version` es `MAJOR.MINOR.PATCH` con enteros decimales no negativos sin ceros iniciales; v1 admite solo `1.x.y` conocido por el motor. `tipo_encargo` es etiqueta informativa, sin efecto ejecutable. `entradas` y `salidas` son listas no vacías; `reglas`, `validaciones` y `analisis` pueden estar vacías; `esquema` es mapa por id de entrada y `parametros` es mapa de escalares JSON (`string`, número finito, booleano o `null`). Se rechazan ids referenciados inexistentes, duplicados, tipos incorrectos, campos exigidos ausentes y campos desconocidos en cada objeto. Los errores señalan ubicación JSON y código, sin copiar valores de celdas.

`parametros` declara valores por defecto escalares. Un valor escalar de `params` puede sustituirse solo por `{"parametro": "nombre"}` cuando el tipo exigido por la operación es escalar; se resuelve contra ese mapa antes de validar tipos. Las sobrescrituras de ejecución solo pueden nombrar parámetros declarados y conservar su tipo; nombre desconocido, referencia no resuelta o estructura adicional se rechazan. `confirmed_delimiters` es un mapa de ejecución `id_entrada -> "," | ";"`, separado de la receta, que registra la confirmación por archivo junto a los parámetros efectivos. Ninguna sustitución evalúa expresiones.

Cada entrada v1 declara `id`, `ruta` relativa de archivo base dentro de `originales/`, `formato: csv` y `codificacion: utf-8` o `utf-8-sig`. `delimitador` es opcional y, si aparece, vale `,` o `;`; si falta, el operador debe confirmarlo en `confirmed_delimiters` bajo el id de esa entrada antes de abrir el archivo. Una confirmación incompatible con el valor declarado se rechaza; el valor efectivo se registra. No se admiten comodines ni rutas a hojas. `esquema.<id>.columnas` es lista ordenada, no vacía, de encabezados literales únicos; `extras` vale `rechazar` o `permitir`. Las columnas declaradas deben existir; si `extras` es `rechazar`, el orden y conjunto deben coincidir exactamente. Si es `permitir`, las requeridas conservan su orden relativo y las extra quedan registradas. `salidas` declara `id`, `tipo` y `ruta` base relativa única dentro de `salidas/`; tipos v1: `resumen_json`, `tabla_csv` y `grafico_png`. `tabla_csv` exige `fuente` con id de entrada; `grafico_png` exige `fuente` con id de análisis `suma_producto` agrupado y se habilita en Sprint 03. Las otras claves adicionales se rechazan. `manifiesto.json` en `evidencia/` es salida obligatoria del motor, no una ruta configurable.

Cada elemento de `reglas`, `validaciones` y `analisis` tiene `id`, `op`, `entrada` y `params`; las validaciones añaden `severidad: advertir|bloquear`. Se ejecutan en el orden escrito: diagnóstico inicial, reglas, validaciones y análisis sobre el resultado validado. Ninguna sección admite nombres de función, expresiones evaluables, scripts, imports, rutas de módulos, SQL ni Python arbitrario. La lista permitida v1 y sus parámetros exactos es:

| Sección | `op` permitido | `params` y efecto |
|---|---|---|
| reglas | `diagnosticar` | `{}`; filas, columnas, duplicados exactos, vacíos y espacios. |
| reglas | `recortar_espacios` | `{"columnas": [<nombre>...]}`; elimina espacios al inicio y fin, sin imputar. |
| reglas | `eliminar_duplicados_exactos` | `{"aprobacion": <id>}`; conserva primera fila, requiere decisión humana registrada antes de ejecutar. |
| validaciones | `columnas_requeridas` | `{"columnas": [<nombre>...]}`; comprueba presencia literal. |
| validaciones | `no_vacio` | `{"columnas": [<nombre>...]}`; vacío literal o solo espacios. |
| validaciones | `email_simple` | `{"columna": <nombre>}`; formato básico de un `@`, texto a ambos lados; no verifica existencia. |
| validaciones | `decimal_positivo` | `{"columna": <nombre>}`; decimal ASCII finito mayor que cero. |
| validaciones | `entero_positivo` | `{"columna": <nombre>}`; entero ASCII mayor que cero. |
| analisis | `suma_producto` | `{"cantidad": <columna>, "precio": <columna>, "grupo": <columna opcional>}`; Decimal exacto, solo filas válidas, total y desglose. |
| analisis | `conteo` | `{"grupo": <columna opcional>}`; solo filas válidas. |

Parámetros de regla solo admiten los campos y tipos de su fila; referencias de columna deben existir. `aprobacion` remite a un registro externo firmado por el responsable del encargo, ligado al hash de entrada y receta; si falta o no coincide, la regla no se ejecuta. Una validación `bloquear` con incidencias impide la entrega final; una `advertir` conserva incidencias y exige revisión humana antes de marcar una entrega como aprobada. Para análisis, «fila válida» significa sin incidencia de validaciones configuradas para las columnas que usa ese análisis; las filas descartadas se cuentan con motivo. Las operaciones desconocidas se rechazan durante validación estática, antes de abrir entradas o crear salidas; nunca se omiten silenciosamente.

**Compatibilidad.** El motor declara la mayor y las menores v1 que entiende. Rechaza mayor distinta, menor futura y operación/campo desconocido, incluso si `version` parece compatible. Una versión `1.x.y` anterior se acepta solo si valida íntegramente contra el esquema de esa menor; `PATCH` corrige documentación o errores sin cambiar significado de datos. Un cambio incompatible de campos, operaciones o semántica exige mayor 2 y migración explícita; no hay conversión automática. El manifiesto guarda hash del JSON original, `id`, `version`, versión del motor y parámetros efectivos. Dos ejecuciones con mismos bytes de entrada, receta, parámetros, aprobaciones y motor producen datos y controles equivalentes; hora y ubicación del espacio se separan de ese contraste.

El esquema puede describir una operación o salida de una fase posterior; el motor declara además sus capacidades implementadas y rechaza una receta que solicite alguna aún no disponible, antes de leer entradas. Incorporar `.xlsx` en Sprint 03 exige ampliar explícitamente el esquema de la entrada y su versión menor compatible, tras aprobar su política propia.

## 5. Política CSV inicial

- Límite por archivo: **10 MiB = 10.485.760 bytes**; medir bytes antes de decodificar. Un byte más se rechaza. Solo archivos `.csv` regulares. Cero bytes, archivo solo BOM y archivo sin encabezado se rechazan; encabezado válido sin datos se acepta con cero filas.
- Admitir UTF-8 sin BOM (`utf-8`) y UTF-8 con BOM inicial (`utf-8-sig`). El BOM se quita solo al inicio del primer encabezado y se registra. Una declaración que no coincida con la presencia de BOM, bytes inválidos, UTF-16, NUL o BOM en otra posición se rechaza; no usar reemplazo de caracteres.
- El delimitador es coma o punto y coma, declarado en la receta o confirmado antes de ejecutar mediante un parámetro explícito registrado en el manifiesto. Sin declaración o confirmación, se bloquea. Si otra interpretación parece plausible, se presenta la duda para confirmación; no se cambia silenciosamente. La confirmación no permite un separador fuera de los dos admitidos.
- CSV con encabezado obligatorio en primer registro. Encabezados vacíos, repetidos literalmente o repetidos tras quitar solo el BOM inicial se rechazan. No se recortan ni normalizan encabezados; espacios en nombres son significativos y deben concordar con el esquema. Se preserva orden de columnas y filas. Cada registro de datos tiene el mismo número de campos que el encabezado; no se rellenan ni truncan campos.
- Comillas dobles envuelven un campo completo; `""` representa una comilla interior. Delimitadores y saltos de línea dentro de campos entrecomillados son datos. Comillas fuera de esa gramática, campo sin cerrar, registros de ancho desigual y líneas vacías entre registros se rechazan con número de registro físico/lógico sin eco de valores. Se aceptan finales de línea LF y CRLF; un CR aislado fuera de comillas se rechaza. El salto final no crea una fila vacía.
- El importador conserva texto de celda; `""` y campo sin contenido cuentan como ausente, solo espacios se cuentan aparte y también como ausente para `no_vacio`. No se interpretan `NA`, `null`, fechas ni separadores decimales automáticamente. Duplicado exacto compara todos los textos de celda de una fila, en orden, antes de transformaciones; se cuenta cada ocurrencia después de la primera. Inferencia inicial informativa: sobre valores no vacíos, `entero`, `decimal` (punto ASCII), o `texto`; columna sin valores: `sin_datos`. No convierte datos ni toma decisiones de negocio.
- El diagnóstico falla con código estable y mensaje comprensible ante formato, tamaño, codificación, delimitador, encabezado o comillas inválidos. No deja entregables válidos parciales. Los detalles de celda quedan fuera de logs y errores ordinarios.

## 6. Contrato de carpetas y rutas

Cada encargo pertenece a un único cliente y usa un espacio independiente:

```text
clientes/
  <cliente>/
    <encargo>/
      originales/    archivos recibidos, preservados
      trabajo/        temporales de esa ejecución
      salidas/        entregables revisables
      evidencia/      manifiesto y controles sin valores sensibles
```

La estructura describe un contrato futuro; no presupone que esas carpetas existan. La raíz `clientes/` es una ruta local configurada por el operador; `cliente` y `encargo` son identificadores internos con la misma gramática de `id` de receta, nunca rutas libres. La combinación cliente/encargo debe ser única. `originales/` se lee y nunca se escribe; `trabajo/` recibe temporales por ejecución; `salidas/` recibe entregables finales; `evidencia/` recibe manifiesto y controles. Cada ejecución tiene un identificador propio y no reutiliza temporales o salidas anteriores sin una decisión explícita.

Las rutas declaradas son nombres base relativos, sin separadores, `.` ni `..`, prefijos de unidad, UNC, componentes vacíos o caracteres de control. Antes de abrir o crear se verifica que raíz, encargo y todos los componentes existentes sean directorios/archivos ordinarios según corresponda y no enlaces simbólicos, junctions ni otros enlaces de redirección. Se comprueba la ruta canónica del objetivo dentro de su subcarpeta permitida, se rechaza cualquier escape o cruce entre clientes y se vuelve a comprobar justo antes de usarla. Los originales se comparan por hash antes y después de la ejecución; una discrepancia bloquea la entrega. Estos controles reducen errores accidentales, pero no garantizan resistencia a cambios concurrentes de rutas ni reemplazan permisos del sistema.

## 7. Privacidad, auditoría y entrega

- Procesamiento local, sin cargas automáticas a Vyntrava, servicios de IA u otros servicios externos. Desarrollo y pruebas solo con datos sintéticos identificados como ficticios.
- Originales sin sobrescritura. La verificación independiente comprobará esta propiedad y la ausencia de mutación inesperada en diagnósticos.
- Registros ordinarios limitados a identificadores técnicos, versiones, estados y conteos, sin valores de celdas. Revisar también errores, trazas y nombres de archivo para evitar exposición accidental.
- Manifiesto con hash de entradas, versión de receta y motor, parámetros no sensibles, controles, resultados y lista de salidas; sin filas completas ni secretos.
- Antes de entregar: comprobar cliente y encargo correctos, controles obligatorios aprobados, correspondencia de salidas con el manifiesto, ausencia de archivos ajenos y revisión humana de resultados de negocio.
- Carpetas separadas y restricciones de rutas son controles iniciales; **no garantizan por sí solos la seguridad** frente a permisos del sistema, copias de seguridad, malware o errores operativos. Acceso, conservación, eliminación y cifrado deben definirse antes de procesar datos reales.

## 8. Pilotos sintéticos y oráculos manuales

Los siguientes datos son inventados y forman el oráculo documental. Cada línea representa una fila CSV; `␠` en la tabla significa un espacio literal al preparar el fixture. Se usan espacios de clientes ficticios separados; leer o escribir en el otro espacio debe rechazarse.

**Piloto A — clientes.** Encabezado `id,nombre,email,ciudad`; delimitador coma, UTF-8 sin BOM:

| Fila | id | nombre | email | ciudad |
|---:|---|---|---|---|
| 1 | C001 | Ana Ruiz | ana@example.test | Buenos Aires |
| 2 | C002 | Luis Paz | vacío | Córdoba |
| 3 | C002 | Luis Paz | vacío | Córdoba |
| 4 | C003 | `␠␠Mara Sol␠␠` | mara@example.test | `␠␠␠` |
| 5 | C004 | Jo Vale | no-es-email | Rosario |
| 6 | C005 | vacío | eve@example.test | Mendoza |

Antes de limpiar: **6 filas, 4 columnas, 1 duplicado exacto** (fila 3), **3 celdas vacías literales** (email 2 y 3, nombre 6), **1 celda solo espacios** (ciudad 4), **1 email de formato inválido** (fila 5). `no_vacio` marca además ciudad 4, por lo que son **4 incidencias de ausencia** antes de deduplicar. Con aprobación vinculada a hashes, `eliminar_duplicados_exactos` quita fila 3 y `recortar_espacios` en nombre y ciudad deja nombre 4 `Mara Sol` y ciudad 4 vacía. Resultado: **5 filas**, **3 ausencias** (email 2, ciudad 4, nombre 6), **1 email inválido**, **0 duplicados exactos**. No se imputan valores ni se corrige email; la entrega final queda bloqueada si esas validaciones son `bloquear`, o requiere revisión si son `advertir`.

**Piloto B — ventas.** Encabezado `id,fecha,producto,cantidad,precio`; delimitador punto y coma, UTF-8 BOM. Fechas son etiquetas ISO sintéticas, sin inferencia semántica en v1:

| Fila | id | fecha | producto | cantidad | precio |
|---:|---|---|---|---:|---:|
| 1 | V001 | 2026-01-05 | Libro | 2 | 10.00 |
| 2 | V002 | 2026-01-05 | Lápiz | 3 | 2.50 |
| 3 | V003 | 2026-01-06 | Libro | 1 | 10.00 |
| 4 | V003 | 2026-01-06 | Libro | 1 | 10.00 |
| 5 | V004 | 2026-01-06 | Libro | 0 | 10.00 |
| 6 | V005 | 2026-01-07 | Lápiz | 2 | 2.50 |

De **6 filas** iniciales, la fila 4 es duplicado exacto y la 5 incumple `entero_positivo` en cantidad. Tras aprobación de deduplicación quedan **5 filas**; el análisis excluye la 5 y cuenta **4 ventas válidas**, **8 unidades**, **42.50** de importe (`20 + 7.50 + 10 + 5`), **2 productos**. Por producto: Libro **30.00 y 3 unidades**; Lápiz **12.50 y 5 unidades**. Por fecha: 2026-01-05 **27.50**, 2026-01-06 **10.00**, 2026-01-07 **5.00**. El gráfico futuro debe representar estos totales por fecha. Si una validación bloqueante falla, estos indicadores pueden existir como borrador revisable pero no como entrega aprobada. El mismo motor y contrato de receta se usa en A y B; visualización y cierre del piloto B corresponden a Sprint 03.

## 9. Primer hito y aceptación

El primer corte vertical conserva el valor del plan anterior: cargar CSV sintético según la política anterior, informar filas y columnas, duplicados exactos, ausentes, tipos inferidos y celdas solo con espacios; generar resumen estructurado reproducible y preservar el original. El límite de 10 MiB es inicial, sujeto a validación comercial.

La aceptación exige pruebas automatizadas con resultados conocidos, errores comprensibles para archivos vacíos, malformados, demasiado grandes o no admitidos, controles de rutas y aislamiento, y evidencia ADEL de ejecución y revisión independiente. Un sprint no se acredita solo por escribir código.

## 10. Desarrollo y decisiones pendientes

Aplicar especificación primero y TDD **RED → GREEN → REFACTOR** por comportamiento. Revisar cada sprint contra criterios explícitos y registrar evidencia ADEL. No publicar datos de clientes, secretos ni afirmaciones comerciales sin verificar.

Siguen pendientes de decisiones posteriores: política `.xlsx` de Sprint 03; tamaño máximo comercial; formato de informes y gráficos; ubicación y permisos operativos de la raíz de clientes; conservación, eliminación, cifrado y copias de seguridad; y umbrales que justifiquen Streamlit. La política CSV y el contrato JSON v1 de este documento son **propuestas para aprobación del fundador**, aún no resultados implementados. Antes de usar datos reales se necesita una política operativa y contractual específica.
