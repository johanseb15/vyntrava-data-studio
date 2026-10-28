"""Local operator wrapper for the two fictional SPEC section 8 pilots."""

import argparse
from decimal import Decimal
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import time
import uuid

from .package_verifier import verify_recipe_package
from .recipes import load_recipe
from .sprint02 import run_recipe


_PILOTS = {"a": ("piloto_a", "clientes.csv"), "b": ("piloto_b", "ventas.csv")}
_ID = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paths(pilot: str, root: Path, job: str, examples: Path):
    if pilot not in _PILOTS or not isinstance(job, str) or not _ID.fullmatch(job):
        raise ValueError("invalid_pilot_or_job")
    client, filename = _PILOTS[pilot]
    recipe = examples / client / "receta_v1.json"
    fixture = examples / client / filename
    base = root / client / job
    measurement = root / "mediciones" / client / f"{job}.json"
    return client, filename, recipe, fixture, base, measurement


def _approval(recipe: Path, inputs: dict[str, str], approval_id: str, key: bytes) -> dict:
    payload = {"id": approval_id, "responsable": "operador_sintetico",
               "receta_sha256": _sha(recipe), "entradas_sha256": inputs}
    message = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return {**payload, "firma": hmac.new(key, message, hashlib.sha256).hexdigest()}


def _oracle(pilot: str, summary: dict) -> tuple[dict, dict]:
    """Compare the published summary with the independent SPEC section 8 oracle."""
    source = "clientes" if pilot == "a" else "ventas"
    entry = summary["entradas"][source]
    before, after = entry["antes"], entry["despues"]
    outcomes = {"initial_rows": before["filas"],
                "duplicates_initial": before["duplicados_exactos"],
                "final_rows": after["filas"]}
    checks = {"initial_rows": before["filas"] == 6,
              "duplicates_initial": before["duplicados_exactos"] == 1,
              "final_rows": after["filas"] == 5,
              "duplicates_final": after["duplicados_exactos"] == 0,
              "review_status": summary["estado"] == "revision_requerida"}
    if pilot == "a":
        outcomes.update({"initial_columns": before["columnas"],
                         "empty_literals": before["celdas_vacias"],
                         "space_only": before["celdas_solo_espacios"],
                         "absences_final": summary["validaciones"]["ausencias"]["incidencias"],
                         "invalid_emails": summary["validaciones"]["email"]["incidencias"]})
        checks.update({"initial_columns": outcomes["initial_columns"] == 4,
                       "empty_literals": outcomes["empty_literals"] == 3,
                       "space_only": outcomes["space_only"] == 1,
                       "absences_final": outcomes["absences_final"] == 3,
                       "invalid_emails": outcomes["invalid_emails"] == 1})
    else:
        date = summary["analisis"]["ventas_fecha"]
        product = summary["analisis"]["ventas_producto"]
        outcomes.update({"included": date["filas_incluidas"],
                         "excluded": date["filas_excluidas"],
                         "units": date["unidades"], "total": date["total"],
                         "amounts_by_date": date["grupos"],
                         "amounts_by_product": product["grupos"]})
        checks.update({"quantity_incidence": summary["validaciones"]["cantidad_valida"]["incidencias"] == 1,
                       "included": outcomes["included"] == 4,
                       "excluded": outcomes["excluded"] == 1,
                       "units": outcomes["units"] == 8,
                       "total": Decimal(outcomes["total"]) == Decimal("42.50"),
                       "dates": outcomes["amounts_by_date"] == {
                           "2026-01-05": "27.50", "2026-01-06": "10.00", "2026-01-07": "5.00"},
                       "products": outcomes["amounts_by_product"] == {"Libro": "30.00", "Lápiz": "12.50"}})
    return outcomes, checks


def run_pilot(pilot: str, root: Path, job: str, kind: str,
              approval_key: bytes | None, examples: Path = _EXAMPLES) -> dict:
    """Create a unique job, execute and verify it; keep the key only in memory."""
    if kind not in {"first", "repeat"}:
        raise ValueError("invalid_run_kind")
    if not isinstance(approval_key, bytes) or not approval_key:
        raise ValueError("approval_key_required")
    root, examples = Path(root), Path(examples)
    client, filename, recipe, fixture, base, measurement = _paths(pilot, root, job, examples)
    if base.exists() or measurement.exists():
        raise ValueError("job_exists")
    configured = load_recipe(recipe)
    source_id = configured.data["entradas"][0]["id"]
    approval_id = next(rule["params"]["aprobacion"] for rule in configured.data["reglas"]
                       if rule["op"] == "eliminar_duplicados_exactos")
    original_hash = _sha(fixture)
    for folder in ("originales", "trabajo", "salidas", "evidencia"):
        (base / folder).mkdir(parents=True, exist_ok=False)
    source = base / "originales" / filename
    shutil.copyfile(fixture, source)
    if _sha(source) != original_hash:
        raise ValueError("fixture_copy_mismatch")
    approval = _approval(recipe, {source_id: original_hash}, approval_id, approval_key)
    start = time.perf_counter()
    result = run_recipe(recipe, root, client, job,
                        approvals={approval_id: approval}, approval_key=approval_key)
    execution = time.perf_counter() - start
    start = time.perf_counter()
    checked = verify_recipe_package(recipe, root, client, job)
    verification = time.perf_counter() - start
    output_hashes = {name: _sha(path) for name, path in result.outputs.items()}
    outcomes, oracle_checks = _oracle(pilot, json.loads(result.outputs["resumen"].read_bytes()))
    report = {
        "synthetic": True, "pilot": pilot, "client": client, "job": job,
        "run_kind": kind, "recipe_id": configured.id, "recipe_version": configured.version,
        "status": result.status, "validations": result.validations,
        "outcomes": outcomes, "oracle_checks": oracle_checks,
        "oracle_ok": all(oracle_checks.values()),
        "hashes": {"recipe": _sha(recipe), "inputs": {source_id: original_hash},
                   "outputs": output_hashes,
                   "manifest": _sha(result.manifest_path) if result.manifest_path else None},
        "timing_seconds": {"execution": execution, "verification": verification},
        "operator_durations_minutes": {"preparation": None, "human_review": None},
        "verification": {"ok": checked.ok, "status": checked.status,
                         "issues": [issue.code for issue in checked.issues]},
        "locations": {"workspace": str(base.absolute()),
                      "outputs": {name: str(path.absolute()) for name, path in result.outputs.items()},
                      "manifest": str(result.manifest_path.absolute()) if result.manifest_path else None,
                      "measurement": str(measurement.absolute())},
    }
    measurement.parent.mkdir(parents=True, exist_ok=True)
    with measurement.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def verify_pilot(pilot: str, root: Path, job: str,
                 examples: Path = _EXAMPLES) -> dict:
    """Require the matching measurement record as well as package integrity."""
    root = Path(root)
    client, _, recipe, _, base, measurement = _paths(pilot, root, job, Path(examples))
    if not measurement.is_file():
        return {"ok": False, "status": None, "issues": ["missing_measurement"]}
    try:
        record = json.loads(measurement.read_text(encoding="utf-8"))
        if (record["pilot"], record["client"], record["job"], record["hashes"]["recipe"]) != (
                pilot, client, job, _sha(recipe)):
            raise ValueError("measurement_mismatch")
        if record["locations"]["workspace"] != str(base.absolute()):
            raise ValueError("measurement_mismatch")
        manifest = base / "evidencia" / "manifiesto.json"
        if record["hashes"]["manifest"] != _sha(manifest):
            raise ValueError("measurement_mismatch")
        if not record["oracle_ok"] or not all(record["oracle_checks"].values()):
            return {"ok": False, "status": None, "issues": ["oracle_mismatch"]}
    except (KeyError, ValueError, OSError, TypeError, json.JSONDecodeError):
        return {"ok": False, "status": None, "issues": ["measurement_mismatch"]}
    checked = verify_recipe_package(recipe, root, client, job)
    return {"ok": checked.ok, "status": checked.status,
            "issues": [issue.code for issue in checked.issues]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Laboratorio sintético local de Sprint 05")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--pilot", choices=tuple(_PILOTS), required=True)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--job")
        if name == "run":
            command.add_argument("--kind", choices=("first", "repeat"), required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            job = args.job or f"job_{uuid.uuid4().hex}"
            key = os.environ.get("VYNTRAVA_SYNTHETIC_APPROVAL_KEY")
            result = run_pilot(args.pilot, args.root, job, args.kind,
                               key.encode("utf-8") if key else None)
        else:
            if not args.job:
                parser.error("verify requires --job")
            result = verify_pilot(args.pilot, args.root, args.job)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"error: {getattr(exc, 'code', str(exc))}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("verification", result).get("ok") and result.get("oracle_ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
