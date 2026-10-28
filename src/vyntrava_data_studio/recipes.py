"""Validación estática del contrato de recetas JSON v1."""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any


IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
TOP_FIELDS = frozenset({"id", "version", "tipo_encargo", "entradas", "esquema",
                        "parametros", "reglas", "validaciones", "analisis", "salidas"})
OPERATIONS = {
    "reglas": {
        "diagnosticar": (frozenset(), frozenset()),
        "recortar_espacios": (frozenset({"columnas"}), frozenset()),
        "eliminar_duplicados_exactos": (frozenset({"aprobacion"}), frozenset()),
    },
    "validaciones": {
        "columnas_requeridas": (frozenset({"columnas"}), frozenset()),
        "no_vacio": (frozenset({"columnas"}), frozenset()),
        "email_simple": (frozenset({"columna"}), frozenset()),
        "decimal_positivo": (frozenset({"columna"}), frozenset()),
        "entero_positivo": (frozenset({"columna"}), frozenset()),
    },
    "analisis": {
        "suma_producto": (frozenset({"cantidad", "precio"}), frozenset({"grupo"})),
        "conteo": (frozenset(), frozenset({"grupo"})),
    },
}


class RecipeError(ValueError):
    """Error sin datos de celdas, con código y ubicación JSON estables."""

    def __init__(self, code: str, location: str):
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class Recipe:
    id: str
    version: str
    data: dict[str, Any]
    sha256: str


class _Pairs(list):
    """Conserva pares hasta poder señalar la ubicación de una clave duplicada."""


def _materialize(value: Any, location: str = "$") -> Any:
    if isinstance(value, _Pairs):
        result = {}
        for key, item in value:
            child = f"{location}.{key}"
            if key in result:
                raise RecipeError("duplicate_key", child)
            result[key] = _materialize(item, child)
        return result
    if isinstance(value, list):
        return [_materialize(item, f"{location}[{index}]") for index, item in enumerate(value)]
    return value


def _object(value: Any, location: str, required: set[str] | frozenset[str],
            optional: set[str] | frozenset[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise RecipeError("invalid_type", location)
    for key in sorted(required - value.keys()):
        raise RecipeError("missing_field", f"{location}.{key}")
    for key in sorted(value.keys() - required - optional):
        raise RecipeError("unknown_field", f"{location}.{key}")
    return value


def _list(value: Any, location: str, nonempty: bool = False) -> list:
    if not isinstance(value, list):
        raise RecipeError("invalid_type", location)
    if nonempty and not value:
        raise RecipeError("empty_list", location)
    return value


def _identifier(value: Any, location: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise RecipeError("invalid_identifier", location)
    return value


def _basename(value: Any, location: str) -> str:
    if (not isinstance(value, str) or not value or value in {".", ".."}
            or any(c in value for c in "/\\:")
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise RecipeError("invalid_path", location)
    return value


def _choice(value: Any, choices: set[str], location: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise RecipeError("invalid_value", location)
    return value


def _scalar(value: Any) -> bool:
    return (value is None or isinstance(value, (str, bool))
            or type(value) is int
            or (type(value) is float and math.isfinite(value)))


def _columns(value: Any, location: str, available: set[str] | None = None) -> list[str]:
    columns = _list(value, location, nonempty=True)
    seen = set()
    for index, column in enumerate(columns):
        item_location = f"{location}[{index}]"
        if not isinstance(column, str) or not column:
            raise RecipeError("invalid_type", item_location)
        if column in seen:
            raise RecipeError("duplicate_id", item_location)
        if available is not None and column not in available:
            raise RecipeError("unknown_reference", item_location)
        seen.add(column)
    return columns


def _validate_version(value: Any) -> None:
    if not isinstance(value, str) or not (match := VERSION.fullmatch(value)):
        raise RecipeError("invalid_version", "$.version")
    if match[1] != "1" or match[2] not in {"0", "1"}:
        raise RecipeError("unsupported_version", "$.version")


def _validate_inputs(data: dict) -> set[str]:
    ids = set()
    for index, raw in enumerate(_list(data["entradas"], "$.entradas", nonempty=True)):
        location = f"$.entradas[{index}]"
        if not isinstance(raw, dict):
            raise RecipeError("invalid_type", location)
        fmt = raw.get("formato")
        _choice(fmt, {"csv", "xlsx"}, f"{location}.formato")
        if fmt == "xlsx":
            if data["version"].split(".")[1] != "1":
                raise RecipeError("unsupported_version", "$.version")
            item = _object(raw, location, {"id", "ruta", "formato", "hoja"})
            if not isinstance(item["hoja"], str) or not item["hoja"]:
                raise RecipeError("invalid_type", f"{location}.hoja")
        else:
            item = _object(raw, location, {"id", "ruta", "formato", "codificacion"}, {"delimitador"})
        entry_id = _identifier(item["id"], f"{location}.id")
        if entry_id in ids:
            raise RecipeError("duplicate_id", f"{location}.id")
        ids.add(entry_id)
        path = _basename(item["ruta"], f"{location}.ruta")
        if not path.endswith(".xlsx" if fmt == "xlsx" else ".csv"):
            raise RecipeError("invalid_path", f"{location}.ruta")
        if fmt == "csv":
            _choice(item["codificacion"], {"utf-8", "utf-8-sig"}, f"{location}.codificacion")
        if fmt == "csv" and "delimitador" in item:
            _choice(item["delimitador"], {",", ";"}, f"{location}.delimitador")
    return ids


def _validate_schema(data: dict, input_ids: set[str]) -> dict[str, set[str]]:
    schema = data["esquema"]
    if not isinstance(schema, dict):
        raise RecipeError("invalid_type", "$.esquema")
    for entry_id in sorted(input_ids - schema.keys()):
        raise RecipeError("missing_field", f"$.esquema.{entry_id}")
    result = {}
    for entry_id, raw in schema.items():
        location = f"$.esquema.{entry_id}"
        if entry_id not in input_ids:
            raise RecipeError("unknown_reference", location)
        item = _object(raw, location, {"columnas", "extras"})
        result[entry_id] = set(_columns(item["columnas"], f"{location}.columnas"))
        _choice(item["extras"], {"rechazar", "permitir"}, f"{location}.extras")
    return result


def _validate_parameters(data: dict, overrides: dict | None = None) -> dict:
    params = data["parametros"]
    if not isinstance(params, dict):
        raise RecipeError("invalid_type", "$.parametros")
    for key, value in params.items():
        _identifier(key, f"$.parametros.{key}")
        if not _scalar(value):
            raise RecipeError("invalid_type", f"$.parametros.{key}")
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise RecipeError("invalid_type", "$.parametros")
        for key, value in overrides.items():
            if key not in params:
                raise RecipeError("unknown_reference", f"$.parametros.{key}")
            if type(value) is not type(params[key]) or not _scalar(value):
                raise RecipeError("invalid_type", f"$.parametros.{key}")
            params[key] = value
    return params


def _resolve_scalar(value: Any, location: str, parameters: dict) -> Any:
    if isinstance(value, dict):
        _object(value, location, {"parametro"})
        name = _identifier(value["parametro"], f"{location}.parametro")
        if name not in parameters:
            raise RecipeError("unknown_reference", f"{location}.parametro")
        return parameters[name]
    return value


def _validate_operations(data: dict, schema: dict[str, set[str]], parameters: dict) -> None:
    for section, operations in OPERATIONS.items():
        seen = set()
        for index, raw in enumerate(_list(data[section], f"$.{section}")):
            location = f"$.{section}[{index}]"
            fields = {"id", "op", "entrada", "params"}
            if section == "validaciones":
                fields.add("severidad")
            item = _object(raw, location, fields)
            op_id = _identifier(item["id"], f"{location}.id")
            if op_id in seen:
                raise RecipeError("duplicate_id", f"{location}.id")
            seen.add(op_id)
            op = item["op"]
            if not isinstance(op, str) or op not in operations:
                raise RecipeError("unknown_operation", f"{location}.op")
            entry_id = item["entrada"]
            if not isinstance(entry_id, str) or entry_id not in schema:
                raise RecipeError("unknown_reference", f"{location}.entrada")
            if section == "validaciones":
                _choice(item["severidad"], {"advertir", "bloquear"}, f"{location}.severidad")
            required, optional = operations[op]
            params = _object(item["params"], f"{location}.params", required, optional)
            for key, value in params.items():
                param_location = f"{location}.params.{key}"
                if key == "columnas":
                    _columns(value, param_location,
                             None if op == "columnas_requeridas" else schema[entry_id])
                    continue
                resolved = _resolve_scalar(value, param_location, parameters)
                if not isinstance(resolved, str) or not resolved:
                    raise RecipeError("invalid_type", param_location)
                if key != "aprobacion" and resolved not in schema[entry_id]:
                    raise RecipeError("unknown_reference", param_location)
                if key == "aprobacion":
                    _identifier(resolved, param_location)
                params[key] = resolved


def _validate_outputs(data: dict, input_ids: set[str]) -> None:
    seen_ids = set()
    seen_paths = set()
    for index, raw in enumerate(_list(data["salidas"], "$.salidas", nonempty=True)):
        location = f"$.salidas[{index}]"
        if not isinstance(raw, dict):
            raise RecipeError("invalid_type", location)
        kind = raw.get("tipo")
        _choice(kind, {"resumen_json", "tabla_csv", "grafico_png"}, f"{location}.tipo")
        required = {"id", "tipo", "ruta"} | ({"fuente"} if kind != "resumen_json" else set())
        item = _object(raw, location, required)
        output_id = _identifier(item["id"], f"{location}.id")
        if output_id in seen_ids:
            raise RecipeError("duplicate_id", f"{location}.id")
        seen_ids.add(output_id)
        path = _basename(item["ruta"], f"{location}.ruta")
        if path in seen_paths:
            raise RecipeError("duplicate_path", f"{location}.ruta")
        seen_paths.add(path)
        if kind == "tabla_csv" and (not isinstance(item["fuente"], str)
                                    or item["fuente"] not in input_ids):
            raise RecipeError("unknown_reference", f"{location}.fuente")
        if kind == "grafico_png":
            if not path.lower().endswith(".png"):
                raise RecipeError("invalid_path", f"{location}.ruta")
            sources = {entry["id"] for entry in data["analisis"]
                       if entry["op"] == "suma_producto" and "grupo" in entry["params"]}
            if not isinstance(item["fuente"], str) or item["fuente"] not in sources:
                raise RecipeError("unknown_reference", f"{location}.fuente")


def load_recipe(path: Path, overrides: dict | None = None) -> Recipe:
    """Carga y valida la receta sin abrir entradas ni crear salidas."""
    try:
        raw_bytes = Path(path).read_bytes()
        raw = raw_bytes.decode("utf-8")
    except (OSError, UnicodeError):
        raise RecipeError("read_error", "$") from None
    try:
        parsed = json.loads(raw, object_pairs_hook=_Pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, json.JSONDecodeError) as exc:
        raise RecipeError("invalid_json", "$") from exc
    data = _materialize(parsed)
    _object(data, "$", TOP_FIELDS)
    _identifier(data["id"], "$.id")
    _validate_version(data["version"])
    if not isinstance(data["tipo_encargo"], str) or not data["tipo_encargo"]:
        raise RecipeError("invalid_type", "$.tipo_encargo")
    inputs = _validate_inputs(data)
    schema = _validate_schema(data, inputs)
    params = _validate_parameters(data, overrides)
    _validate_operations(data, schema, params)
    _validate_outputs(data, inputs)
    return Recipe(data["id"], data["version"], data,
                  hashlib.sha256(raw_bytes).hexdigest())
