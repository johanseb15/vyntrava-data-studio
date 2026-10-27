"""Recipe-driven CSV cleaning and validation for Sprint 02."""

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
from typing import Any

from .delivery import (DeliveryError, ENGINE_VERSION, _check_schema, _delimiters,
                       _json_bytes, _sha256, _stage_bytes, _summary)
from .importer import CsvTable, read_csv
from .recipes import load_recipe
from .workspace import resolve_input, resolve_output


_INTEGER = re.compile(r"[0-9]+\Z")
_DECIMAL = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)\Z")


@dataclass(frozen=True)
class RecipeRun:
    status: str
    outputs: dict[str, Path]
    manifest_path: Path | None
    validations: dict[str, dict[str, Any]]


def _approved(record: Any, approval_id: str, recipe_hash: str,
              input_hashes: dict[str, str], key: bytes | None) -> bool:
    if not isinstance(record, dict) or not isinstance(key, bytes) or not key:
        return False
    if set(record) != {"id", "responsable", "receta_sha256", "entradas_sha256", "firma"}:
        return False
    if (record["id"] != approval_id or not isinstance(record["responsable"], str)
            or not record["responsable"] or record["receta_sha256"] != recipe_hash
            or record["entradas_sha256"] != input_hashes
            or not isinstance(record["firma"], str)):
        return False
    payload = {field: record[field] for field in ("id", "responsable", "receta_sha256", "entradas_sha256")}
    expected = hmac.new(key, json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False).encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, record["firma"])


def _replace_rows(table: CsvTable, rows: tuple[tuple[str, ...], ...]) -> CsvTable:
    return CsvTable(table.headers, rows, table.had_bom, table.delimiter, table.encoding)


def _clean(table: CsvTable, rule: dict) -> tuple[CsvTable, int]:
    if rule["op"] == "diagnosticar":
        return table, 0
    if rule["op"] == "recortar_espacios":
        indices = {table.headers.index(name) for name in rule["params"]["columnas"]}
        rows = tuple(tuple(value.strip(" ") if index in indices else value
                           for index, value in enumerate(row)) for row in table.rows)
        count = sum(a != b for old, new in zip(table.rows, rows)
                    for a, b in zip(old, new))
        return _replace_rows(table, rows), count
    seen = set()
    rows = []
    for row in table.rows:
        if row not in seen:
            rows.append(row)
            seen.add(row)
    return _replace_rows(table, tuple(rows)), len(table.rows) - len(rows)


def _positive(value: str, integer: bool) -> bool:
    if not (_INTEGER if integer else _DECIMAL).fullmatch(value):
        return False
    try:
        number = Decimal(value)
        return number.is_finite() and number > 0
    except InvalidOperation:
        return False


def _validate(table: CsvTable, operation: dict) -> int:
    op = operation["op"]
    params = operation["params"]
    if op == "columnas_requeridas":
        return sum(column not in table.headers for column in params["columnas"])
    if op == "no_vacio":
        indices = [table.headers.index(column) for column in params["columnas"]]
        return sum(not row[index].strip(" ") for row in table.rows for index in indices)
    index = table.headers.index(params["columna"])
    if op == "email_simple":
        return sum(bool(row[index]) and (row[index].count("@") != 1
                    or not all(row[index].split("@"))) for row in table.rows)
    return sum(not _positive(row[index], op == "entero_positivo") for row in table.rows)


def _csv_bytes(table: CsvTable) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=table.delimiter, lineterminator="\n")
    writer.writerow(table.headers)
    writer.writerows(table.rows)
    return stream.getvalue().encode("utf-8-sig" if table.had_bom else "utf-8")


def run_recipe(recipe_path: Path, root: Path, client: str, job: str,
               confirmed_delimiters: dict[str, str] | None = None,
               overrides: dict[str, Any] | None = None,
               approvals: dict[str, dict] | None = None,
               approval_key: bytes | None = None) -> RecipeRun:
    """Execute supported v1 cleaning; publish only if no blocking incidence exists."""
    recipe = load_recipe(recipe_path, overrides)
    if recipe.data["analisis"] or any(out["tipo"] == "grafico_png" for out in recipe.data["salidas"]):
        raise DeliveryError("unsupported_capability")
    if os.name != "nt":
        raise DeliveryError("unsupported_publication_platform")
    delimiters = _delimiters(recipe, confirmed_delimiters)
    if approvals is not None and not isinstance(approvals, dict):
        raise DeliveryError("invalid_approval")
    approvals = approvals or {}
    recipe_hash = recipe.sha256
    input_hashes = {}
    tables = {}
    extras = {}
    for entry in recipe.data["entradas"]:
        source = resolve_input(root, client, job, entry["ruta"])
        digest = _sha256(source)
        table = read_csv(source, entry["codificacion"], delimiters[entry["id"]],
                         ambiguity_confirmed=confirmed_delimiters is not None
                         and entry["id"] in confirmed_delimiters)
        if _sha256(source) != digest:
            raise DeliveryError("original_changed")
        extras[entry["id"]] = _check_schema(table, recipe.data["esquema"][entry["id"]])
        input_hashes[entry["id"]] = digest
        tables[entry["id"]] = table
    before = {name: _summary(table, extras[name]) for name, table in tables.items()}
    changes = {}
    for rule in recipe.data["reglas"]:
        if rule["op"] == "eliminar_duplicados_exactos" and not _approved(
                approvals.get(rule["params"]["aprobacion"]), rule["params"]["aprobacion"],
                recipe_hash, input_hashes, approval_key):
            raise DeliveryError("approval_required")
        name = rule["entrada"]
        tables[name], count = _clean(tables[name], rule)
        changes[rule["id"]] = {"op": rule["op"], "cambios": count}
    validations = {}
    blocking = False
    warning = False
    for operation in recipe.data["validaciones"]:
        count = _validate(tables[operation["entrada"]], operation)
        validations[operation["id"]] = {"incidencias": count, "severidad": operation["severidad"]}
        blocking |= count > 0 and operation["severidad"] == "bloquear"
        warning |= count > 0 and operation["severidad"] == "advertir"
    if blocking:
        return RecipeRun("bloqueado", {}, None, validations)
    status = "revision_requerida" if warning else "validado"
    report = {"receta": recipe.id, "estado": status,
              "entradas": {name: {"antes": before[name], "despues": _summary(table, extras[name])}
                           for name, table in tables.items()},
              "reglas": changes, "validaciones": validations}
    contents = {}
    for output in recipe.data["salidas"]:
        contents[output["id"]] = (_json_bytes(report) if output["tipo"] == "resumen_json"
                                   else _csv_bytes(tables[output["fuente"]]))
    paths = {out["id"]: resolve_output(root, client, job, out["ruta"], "salidas")
             for out in recipe.data["salidas"]}
    manifest_path = resolve_output(root, client, job, "manifiesto.json", "evidencia")
    manifest = {"estado": status, "receta": {"id": recipe.id, "version": recipe.version,
                "sha256": recipe_hash}, "motor": ENGINE_VERSION,
                "parametros": recipe.data["parametros"], "delimitadores": delimiters,
                "entradas": {name: {"sha256": digest} for name, digest in input_hashes.items()},
                "aprobaciones": {key: {"responsable": approvals[key]["responsable"],
                                  "firma": approvals[key]["firma"]}
                                 for key in sorted({rule["params"]["aprobacion"] for rule in recipe.data["reglas"]
                                                    if rule["op"] == "eliminar_duplicados_exactos"})},
                "validaciones": validations,
                "salidas": {out["id"]: {"archivo": out["ruta"],
                            "sha256": hashlib.sha256(contents[out["id"]]).hexdigest()}
                            for out in recipe.data["salidas"]}}
    work = resolve_output(root, client, job, "recipe-stage", "trabajo").parent
    staged = {key: _stage_bytes(work, value) for key, value in contents.items()}
    staged_manifest = _stage_bytes(work, _json_bytes(manifest))
    if _sha256(Path(recipe_path)) != recipe_hash:
        raise DeliveryError("recipe_changed")
    for entry in recipe.data["entradas"]:
        if _sha256(resolve_input(root, client, job, entry["ruta"])) != input_hashes[entry["id"]]:
            raise DeliveryError("original_changed")
    try:
        for out in recipe.data["salidas"]:
            target = resolve_output(root, client, job, out["ruta"], "salidas")
            os.rename(staged[out["id"]], target)
            if _sha256(target) != manifest["salidas"][out["id"]]["sha256"]:
                raise DeliveryError("write_error")
        resolve_output(root, client, job, "manifiesto.json", "evidencia")
        os.rename(staged_manifest, manifest_path)
    except OSError:
        raise DeliveryError("write_error") from None
    return RecipeRun(status, paths, manifest_path, validations)
