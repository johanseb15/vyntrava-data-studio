# Laboratorio sintético local — Sprint 05

Ejecutar desde la raíz del repositorio con Python del entorno existente. Los archivos de `examples/piloto_a` y `examples/piloto_b` reproducen `SPEC.md` §8. Cada ejecución crea un encargo nuevo; no reutilizar un `--job`. La clave de abajo es ficticia y se entrega solo al proceso. El programa firma el comprobante HMAC ligado al hash de la receta y del original, y `run_recipe` lo valida antes de deduplicar.

```powershell
$env:VYNTRAVA_SYNTHETIC_APPROVAL_KEY = 'clave-ficticia-solo-para-pruebas'
.venv/Scripts/python.exe -m vyntrava_data_studio.synthetic_lab run --pilot a --root workspaces/s05_synthetic --job ejemplo_a_01 --kind first
.venv/Scripts/python.exe -m vyntrava_data_studio.synthetic_lab run --pilot b --root workspaces/s05_synthetic --job ejemplo_b_01 --kind first
.venv/Scripts/python.exe -m vyntrava_data_studio.synthetic_lab run --pilot a --root workspaces/s05_synthetic --job ejemplo_a_02 --kind repeat
.venv/Scripts/python.exe -m vyntrava_data_studio.synthetic_lab run --pilot b --root workspaces/s05_synthetic --job ejemplo_b_02 --kind repeat
Remove-Item Env:VYNTRAVA_SYNTHETIC_APPROVAL_KEY
```

Si se omite `--job` al ejecutar, el programa genera uno único y lo imprime. `--kind` distingue la primera ejecución de la repetición; no combina sus tiempos. Para verificar después, sin la clave:

```powershell
.venv/Scripts/python.exe -m vyntrava_data_studio.synthetic_lab verify --pilot a --root workspaces/s05_synthetic --job ejemplo_a_01
.venv/Scripts/python.exe -m vyntrava_data_studio.synthetic_lab verify --pilot b --root workspaces/s05_synthetic --job ejemplo_b_01
```

El JSON impreso por `run` muestra estado, verificaciones, checks del oráculo, hashes, tiempos y rutas absolutas. `verify` exige el registro de medición del piloto, cliente y encargo solicitados y llama al verificador de Sprint 04. Un paquete de otro piloto o un registro ausente devuelve error. La verificación de paquete acredita integridad local, no aprobación del resultado.

En la ejecución real de ADEL-S05-002, las entradas copiadas están en `workspaces/s05_synthetic/piloto_a/s05_a_final_first/originales/clientes.csv` y `workspaces/s05_synthetic/piloto_b/s05_b_final_first/originales/ventas.csv`; salidas en los respectivos `salidas/`, manifiestos en `evidencia/manifiesto.json`, y mediciones en `workspaces/s05_synthetic/mediciones/piloto_a/s05_a_final_first.json` y `workspaces/s05_synthetic/mediciones/piloto_b/s05_b_final_first.json`. Hay además encargos `s05_a_final_repeat` y `s05_b_final_repeat` en las mismas estructuras. `workspaces/` está ignorado por Git. Todas las mediciones quedan fuera de `originales/`.

El operador debe registrar sus minutos reales de preparación y revisión humana en `operator_durations_minutes` del JSON de medición; `null` significa pendiente. No inferirlos de `timing_seconds`, que mide únicamente ejecución y verificación con reloj monotónico. El estado `revision_requerida` exige revisión humana del CSV limpio, los importes y el gráfico antes de cualquier entrega. Contrastar Piloto A con 6 filas, 1 duplicado, 3 vacíos literales, 1 celda solo espacios, y después 5 filas, 3 ausencias y 1 email inválido. Contrastar Piloto B con 6 filas, 1 duplicado, 4 ventas incluidas, 1 excluida, 8 unidades, total Decimal 42.50, fechas 27.50, 10.00 y 5.00, y productos Libro 30.00 y Lápiz 12.50.

No usar datos reales. Si una ejecución se interrumpe o falla tras crear el encargo, conservarlo para inspección y ejecutar de nuevo con otro `--job`. Los tiempos observados son de estas cuatro ejecuciones sintéticas y no representan un benchmark comercial.
