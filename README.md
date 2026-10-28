<div align="center">

<img src="assets/vyntrava-data-banner.svg" alt="Vyntrava Data Studio — CSV y Excel, recetas deterministas, verificación e informes" width="100%" />

# Vyntrava Data Studio

**From messy spreadsheets to reproducible, verifiable data deliverables.**

Motor Python local para **importar, diagnosticar, limpiar, validar, analizar y entregar datos** usando recetas JSON versionadas, controles de integridad y espacios de trabajo aislados.

![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![CSV + XLSX](https://img.shields.io/badge/Inputs-CSV%20%2B%20XLSX-0D9488)
![Local-first](https://img.shields.io/badge/Architecture-Local--first-14532D)
![Tests](https://img.shields.io/badge/Latest%20verified-182%20passed%20%7C%203%20skipped-2563EB)
![MVP](https://img.shields.io/badge/Status-Technical%20MVP%20%28with%20limitations%29-F59E0B)

</div>

## Why Vyntrava Data Studio?

Muchos trabajos de datos terminan siendo una colección de scripts difíciles de repetir. **Vyntrava Data Studio** separa las reglas de procesamiento de los archivos originales y registra qué receta y entradas generaron cada entrega.

- **CSV y Excel `.xlsx`** con políticas de importación explícitas y controles preventivos.
- **Recetas JSON versionadas** para ejecutar transformaciones y validaciones deterministas.
- **Diagnóstico de calidad:** duplicados exactos, valores ausentes, espacios, estructura y tipos inferidos.
- **Aprobación de operaciones destructivas:** deduplicación condicionada a aprobación HMAC vinculada a receta y entradas.
- **Análisis y gráficos:** conteos, sumas de productos con `Decimal`, agrupaciones y PNG.
- **Entregas auditables:** archivos de salida, resumen, manifiesto y hashes SHA-256.
- **Verificador de paquetes de solo lectura**, con rechazo de archivos alterados, faltantes, extras o inconsistentes.
- **Trabajo aislado por cliente y encargo**; originales preservados.

> [!IMPORTANT]
> Este repositorio contiene un **MVP técnico validado con datos sintéticos**, no una plataforma SaaS ni un producto aprobado para procesar datos reales de clientes. Los controles de integridad no constituyen validación semántica ni garantía de autenticidad criptográfica. Las entregas con `revision_requerida` necesitan revisión humana.

## How it works

<div align="center">
<img src="assets/workflow.svg" width="100%" alt="Flujo del motor desde archivos originales y receta hasta salidas y verificación" />
</div>

## Two reproducible demos

Los ejemplos están en [`examples/piloto_a`](examples/piloto_a) y [`examples/piloto_b`](examples/piloto_b). **Son datos ficticios**; la ejecución crea encargos nuevos y conserva intactos los archivos de entrada.

| | Pilot A · Customer data | Pilot B · Sales analysis |
|---|---|---|
| Input | 6 filas de clientes ficticios | 6 filas de ventas ficticias |
| Processing | Diagnóstico, deduplicación aprobada, recorte de espacios, validaciones | Deduplicación aprobada, validación de cantidad, análisis y gráfico |
| Result | 5 filas finales, 3 ausencias, 1 email inválido | 4 ventas incluidas, 1 excluida, 8 unidades, **42.50** |
| Output | CSV limpio + JSON + manifiesto | CSV + JSON + PNG + manifiesto |
| Final state | `revision_requerida` | `revision_requerida` |

<div align="center">
<img src="assets/pilots.svg" width="100%" alt="Resultados esperados de los dos pilotos sintéticos, incluidos totales de ventas por fecha" />
</div>

## Quick start — Windows PowerShell

**Requirements:** Python 3.12 y [`uv`](https://docs.astral.sh/uv/). Ejecutá desde la raíz del repositorio.

```powershell
uv sync --frozen
$env:VYNTRAVA_SYNTHETIC_APPROVAL_KEY = 'clave-ficticia-solo-para-demo'
$root = Join-Path $env:TEMP 'vyntrava-data-demo'

# Two synthetic jobs, with unique names for each new run
uv run --no-sync python -m vyntrava_data_studio.synthetic_lab run --pilot a --root $root --kind first
uv run --no-sync python -m vyntrava_data_studio.synthetic_lab run --pilot b --root $root --kind first

Remove-Item Env:VYNTRAVA_SYNTHETIC_APPROVAL_KEY
```

El comando muestra el **ID del encargo**, las rutas de salida, los checks del oráculo, el estado y los tiempos medidos. Para verificar posteriormente un encargo generado:

```powershell
uv run --no-sync python -m vyntrava_data_studio.synthetic_lab verify --pilot b --root $root --job <ID_DE_ENCARGO>
```

Sustituí `<ID_DE_ENCARGO>` por el ID generado; no pegues los símbolos `< >` literalmente. Los comandos de demo requieren un entorno correctamente instalado y acceso a las dependencias; si `uv sync --frozen` no puede recuperar paquetes en modo offline, consultá la documentación operativa.

> [!NOTE]
> La clave anterior es **exclusivamente para datos sintéticos**. No usarla para operaciones reales. El comando `run` produce paquetes con `revision_requerida`; la verificación de integridad no levanta esa condición.

## Project layout

```text
src/vyntrava_data_studio/  # import, diagnosis, recipes, transforms, charts
                           # deliveries, package verification and demo CLI
examples/piloto_a/         # synthetic customers + recipe
examples/piloto_b/         # synthetic sales + recipe
docs/                      # operator guides and verification contract
tests/                     # automated regression tests
reports/                   # ADEL implementation and acceptance evidence
SPEC.md                    # technical contract
PLAN.md                    # sprint plan and acceptance criteria
```

## Test and verify

```powershell
$testTemp = Join-Path $env:TEMP ('vyntrava-pytest-' + [guid]::NewGuid().ToString('N'))
uv run --no-sync python -m pytest -q -rs -p no:cacheprovider --basetemp "$testTemp"
```

Última regresión local registrada al cerrar el alcance técnico: **182 passed, 3 skipped**. Las tres omisiones correspondieron a controles de symlinks no ejecutables en el entorno Windows utilizado. Este resultado es evidencia histórica, **no un badge de CI en tiempo real**.

## Engineering approach

Se desarrolló bajo **ADEL (Adaptive Development Engineering Lifecycle)**: preservación de arquitectura existente, especificaciones y aceptación explícitas, pruebas **RED → GREEN → REFACTOR**, controles de rutas y permisos, trazabilidad y revisión de resultados. El alcance técnico original de los sprints 00–05 quedó **aceptado con reservas**.

**Known limitations:** revisión humana y tiempos operativos manuales diferidos; publicación de múltiples archivos no atómica; riesgos residuales de concurrencia y permisos; el verificador no firma manifiestos ni certifica corrección comercial; políticas para uso con datos reales pendientes.

## Documentation

- [Technical specification](SPEC.md)
- [Implementation plan and acceptance criteria](PLAN.md)
- [Sprint 05 — running the demo](docs/OPERACION_S05.md)
- [Sprint 04 — verifying result packages](docs/VERIFICACION_S04.md)
- [Sprint 03 — operations](docs/OPERACION_S03.md)
- [Sprint 03 — XLSX policy](docs/OPERACION_XLSX_V1.md)

---

<div align="center">

**Built by Vyntrava Technologies** · *Data workflows with reproducibility, traceability and practical safeguards.*

**Technical MVP · Synthetic demonstrations only**

</div>
