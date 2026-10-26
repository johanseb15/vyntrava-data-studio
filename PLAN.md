# Vyntrava Data Studio — Plan propuesto

> **Para la ejecución futura:** usar Superpowers `executing-plans` o `subagent-driven-development` tarea por tarea. Las casillas marcan trabajo pendiente; este documento no ejecuta código.

**Goal:** Motor Python local con importación CSV y diagnóstico verificables, ampliado por recetas y pilotos sintéticos.

**Architecture:** El espacio de encargo limita rutas. Un validador JSON acepta solo operaciones declarativas permitidas; importación, diagnóstico, transformaciones y análisis producen resultados estructurados independientes de Streamlit.

**Tech Stack:** Python 3.12, pandas, NumPy, pytest, uv y Git previstos.

**Spec:** [SPEC.md](SPEC.md)

**Global Constraints:** Solo datos sintéticos; CSV hasta 10.485.760 bytes; UTF-8 o UTF-8 BOM; delimitador `,` o `;` declarado o confirmado; originales preservados; ninguna receta ejecuta Python arbitrario; sin servicios pagos.

**Review Focus:** Límite de tamaño; BOM y encabezado; comillas y finales de línea; enlaces y cruces entre encargos; filtración de valores en errores. Las pruebas concretas figuran en Sprint 01.

---

**Proyecto:** VYNTRAVA-DATA-001  
**Método:** ADEL + Superpowers 7.0.1 + TDD RED → GREEN → REFACTOR  
**Estado:** Sprint 00 — Contrato técnico documentado; ejecución pendiente de aprobación  
**Arquitectura:** Motor Python local por recetas, independiente de la interfaz  
**Especificación:** [SPEC.md](SPEC.md)

## 1. Decisiones aprobadas y enfoque

Data Studio es una herramienta interna para encargos freelance de múltiples clientes. Su unidad de trabajo es un encargo aislado con entradas, receta versionada, ejecución controlada y entregables reproducibles. Se construye un motor común, sin software a medida por pedido. CSV va primero; Excel es prioridad comercial temprana. Streamlit sigue al motor y a los pilotos. No hay servicios pagos obligatorios ni desarrollo con datos reales.

Las tareas repetitivas usarán recetas y herramientas locales. Codex apoyará implementación compleja, pruebas y revisión de capacidades compartidas con fixtures sintéticos. El contrato JSON v1 y la política CSV detallados en SPEC.md son propuestas de cierre para aprobar; no son capacidades implementadas.

## 2. Unidades de trabajo y estructura prevista

Se conserva Python 3.12, pandas, NumPy, pytest, uv y Git como base técnica. El motor estará separado de la interfaz. Esta estructura es **propuesta, no creada**:

```text
DataStudio/
├── SPEC.md
├── PLAN.md
├── README.md
├── pyproject.toml
├── src/vyntrava_data_studio/
│   ├── importer.py       lectura y política de formatos
│   ├── workspace.py      límites del encargo y rutas
│   ├── recipes.py        validación y versión de recetas
│   ├── diagnostics.py    perfil y calidad de entradas
│   ├── transforms.py     reglas deterministas
│   ├── analysis.py       indicadores y datos para gráficos
│   └── delivery.py       salidas y manifiesto
├── app/main.py           interfaz posterior al motor
├── tests/                pruebas con fixtures sintéticos
├── examples/             dos pilotos ficticios y recetas
└── reports/              evidencia ADEL sin valores sensibles
```

Los nombres de módulos son la propuesta de trabajo. Para Sprint 01 se fijan las interfaces en la sección 4; el contrato de receta es el de SPEC.md §4. No se crean estas carpetas en Sprint 00.

## 3. Sprints, ponderación y criterios de salida

La ponderación total mide **avance técnico verificado**. El valor comercial se mide aparte mediante pilotos y, más adelante, uso operativo; no se infiere de ese porcentaje.

| Sprint | Peso | Entrega y criterios de aceptación |
|---|---:|---|
| 00 — Contratos y preparación | 10% | Especificación, formato de receta y política inicial de espacios y CSV aprobados; resultados esperados de ambos pilotos documentados; plan detallado revisable. Este documento por sí solo no acredita el 10%. |
| 01 — CSV, espacio y diagnóstico | 20% | Importar CSV hasta 10 MiB; rechazar exceso, vacíos, malformados o no admitidos; conservar original, columnas y orden; diagnosticar filas, columnas, duplicados exactos, ausentes, tipos inferidos y celdas solo con espacios; rechazar rutas fuera del encargo; producir resumen estructurado. |
| 02 — Recetas, limpieza y validación | 25% | Ejecutar reglas deterministas versionadas; señalar cambios ambiguos o destructivos para aprobación; bloquear salidas inválidas; repetir resultados con iguales entradas y parámetros; completar el piloto de limpieza de clientes. |
| 03 — Excel, análisis y gráficos | 20% | Aprobar una política propia de `.xlsx` antes de implementarlo; calcular estadísticas e indicadores con valores esperados; exportar al menos un gráfico útil; completar el piloto de ventas con el mismo motor. |
| 04 — Entregables y revisión | 15% | Generar datos, validaciones, informe y manifiesto según receta; verificar hashes de entradas, versiones y lista de salidas; revisión independiente del paquete y prueba de ausencia de cruces entre clientes ficticios. |
| 05 — Operación local | 10% | Documentar ejecución repetitiva por receta; medir tiempo y reutilización de ambos pilotos; decidir con evidencia si Streamlit reduce trabajo operativo e implementarlo solo tras esa decisión y su aceptación. |
| **Total** | **100%** | El peso se acredita únicamente al verificar la salida del sprint. |

La ponderación conserva el total de 100% del plan anterior y mantiene sus ejes de importación, limpieza, análisis y exportación. La publicación pública deja de ser un hito del producto interno.

## 4. Ciclo TDD y evidencia por unidad

Para cada comportamiento: (1) escribir prueba con fixture sintético y resultado esperado; (2) ejecutar y registrar **RED** por ausencia del comportamiento; (3) implementar lo mínimo y registrar **GREEN**; (4) mejorar la estructura sin cambiar resultados y volver a probar (**REFACTOR**). Cada sprint cierra con pruebas pertinentes, revisión independiente y evidencia ADEL de criterios, comandos, resultados y limitaciones, sin valores sensibles.

Casos obligatorios de revisión: límite exacto de 10 MiB y archivo que lo supera; archivos vacíos, malformados y codificación no admitida; duplicados y ausentes con resultados manuales; celdas solo con espacios; columnas inesperadas; rutas `..`, absolutas y enlaces fuera del espacio; no sobrescritura del original; temporales y salidas aislados; ausencia de filas y secretos en registros y manifiesto. Las pruebas de Excel se concretarán al aprobar su política de hojas y formatos.

### Sprint 01 — mapa de archivos e interfaces

Este plan implementa SPEC.md §§4–6 y el primer corte de §9. Solo se emplean fixtures sintéticos. Los archivos listados son **futuros**, no existen por efecto de este documento:

| Responsabilidad | Archivo futuro | Interfaz propuesta |
|---|---|---|
| Validación estática JSON v1 | `src/vyntrava_data_studio/recipes.py`, `tests/test_recipes.py` | `load_recipe(path: Path) -> Recipe` o `RecipeError(code, location)` |
| Rutas por encargo | `src/vyntrava_data_studio/workspace.py`, `tests/test_workspace.py` | `resolve_input(root, client, job, basename) -> Path`; `resolve_output(root, client, job, basename, kind) -> Path` o `WorkspaceError(code)` |
| CSV estricto | `src/vyntrava_data_studio/importer.py`, `tests/test_importer.py` | `read_csv(path, encoding, delimiter) -> CsvTable` o `CsvError(code, record_number)`; `CsvTable` conserva encabezados, filas de texto, BOM y delimitador |
| Diagnóstico | `src/vyntrava_data_studio/diagnostics.py`, `tests/test_diagnostics.py` | `diagnose(table: CsvTable) -> DiagnosticSummary` |
| Corte vertical | `src/vyntrava_data_studio/delivery.py`, `tests/test_vertical_slice.py` | `run_diagnostic(recipe_path, root, client, job, confirmed_delimiters: dict[str, str] | None = None) -> DiagnosticRun` |

**Foco de revisión:** CSV de tamaño exacto y un byte más; solo BOM y encabezado sin datos; comillas y saltos dentro de campos frente a CR aislado; symlink/junction y cruce de encargo; errores que puedan revelar celdas. Los cinco casos tienen pruebas en las tareas siguientes.

### Tarea 01.1 — Receta estática

- [ ] **RED:** en `tests/test_recipes.py`, probar ejemplo de SPEC.md §4, clave y parámetro extra, clave duplicada, versión mayor 2, menor futura, operación desconocida y referencia inexistente. Ejecutar `pytest tests/test_recipes.py -v`; guardar cada fallo esperado.
- [ ] **GREEN:** implementar `load_recipe` con las diez claves obligatorias, allowlist y validación de tipos y referencias antes de abrir datos; repetir comando y registrar `PASS`.
- [ ] **REFACTOR:** separar validación de forma, versión y operaciones; repetir la suite sin cambiar códigos de error.
- [ ] **Aceptación:** ninguna operación desconocida se omite o ejecuta; los errores indican código y ubicación JSON, sin valores de celdas.

### Tarea 01.2 — Espacio y rutas

- [ ] **RED:** en `tests/test_workspace.py`, probar nombre base válido y rechazo de `..`, ruta absoluta, UNC, unidad, separador, symlink/junction, acceso desde cliente A al B y salida hacia `originales/`. Ejecutar `pytest tests/test_workspace.py -v`; guardar fallos.
- [ ] **GREEN:** implementar `resolve_input` y `resolve_output`; comprobar identificadores, componentes existentes, ruta canónica y destino permitido antes de usar. Repetir pruebas y registrar `PASS`.
- [ ] **REFACTOR:** centralizar comprobación de componentes; repetir suite y documentar el límite ante reemplazo concurrente de rutas.
- [ ] **Aceptación:** el original nunca se abre para escritura y un cruce de encargo se rechaza antes de leer o crear archivos.

### Tarea 01.3 — CSV estricto

- [ ] **RED:** en `tests/test_importer.py`, probar coma, punto y coma, BOM correcto e incompatible, UTF-8 inválido, delimitador ausente, 10.485.760 y 10.485.761 bytes, cero bytes, solo BOM y encabezado sin filas. Ejecutar `pytest tests/test_importer.py -v`; guardar fallos.
- [ ] **RED:** añadir campos entrecomillados con delimitador, `""`, salto LF interior, CRLF, CR aislado, comillas sin cerrar, encabezado vacío o duplicado, ancho desigual y línea vacía intermedia. Guardar fallos antes de completar la implementación.
- [ ] **GREEN:** implementar `read_csv` según SPEC.md §5, sin autodetección ni sustitución de caracteres; repetir suite y registrar `PASS`.
- [ ] **REFACTOR:** separar límite/decodificación de análisis CSV; repetir suite.
- [ ] **Aceptación:** preservar texto, encabezados y orden; un fallo no devuelve tabla parcial ni vuelca datos de celda en el error.

### Tarea 01.4 — Diagnóstico

- [ ] **RED:** en `tests/test_diagnostics.py`, usar Piloto A de SPEC.md §8 y afirmar 6 filas, 4 columnas, 1 duplicado, 3 vacíos literales, 1 celda solo espacios; probar también columna sin datos e inferencia `entero`, `decimal`, `texto`. Ejecutar `pytest tests/test_diagnostics.py -v`; guardar fallos.
- [ ] **GREEN:** implementar `diagnose` sin mutar `CsvTable`; repetir suite y registrar `PASS`.
- [ ] **REFACTOR:** separar conteos e inferencia; repetir suite.
- [ ] **Aceptación:** dos ejecuciones producen el mismo resumen y este no contiene valores de celda.

### Tarea 01.5 — Corte vertical

- [ ] **RED:** en `tests/test_vertical_slice.py`, ejecutar Piloto A; afirmar resumen, hash SHA-256 del original antes/después igual y bytes idénticos. Probar ruta cruzada y CSV fallido sin entrega marcada válida. Ejecutar `pytest tests/test_vertical_slice.py -v`; guardar fallos.
- [ ] **GREEN:** implementar `run_diagnostic` usando 01.1–01.4; resumen en `salidas/` y metadatos sin celdas en `evidencia/`; repetir suite.
- [ ] **REFACTOR:** aislar composición y serialización del resumen; repetir suite.
- [ ] **Aceptación:** original inalterado, resumen reproducible, rutas restringidas y sin paquete válido parcial. Limpieza, análisis y entregables comerciales quedan para Sprints 02–04.

### Tarea 01.6 — Cierre ADEL independiente

- [ ] Una persona o agente distinto del implementador recibe SPEC.md, hashes de fixtures, comandos y salidas RED/GREEN/REFACTOR; ejecuta las suites de Sprint 01 desde un entorno limpio autorizado.
- [ ] Recalcula el oráculo del Piloto A a mano; revisa rechazo de ruta cruzada, original intacto y ausencia de filas o nombres sensibles en errores y evidencia. Registra hallazgos con severidad, responsable y estado.
- [ ] Se corrigen hallazgos bloqueantes, se repiten las pruebas afectadas y el revisor confirma el cierre. Sin revisión aceptada no se acredita el 20% de Sprint 01.

**Evidencia ADEL por tarea:** requisito, prueba, hash del fixture, comando y salida RED por el comportamiento previsto, comando y salida GREEN, repetición REFACTOR, hashes del original, incidencias, responsable y decisión independiente. Son comandos de implementación futura; ninguno se ejecuta en Sprint 00.

## 5. Pilotos sintéticos

| Piloto | Entrada y propósito | Entregables y contraste independiente |
|---|---|---|
| Limpieza de clientes | Seis filas y cuatro columnas de SPEC.md §8; un duplicado exacto, tres vacíos literales, una celda solo espacios y un email inválido. | Tras aprobación de deduplicación: cinco filas, tres ausencias, cero duplicados y un email inválido; no hay imputación. Registrar si la validación bloquea o requiere revisión. |
| Análisis de ventas | Seis filas de SPEC.md §8, con delimitador `;`, BOM, un duplicado y cantidad cero inválida; prueba posterior `.xlsx` según política aprobada. | Tras deduplicación aprobada, cuatro ventas válidas, ocho unidades y 42.50; Libro 30.00, Lápiz 12.50; gráfico por fecha 27.50, 10.00 y 5.00. |

Los pilotos usan clientes y encargos ficticios separados. Una prueba de integración intenta leer o escribir entre ambos espacios y debe recibir un rechazo claro. Otra persona revisa que el paquete de cada piloto contiene solo sus propias salidas y coincide con su manifiesto.

## 6. Métricas y decisión comercial

Antes de cada ejecución, anotar id de piloto, versión/hash de receta, versión del motor, hash de entrada sintética, operador y revisor. Registrar marcas de tiempo locales para inicio de preparación, primera ejecución, salida revisable y aprobación; calcular minutos de preparación, de corrección y totales hasta aprobación. Separar tiempo de adaptación de receta, código nuevo y revisión. Una repetición con la misma receta/entrada se mide aparte, nunca se mezcla con la primera ejecución. No omitir intentos fallidos.

Medir **reutilización** como `encargos terminados sin código nuevo / encargos terminados`, junto con recuento de reglas ya existentes usadas y reglas nuevas requeridas; con solo dos pilotos informar también numerador y denominador, sin extrapolar. Medir **calidad** como `controles obligatorios aprobados / controles obligatorios aplicables`, número de discrepancias del revisor por severidad, correcciones tras primera salida revisable y concordancia de cada cifra con el oráculo manual. Registrar `no aplicable` cuando corresponda, nunca tratarlo como aprobado.

La revisión es independiente si el revisor no implementó la tarea revisada y recibe datos sintéticos, oráculos y criterios antes de ver la salida. Debe recalcular los importes del Piloto B por fila y grupo, comprobar conteos del A, hashes de originales, separación de espacios y correspondencia de cada salida con el manifiesto. Registra discrepancias y solicita corrección; el mismo revisor verifica la corrección. Si no hay una segunda persona disponible, una revisión posterior con contexto separado se etiqueta **revisión diferida**, no independiente, y el criterio queda pendiente.

Los pilotos comprueban viabilidad técnica y permiten una línea base de tiempo; **no validan por sí solos ahorro, margen ni demanda comercial**. Los objetivos numéricos de tiempo, reutilización y calidad se fijarán después de esa línea base y de encargos representativos autorizados. El avance técnico verificado se informa separado de las métricas comerciales.

## 7. Riesgos, límites y decisiones pendientes

- **Aislamiento:** rutas comprobadas y carpetas separadas reducen cruces accidentales, pero no sustituyen permisos del sistema, cifrado, control de acceso o copias de seguridad. Probar rutas adversas y revisar cada paquete.
- **Reproducibilidad:** cambios del motor, dependencias o interpretación de formatos pueden alterar resultados. Fijar versiones pertinentes en el manifiesto y repetir los pilotos.
- **Calidad de negocio:** una salida técnicamente válida puede responder mal a la pregunta del cliente. Comparar indicadores e informe con resultados esperados mediante revisión independiente.
- **Escala:** el límite CSV de 10 MiB procede del plan anterior; su suficiencia comercial no está validada.
- **Contrato propuesto para aprobación en este cierre:** JSON v1, compatibilidad y allowlist, política CSV y carpetas de SPEC.md §§4–6. Hasta aprobación son decisiones documentadas, no capacidades verificadas.
- **Pendiente posterior:** política `.xlsx` de Sprint 03; permisos, conservación, eliminación, cifrado y copias de seguridad; suficiencia comercial del límite; umbrales para Streamlit; política para datos reales.

## 8. Definición de terminado

Un sprint termina cuando sus criterios están verificados, pasan sus pruebas pertinentes, la evidencia ADEL está registrada, una revisión independiente ha examinado resultados y límites, y el responsable acepta la entrega. Esta consolidación documental no acredita por sí sola ningún sprint de implementación ni autoriza procesar datos reales.
