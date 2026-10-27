# ADEL-S01-005-FIX02 — Entorno limpio para Sprint 01

**Alcance:** resolver el bloqueo de instalación registrado en FIX01 y ejecutar la suite de Sprint 01 con dependencias nuevas. Operador: Codex (implementador). No constituye la confirmación de un revisor independiente.

## Instalación

El intento anterior de `uv sync --offline --locked` usaba un caché global inaccesible. En FIX02 se configuró `UV_CACHE_DIR` dentro de `.pytest_tmp/`, se creó `.pytest_tmp/fix02_clean_env` con `uv venv` y se dirigió `uv sync --locked --active` a ese entorno mediante `VIRTUAL_ENV`. El intento sin conexión confirmó que faltaban paquetes en el caché nuevo. El intento con red encontró un certificado no reconocido; `uv sync --locked --active --system-certs` completó la instalación desde `uv.lock` con los certificados del sistema.

Comandos ejecutados desde la raíz del proyecto en PowerShell:

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.pytest_tmp/fix02_uv_cache')
uv venv .pytest_tmp/fix02_clean_env
$env:VIRTUAL_ENV = (Resolve-Path '.pytest_tmp/fix02_clean_env').Path
uv sync --locked --active --system-certs
$env:PYTHONPATH = (Resolve-Path 'src').Path
.\.pytest_tmp\fix02_clean_env\Scripts\python.exe -m pytest -q -rs --basetemp=.pytest_tmp/fix02_clean_suite
```

`uv` informó `Installed 7 packages`: `colorama 0.4.6`, `iniconfig 2.3.1`, `packaging 26.3`, `pluggy 1.7.0`, `pygments 2.21.0`, `pytest 9.1.1` y `vyntrava-data-studio 0.1.0` desde el proyecto local. El intérprete nuevo informó `pytest 9.1.1`.

## Resultado

La suite terminó con **95 aprobadas y 2 omitidas en 4,01 s**. Ambas omisiones son las pruebas de symlink en `tests/test_workspace.py:149` y `:162` por falta de permiso del sistema; las pruebas de junction se ejecutaron. `git diff --check` no informó errores de formato. No hubo cambios de código de producción ni de pruebas en FIX02.

Los hashes SHA-256 de las cinco suites coinciden con los registrados en FIX01: importador `30037970ece18e318584912d2090cfdd73ceabdfd2b9265ef90858ba0a4597aa5`, diagnóstico `1943c3904d6c8e10fcb93ceae1e8772a7e77cb6ddff5add5f2f23b42a35c0f6a`, corte vertical `cb4eb81a5b4697c5b49be7de4f03ac59db5106a85c72d7816132862139967032`, espacio `a260da99c0b7f99c0ecd4d4bf1b8b636a9f9bb1fc231d716edbacf31eab1405a` y recetas `09d8d559c88599ab234224f0ac799db33b8ba3f12cfea5e020303eddd35c5ab6`.

## Decisión y pendiente

El bloqueo técnico de instalación en entorno nuevo queda resuelto en este equipo. La prueba se ejecutó contra el árbol de trabajo actual, con el paquete local instalado de forma editable. FIX01 ya registra la revisión manual independiente del oráculo, las rutas y la privacidad; el revisor aún debe repetir la suite desde un entorno limpio autorizado y confirmar formalmente el cierre de 01.6. Hasta entonces, Sprint 01 no se acredita como cerrado.
