"""Compose the first, diagnostic-only vertical slice of the local engine."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any
from uuid import uuid4

from .diagnostics import diagnose
from .importer import CsvTable, read_csv
from .recipes import Recipe, load_recipe
from .workspace import WorkspaceError, _workspace, resolve_input, resolve_output


ENGINE_VERSION = "0.1.0"
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_MAX_VERIFICATION_JSON_BYTES = 64 * 1024 * 1024
_MAX_VERIFICATION_JSON_DEPTH = 64


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


def _stage_bytes(folder: Path, content: bytes) -> Path:
    """Write an exclusive private file and verify it only after closing it."""
    try:
        target = tempfile.NamedTemporaryFile(mode="wb", prefix="diagnostic-", suffix=".tmp",
                                             dir=folder, delete=False)
        path = Path(target.name)
        try:
            target.write(content)
            target.flush()
        finally:
            target.close()
        if path.read_bytes() != content:
            raise DeliveryError("write_error")
    except OSError:
        raise DeliveryError("write_error") from None
    return path


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
    if os.name != "nt":
        raise DeliveryError("unsupported_publication_platform")
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
        table = read_csv(source, entry["codificacion"], delimiters[entry_id],
                         ambiguity_confirmed=confirmed_delimiters is not None
                         and entry_id in confirmed_delimiters)
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

    work_folder = resolve_output(root, client, job, f"diagnostic-{uuid4().hex}", "trabajo").parent
    try:
        staged_summary = _stage_bytes(work_folder, summary_bytes)
        staged_manifest = _stage_bytes(work_folder, manifest_bytes)
        if _sha256(Path(recipe_path)) != manifest["receta"]["sha256"]:
            raise DeliveryError("recipe_changed")
        for entry_id, entry in ((item["id"], item) for item in recipe.data["entradas"]):
            if _sha256(resolve_input(root, client, job, entry["ruta"])) != inputs[entry_id]["sha256"]:
                raise DeliveryError("original_changed")
        if resolve_output(root, client, job, output_name, "salidas") != summary_path:
            raise DeliveryError("workspace_changed")
        os.rename(staged_summary, summary_path)
        if _sha256(summary_path) != manifest["salidas"][recipe.data["salidas"][0]["id"]]["sha256"]:
            raise DeliveryError("write_error")
        if resolve_output(root, client, job, "manifiesto.json", "evidencia") != manifest_path:
            raise DeliveryError("workspace_changed")
        os.rename(staged_manifest, manifest_path)
    except (OSError, DeliveryError) as exc:
        if isinstance(exc, DeliveryError):
            raise
        raise DeliveryError("write_error") from None
    return DiagnosticRun(summary_path, manifest_path)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("invalid_json_constant")


def _regular_bytes(path: Path, folder: Path) -> bytes:
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & _REPARSE_POINT
            or path.resolve(strict=True).parent != folder):
        raise ValueError("invalid_file")
    if info.st_size > _MAX_VERIFICATION_JSON_BYTES:
        raise ValueError("json_too_large")
    with path.open("rb") as source:
        data = source.read(_MAX_VERIFICATION_JSON_BYTES + 1)
    if len(data) > _MAX_VERIFICATION_JSON_BYTES:
        raise ValueError("json_too_large")
    return data


def _bounded_json(data: bytes) -> Any:
    depth = 0
    quoted = False
    escaped = False
    for char in data:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:  # backslash
                escaped = True
            elif char == 34:  # double quote
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):  # [ {
            depth += 1
            if depth > _MAX_VERIFICATION_JSON_DEPTH:
                raise ValueError("json_too_deep")
        elif char in (93, 125):  # ] }
            depth -= 1
    return json.loads(data, object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant)


def verify_delivery(recipe_path: Path, root: Path, client: str, job: str) -> str:
    """Classify a diagnostic package at consumption time without changing files.

    The caller must keep the original recipe and serialize writers for this job.
    A verified package is an integrity check, not a business approval or signature.
    """
    try:
        recipe = load_recipe(recipe_path)
        _check_capabilities(recipe)
        work = _workspace(root, client, job, "trabajo")
        outputs = _workspace(root, client, job, "salidas")
        evidence = _workspace(root, client, job, "evidencia")
        output = recipe.data["salidas"][0]
        summary_path = outputs / output["ruta"]
        manifest_path = evidence / "manifiesto.json"
        output_names = {item.name for item in outputs.iterdir()}
        evidence_names = {item.name for item in evidence.iterdir()}
        temporary = any(item.name.startswith("diagnostic-") and item.name.endswith(".tmp")
                        for item in work.iterdir())
    except (OSError, WorkspaceError):
        return "no-verificable"
    except (ValueError, TypeError, KeyError):
        return "inconsistente"

    if "manifiesto.json" not in evidence_names:
        return "incompleto" if not evidence_names else "inconsistente"
    if output["ruta"] not in output_names:
        return "inconsistente"
    if output_names != {output["ruta"]} or evidence_names != {"manifiesto.json"}:
        return "inconsistente"
    try:
        manifest_bytes = _regular_bytes(manifest_path, evidence)
        summary_bytes = _regular_bytes(summary_path, outputs)
        manifest = _bounded_json(manifest_bytes)
        summary = _bounded_json(summary_bytes)
        expected_inputs = {entry["id"]: entry for entry in recipe.data["entradas"]}
        if not isinstance(manifest, dict) or set(manifest) != {
                "estado", "receta", "motor", "parametros", "delimitadores", "entradas", "salidas"}:
            return "inconsistente"
        if (manifest["estado"] != "diagnostico" or manifest["motor"] != ENGINE_VERSION
                or manifest["parametros"] != {}
                or not isinstance(manifest["receta"], dict)
                or set(manifest["receta"]) != {"id", "version", "sha256"}
                or manifest["receta"] != {"id": recipe.id, "version": recipe.version,
                                          "sha256": _sha256(Path(recipe_path))}
                or not isinstance(manifest["entradas"], dict)
                or set(manifest["entradas"]) != set(expected_inputs)
                or not isinstance(manifest["delimitadores"], dict)
                or set(manifest["delimitadores"]) != set(expected_inputs)
                or not isinstance(manifest["salidas"], dict)
                or set(manifest["salidas"]) != {output["id"]}
                or not isinstance(summary, dict)
                or set(summary) != {"receta", "entradas"}
                or summary["receta"] != recipe.id
                or not isinstance(summary["entradas"], dict)
                or set(summary["entradas"]) != set(expected_inputs)):
            return "inconsistente"
        published = manifest["salidas"][output["id"]]
        if (not isinstance(published, dict) or set(published) != {"archivo", "sha256"}
                or published["archivo"] != output["ruta"]
                or not isinstance(published["sha256"], str)
                or not _HASH.fullmatch(published["sha256"])
                or hashlib.sha256(summary_bytes).hexdigest() != published["sha256"]):
            return "inconsistente"
        for entry_id in expected_inputs:
            diagnosis = summary["entradas"][entry_id]
            if (not isinstance(diagnosis, dict)
                    or set(diagnosis) != {"filas", "columnas", "duplicados_exactos",
                                              "celdas_vacias", "celdas_solo_espacios",
                                              "columnas_extra", "detalle_columnas"}
                    or any(type(diagnosis[key]) is not int or diagnosis[key] < 0
                           for key in ("filas", "columnas", "duplicados_exactos",
                                       "celdas_vacias", "celdas_solo_espacios"))
                    or not isinstance(diagnosis["columnas_extra"], list)
                    or not isinstance(diagnosis["detalle_columnas"], list)
                    or len(diagnosis["detalle_columnas"]) != diagnosis["columnas"]):
                return "inconsistente"
        for entry_id, entry in expected_inputs.items():
            recorded = manifest["entradas"][entry_id]
            if (not isinstance(recorded, dict) or set(recorded) != {"sha256", "codificacion", "bom"}
                    or not isinstance(recorded["sha256"], str)
                    or not _HASH.fullmatch(recorded["sha256"])
                    or recorded["codificacion"] != entry["codificacion"]
                    or type(recorded["bom"]) is not bool
                    or manifest["delimitadores"][entry_id] not in (",", ";")
                    or (entry.get("delimitador") is not None
                        and manifest["delimitadores"][entry_id] != entry["delimitador"])):
                return "inconsistente"
            try:
                source = resolve_input(root, client, job, entry["ruta"])
            except WorkspaceError as exc:
                return "inconsistente" if exc.code == "missing_input" else "no-verificable"
            if _sha256(source) != recorded["sha256"]:
                return "inconsistente"
        return "inconsistente" if temporary else "completo-verificado"
    except DeliveryError:
        return "no-verificable"
    except (OSError, WorkspaceError):
        return "no-verificable"
    except (ValueError, TypeError, KeyError, RecursionError):
        return "inconsistente"
