"""Compose the first, diagnostic-only vertical slice of the local engine."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .diagnostics import diagnose
from .importer import CsvTable, read_csv
from .recipes import Recipe, load_recipe
from .workspace import resolve_input, resolve_output


ENGINE_VERSION = "0.1.0"


class DeliveryError(ValueError):
    """A delivery was rejected without exposing input cells or file paths."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DiagnosticRun:
    summary_path: Path
    manifest_path: Path


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise DeliveryError("read_error") from None


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _check_capabilities(recipe: Recipe) -> None:
    data = recipe.data
    if (any(item["op"] != "diagnosticar" for item in data["reglas"])
            or data["validaciones"]
            or data["analisis"]
            or len(data["salidas"]) != 1
            or data["salidas"][0]["tipo"] != "resumen_json"):
        raise DeliveryError("unsupported_capability")


def _delimiters(recipe: Recipe, confirmed: dict[str, str] | None) -> dict[str, str]:
    if confirmed is not None and not isinstance(confirmed, dict):
        raise DeliveryError("invalid_confirmation")
    confirmed = confirmed or {}
    entry_ids = {item["id"] for item in recipe.data["entradas"]}
    if confirmed.keys() - entry_ids:
        raise DeliveryError("invalid_confirmation")
    effective = {}
    for entry in recipe.data["entradas"]:
        entry_id = entry["id"]
        declared = entry.get("delimitador")
        selected = confirmed.get(entry_id, declared)
        if selected not in (",", ";"):
            raise DeliveryError("delimiter_required" if selected is None else "invalid_confirmation")
        if declared is not None and selected != declared:
            raise DeliveryError("invalid_confirmation")
        effective[entry_id] = selected
    return effective


def _check_schema(table: CsvTable, schema: dict[str, Any]) -> tuple[str, ...]:
    required = schema["columnas"]
    actual = table.headers
    positions = [actual.index(name) for name in required if name in actual]
    if (len(positions) != len(required) or positions != sorted(positions)
            or (schema["extras"] == "rechazar" and actual != tuple(required))):
        raise DeliveryError("schema_mismatch")
    return tuple(name for name in actual if name not in required)


def _summary(table: CsvTable, extra: tuple[str, ...]) -> dict[str, Any]:
    result = diagnose(table)
    return {
        "filas": result.row_count,
        "columnas": result.column_count,
        "duplicados_exactos": result.exact_duplicate_count,
        "celdas_vacias": result.empty_cell_count,
        "celdas_solo_espacios": result.whitespace_only_cell_count,
        "columnas_extra": list(extra),
        "detalle_columnas": [
            {"nombre": column.name, "vacias": column.empty_count,
             "solo_espacios": column.whitespace_only_count,
             "tipo_inferido": column.inferred_type}
            for column in result.columns
        ],
    }


def run_diagnostic(recipe_path: Path, root: Path, client: str, job: str,
                   confirmed_delimiters: dict[str, str] | None = None) -> DiagnosticRun:
    """Run supported diagnostics and publish the manifest only after all checks pass."""
    recipe = load_recipe(recipe_path)
    _check_capabilities(recipe)
    delimiters = _delimiters(recipe, confirmed_delimiters)
    output_name = recipe.data["salidas"][0]["ruta"]
    summary_path = resolve_output(root, client, job, output_name, "salidas")
    manifest_path = resolve_output(root, client, job, "manifiesto.json", "evidencia")

    summaries: dict[str, Any] = {}
    inputs: dict[str, Any] = {}
    for entry in recipe.data["entradas"]:
        entry_id = entry["id"]
        source = resolve_input(root, client, job, entry["ruta"])
        before = _sha256(source)
        source = resolve_input(root, client, job, entry["ruta"])
        table = read_csv(source, entry["codificacion"], delimiters[entry_id])
        if _sha256(source) != before:
            raise DeliveryError("original_changed")
        extra = _check_schema(table, recipe.data["esquema"][entry_id])
        summaries[entry_id] = _summary(table, extra)
        inputs[entry_id] = {"sha256": before, "codificacion": entry["codificacion"],
                            "bom": table.had_bom}

    summary_bytes = _json_bytes({"receta": recipe.id, "entradas": summaries})
    manifest = {
        "estado": "diagnostico",
        "receta": {"id": recipe.id, "version": recipe.version,
                   "sha256": _sha256(Path(recipe_path))},
        "motor": ENGINE_VERSION,
        "parametros": {},
        "delimitadores": delimiters,
        "entradas": inputs,
        "salidas": {recipe.data["salidas"][0]["id"]: {
            "sha256": hashlib.sha256(summary_bytes).hexdigest(), "archivo": output_name}},
    }
    manifest_bytes = _json_bytes(manifest)

    # Recheck just before use; exclusive creation protects existing outputs.
    if resolve_output(root, client, job, output_name, "salidas") != summary_path:
        raise DeliveryError("workspace_changed")
    if resolve_output(root, client, job, "manifiesto.json", "evidencia") != manifest_path:
        raise DeliveryError("workspace_changed")
    summary_created = False
    manifest_created = False
    try:
        with summary_path.open("xb") as target:
            summary_created = True
            target.write(summary_bytes)
        for entry_id, entry in ((item["id"], item) for item in recipe.data["entradas"]):
            if _sha256(resolve_input(root, client, job, entry["ruta"])) != inputs[entry_id]["sha256"]:
                raise DeliveryError("original_changed")
        with manifest_path.open("xb") as target:
            manifest_created = True
            target.write(manifest_bytes)
    except (OSError, DeliveryError) as exc:
        try:
            if manifest_created:
                manifest_path.unlink(missing_ok=True)
            if summary_created:
                summary_path.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, DeliveryError):
            raise
        raise DeliveryError("write_error") from None
    return DiagnosticRun(summary_path, manifest_path)
