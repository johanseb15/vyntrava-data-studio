"""Generate one local synthetic XLSX demo with the integrated recipe engine."""

import csv
import hashlib
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

from test_xlsx_consolidation import _setup  # noqa: E402
from vyntrava_data_studio.package_verifier import verify_recipe_package  # noqa: E402
from vyntrava_data_studio.sprint02 import run_recipe  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("uso: python examples/adel_data_demo_001.py RUTA_NUEVA")
    package = Path(sys.argv[1]).resolve()
    if package.exists():
        raise SystemExit("la ruta del paquete ya existe; elegí una ruta nueva")

    root, _job, recipe, first, second = _setup(package)
    result = run_recipe(recipe, root, "cliente_demo", "encargo_demo")
    checked = verify_recipe_package(recipe, root, "cliente_demo", "encargo_demo")
    report = json.loads(result.outputs["resumen"].read_text(encoding="utf-8"))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    incidences = report["validaciones"]["cantidad"]["incidencias"]
    with result.outputs["tabla"].open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = [
        {"id": "001", "producto": "Libro", "cantidad": "2"},
        {"id": "002", "producto": "Lápiz", "cantidad": "3"},
        {"id": "003", "producto": "Libro", "cantidad": "1"},
        {"id": "004", "producto": "Cuaderno", "cantidad": "0"},
    ]
    if (rows != expected or result.status != "revision_requerida"
            or report["estado"] != result.status or manifest["estado"] != result.status
            or incidences != 1 or not checked.ok):
        raise RuntimeError("el paquete no cumple los criterios de la demo")

    (package / "DATOS_SINTETICOS.txt").write_text(
        "Datos ficticios. La fila 004 tiene cantidad 0 para mostrar una alerta.\n"
        "Estado revision_requerida: una persona debe revisar antes de cualquier entrega.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "datos": "SINTETICOS", "estado": result.status, "filas": len(rows),
        "incidencias": incidences, "verificacion_independiente": checked.ok,
        "paquete": str(package), "csv": str(result.outputs["tabla"]),
        "resumen": str(result.outputs["resumen"]),
        "manifiesto": str(result.manifest_path),
        "sha256_entradas": {name: hashlib.sha256(path.read_bytes()).hexdigest()
                            for name, path in (("lote_a", first), ("lote_b", second))},
        "sha256_salidas": {name: manifest["salidas"][name]["sha256"]
                           for name in ("tabla", "resumen")},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
