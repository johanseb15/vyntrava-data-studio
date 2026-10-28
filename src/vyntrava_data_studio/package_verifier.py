"""Read-only integrity verification for existing ``run_recipe`` packages.

Public API: ``verify_recipe_package(recipe_path, root, client, job)`` returns a
``PackageVerification``. ``ok`` means file and manifest integrity only. It
does not establish business correctness, human approval, or cryptographic
authenticity of the package. No transformation is run and no file is written.
"""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import stat

from .delivery import ENGINE_VERSION, _HASH, _bounded_json, _regular_bytes
from .recipes import load_recipe
from .workspace import WorkspaceError, _status, _workspace, resolve_input


@dataclass(frozen=True)
class VerificationIssue:
    """Stable machine code; contains no path, cell value, or secret."""

    code: str


@dataclass(frozen=True)
class PackageVerification:
    """Verification result. ``status`` is the recorded execution state if valid."""

    ok: bool
    status: str | None
    issues: tuple[VerificationIssue, ...]


def _fail(code: str) -> PackageVerification:
    return PackageVerification(False, None, (VerificationIssue(code),))


def _hash(value: object) -> bool:
    return isinstance(value, str) and bool(_HASH.fullmatch(value))


def _keys(value: object, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _digest(path: Path, folder: Path) -> str:
    """Hash only an ordinary file directly in the already checked folder."""
    info = _status(path)
    if info is None:
        raise FileNotFoundError
    if not stat.S_ISREG(info.st_mode) or path.resolve(strict=True).parent != folder:
        raise WorkspaceError("invalid_file")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_shape(manifest: object, recipe) -> bool:
    if not _keys(manifest, {"estado", "receta", "motor", "parametros", "delimitadores",
                            "entradas", "aprobaciones", "validaciones", "salidas"}
                 | ({"analisis"} if recipe.data["analisis"] else set())):
        return False
    inputs = {entry["id"]: entry for entry in recipe.data["entradas"]}
    outputs = {entry["id"]: entry for entry in recipe.data["salidas"]}
    validations = {entry["id"]: entry for entry in recipe.data["validaciones"]}
    analyses = {entry["id"] for entry in recipe.data["analisis"]}
    approval_ids = {rule["params"]["aprobacion"] for rule in recipe.data["reglas"]
                    if rule["op"] == "eliminar_duplicados_exactos"}
    if (manifest["estado"] not in ("validado", "revision_requerida")
            or manifest["motor"] != ENGINE_VERSION
            or not _keys(manifest["receta"], {"id", "version", "sha256"})
            or manifest["receta"]["id"] != recipe.id
            or manifest["receta"]["version"] != recipe.version
            or not _hash(manifest["receta"]["sha256"])
            or not isinstance(manifest["parametros"], dict)
            or set(manifest["parametros"]) != set(recipe.data["parametros"])
            or not _keys(manifest["delimitadores"], {name for name, entry in inputs.items()
                                                   if entry["formato"] == "csv"})
            or not _keys(manifest["entradas"], set(inputs))
            or not _keys(manifest["salidas"], set(outputs))
            or not _keys(manifest["validaciones"], set(validations))
            or not _keys(manifest["aprobaciones"], approval_ids)):
        return False
    if analyses and not _keys(manifest["analisis"], analyses):
        return False
    for name, default in recipe.data["parametros"].items():
        actual = manifest["parametros"][name]
        if type(actual) is not type(default):
            return False
    for name, entry in inputs.items():
        recorded = manifest["entradas"][name]
        if entry["formato"] == "xlsx":
            if (not _keys(recorded, {"sha256", "formato", "hoja"})
                    or recorded["formato"] != "xlsx" or recorded["hoja"] != entry["hoja"]):
                return False
            if name in manifest["delimitadores"]:
                return False
        else:
            expected = {"sha256"} if recipe.version.startswith("1.0.") else {
                "sha256", "formato", "codificacion", "delimitador"}
            if not _keys(recorded, expected):
                return False
            delimiter = manifest["delimitadores"][name]
            if delimiter not in (",", ";") or (entry.get("delimitador") is not None
                                                   and delimiter != entry["delimitador"]):
                return False
            if len(expected) > 1 and (recorded["formato"] != "csv"
                    or recorded["codificacion"] != entry["codificacion"]
                    or recorded["delimitador"] != delimiter):
                return False
        if not _hash(recorded["sha256"]):
            return False
    warning = False
    for name, entry in validations.items():
        record = manifest["validaciones"][name]
        if (not _keys(record, {"incidencias", "severidad"})
                or type(record["incidencias"]) is not int or record["incidencias"] < 0
                or record["severidad"] != entry["severidad"]):
            return False
        if record["incidencias"] and entry["severidad"] == "bloquear":
            return False
        warning |= bool(record["incidencias"] and entry["severidad"] == "advertir")
    if manifest["estado"] != ("revision_requerida" if warning else "validado"):
        return False
    for name in approval_ids:
        record = manifest["aprobaciones"][name]
        if (not _keys(record, {"responsable", "firma"})
                or not isinstance(record["responsable"], str) or not record["responsable"]
                or not _hash(record["firma"])):
            return False
    for operation in recipe.data["analisis"]:
        record = manifest["analisis"][operation["id"]]
        fields = {"entrada", "columnas", "filas_incluidas", "filas_excluidas",
                  "exclusiones", "total"}
        if operation["op"] == "suma_producto":
            fields.add("unidades")
        if "grupo" in operation["params"]:
            fields.add("grupos")
        if (not _keys(record, fields)
                or record["entrada"] != operation["entrada"]
                or record["columnas"] != sorted(set(operation["params"].values()))
                or any(type(record[key]) is not int or record[key] < 0
                       for key in ("filas_incluidas", "filas_excluidas"))
                or not isinstance(record["exclusiones"], dict)
                or any(not isinstance(key, str) or type(value) is not int or value < 0
                       for key, value in record["exclusiones"].items())):
            return False
        if operation["op"] == "suma_producto":
            if (type(record["unidades"]) is not int or record["unidades"] < 0
                    or not isinstance(record["total"], str)):
                return False
        elif type(record["total"]) is not int or record["total"] != record["filas_incluidas"]:
            return False
        if "grupos" in fields and not isinstance(record["grupos"], dict):
            return False
    for name, entry in outputs.items():
        record = manifest["salidas"][name]
        if (not _keys(record, {"archivo", "sha256"})
                or record["archivo"] != entry["ruta"] or not _hash(record["sha256"])):
            return False
    return True


def verify_recipe_package(recipe_path: Path, root: Path, client: str,
                          job: str) -> PackageVerification:
    """Verify a published run_recipe package without opening data as tables.

    The caller supplies the original recipe and exact client/job identity.
    Results use stable issue codes and reveal no package content. Writers must
    be serialized externally; path checks cannot prevent concurrent replacement.
    """
    try:
        recipe_path = Path(recipe_path)
        recipe_folder = recipe_path.absolute().parent
        recipe_hash = _digest(recipe_path, recipe_folder)
        recipe = load_recipe(recipe_path)
    except (WorkspaceError, FileNotFoundError, OSError, TypeError, ValueError) as exc:
        return _fail("invalid_path" if isinstance(exc, (WorkspaceError, TypeError)) else "invalid_recipe")
    try:
        originals = _workspace(root, client, job, "originales")
        outputs = _workspace(root, client, job, "salidas")
        evidence = _workspace(root, client, job, "evidencia")
        manifest_path = evidence / "manifiesto.json"
        if _status(manifest_path) is None:
            return _fail("missing_manifest")
        manifest = _bounded_json(_regular_bytes(manifest_path, evidence))
        if not _manifest_shape(manifest, recipe):
            return _fail("invalid_manifest")
        if manifest["receta"]["sha256"] != recipe_hash:
            return _fail("recipe_hash_mismatch")
        expected_outputs = {entry["ruta"] for entry in recipe.data["salidas"]}
        output_names = {item.name for item in outputs.iterdir()}
        evidence_names = {item.name for item in evidence.iterdir()}
        if output_names - expected_outputs or evidence_names != {"manifiesto.json"}:
            return _fail("unexpected_file")
        if expected_outputs - output_names:
            return _fail("missing_output")
        for entry in recipe.data["entradas"]:
            try:
                source = resolve_input(root, client, job, entry["ruta"])
            except WorkspaceError as exc:
                return _fail("missing_input" if exc.code == "missing_input" else "invalid_path")
            if _digest(source, originals) != manifest["entradas"][entry["id"]]["sha256"]:
                return _fail("input_hash_mismatch")
        for entry in recipe.data["salidas"]:
            target = outputs / entry["ruta"]
            if _digest(target, outputs) != manifest["salidas"][entry["id"]]["sha256"]:
                return _fail("output_hash_mismatch")
        return PackageVerification(True, manifest["estado"], ())
    except WorkspaceError:
        return _fail("invalid_path")
    except FileNotFoundError:
        return _fail("missing_output")
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        return _fail("invalid_manifest")
