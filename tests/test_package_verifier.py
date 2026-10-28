"""Integrity checks use only fictional packages produced by run_recipe."""

import hashlib
import json

import pytest

from vyntrava_data_studio.sprint02 import run_recipe
from vyntrava_data_studio.package_verifier import verify_recipe_package


def package(tmp_path, *, version="1.0.0", severity="advertir", value="synthetic"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    root = tmp_path / "clientes"
    job = root / "cliente_a" / "encargo_a"
    for folder in ("originales", "trabajo", "salidas", "evidencia"):
        (job / folder).mkdir(parents=True)
    source = job / "originales" / "datos.csv"
    source.write_bytes(f"id,valor\n1,{value}\n".encode())
    data = {
        "id": "receta_sintetica", "version": version, "tipo_encargo": "prueba",
        "entradas": [{"id": "datos", "ruta": "datos.csv", "formato": "csv",
                      "codificacion": "utf-8", "delimitador": ","}],
        "esquema": {"datos": {"columnas": ["id", "valor"], "extras": "rechazar"}},
        "parametros": {}, "reglas": [],
        "validaciones": [{"id": "v1", "op": "no_vacio", "entrada": "datos",
                          "params": {"columnas": ["valor"]}, "severidad": severity}],
        "analisis": [],
        "salidas": [{"id": "resumen", "tipo": "resumen_json", "ruta": "resumen.json"},
                    {"id": "tabla", "tipo": "tabla_csv", "ruta": "tabla.csv", "fuente": "datos"}],
    }
    recipe = tmp_path / "receta.json"
    recipe.write_text(json.dumps(data), encoding="utf-8")
    run = run_recipe(recipe, root, "cliente_a", "encargo_a")
    return root, job, source, recipe, run


def check(recipe, root, client="cliente_a", job="encargo_a"):
    return verify_recipe_package(recipe, root, client, job)


def edit_manifest(run, change):
    path = run.manifest_path
    data = json.loads(path.read_bytes())
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0"])
def test_valid_package_is_repeatable_and_read_only(tmp_path, version):
    root, job, source, recipe, run = package(tmp_path, version=version)
    files = [recipe, *job.rglob("*")]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    first = check(recipe, root)
    assert first.ok and first.status == "validado" and first.issues == ()
    assert first == check(recipe, root)
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}


@pytest.mark.parametrize("damage,code", [
    ("original", "input_hash_mismatch"), ("recipe", "recipe_hash_mismatch"),
    ("output", "output_hash_mismatch"), ("missing_output", "missing_output"),
    ("extra", "unexpected_file"), ("invalid_json", "invalid_manifest"),
    ("fake_hash", "invalid_manifest"), ("wrong_filename", "invalid_manifest"),
])
def test_rejects_damage_without_exposing_values(tmp_path, damage, code):
    root, job, source, recipe, run = package(tmp_path)
    if damage == "original":
        source.write_bytes(source.read_bytes() + b"secret-cell-value")
    elif damage == "recipe":
        recipe.write_bytes(recipe.read_bytes() + b" ")
    elif damage == "output":
        run.outputs["tabla"].write_bytes(b"secret-cell-value")
    elif damage == "missing_output":
        run.outputs["tabla"].unlink()
    elif damage == "extra":
        (job / "salidas" / "extra.txt").write_text("secret-cell-value")
    elif damage == "invalid_json":
        run.manifest_path.write_bytes(b"{secret-cell-value")
    elif damage == "fake_hash":
        edit_manifest(run, lambda m: m["salidas"]["tabla"].update(sha256="fake"))
    elif damage == "wrong_filename":
        edit_manifest(run, lambda m: m["salidas"]["tabla"].update(archivo="../secret"))
    result = check(recipe, root)
    assert not result.ok and result.issues[0].code == code
    assert "secret-cell-value" not in repr(result)


def test_rejects_cross_client_and_invalid_path(tmp_path):
    root, job, source, recipe, run = package(tmp_path)
    assert check(recipe, root, "../cliente_a").issues[0].code == "invalid_path"
    assert check(recipe, root, "cliente_b").issues[0].code == "invalid_path"


def test_blocked_has_no_package_and_review_state_is_not_approval(tmp_path):
    root, job, source, recipe, run = package(tmp_path / "review", value="")
    assert run.status == "revision_requerida"
    result = check(recipe, root)
    assert result.ok and result.status == "revision_requerida"
    blocked_root, _, _, blocked_recipe, blocked = package(
        tmp_path / "blocked", value="", severity="bloquear")
    assert blocked.status == "bloqueado" and blocked.manifest_path is None
    assert check(blocked_recipe, blocked_root).issues[0].code == "missing_manifest"


def test_rejects_inconsistent_state_and_redirected_file(tmp_path):
    root, job, source, recipe, run = package(tmp_path)
    edit_manifest(run, lambda m: m.update(estado="bloqueado"))
    assert check(recipe, root).issues[0].code == "invalid_manifest"
    run.manifest_path.unlink()
    try:
        run.manifest_path.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("symlink unavailable")
    assert check(recipe, root).issues[0].code == "invalid_path"
