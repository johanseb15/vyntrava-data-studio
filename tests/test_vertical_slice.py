import hashlib
import json

import pytest

from vyntrava_data_studio.delivery import DeliveryError, run_diagnostic
from vyntrava_data_studio.importer import CsvError
from vyntrava_data_studio.recipes import RecipeError
from vyntrava_data_studio.workspace import WorkspaceError


PILOT = (
    "id,nombre,email,ciudad\n"
    "C001,Ana Ruiz,ana@example.test,Buenos Aires\n"
    "C002,Luis Paz,,Córdoba\n"
    "C002,Luis Paz,,Córdoba\n"
    "C003,  Mara Sol  ,mara@example.test,   \n"
    "C004,Jo Vale,no-es-email,Rosario\n"
    "C005,,eve@example.test,Mendoza\n"
).encode("utf-8")


def setup_job(tmp_path, *, content=PILOT, delimiter=",", rules=None, validations=None):
    root = tmp_path / "clientes"
    base = root / "cliente_a" / "encargo_a"
    for folder in ("originales", "trabajo", "salidas", "evidencia"):
        (base / folder).mkdir(parents=True)
    source = base / "originales" / "clientes.csv"
    source.write_bytes(content)
    entry = {"id": "clientes", "ruta": "clientes.csv", "formato": "csv", "codificacion": "utf-8"}
    if delimiter is not None:
        entry["delimitador"] = delimiter
    recipe = {
        "id": "piloto_clientes", "version": "1.0.0", "tipo_encargo": "limpieza_clientes",
        "entradas": [entry],
        "esquema": {"clientes": {"columnas": ["id", "nombre", "email", "ciudad"], "extras": "rechazar"}},
        "parametros": {}, "reglas": rules if rules is not None else [{"id": "r1", "op": "diagnosticar", "entrada": "clientes", "params": {}}],
        "validaciones": validations if validations is not None else [], "analisis": [],
        "salidas": [{"id": "diagnostico", "tipo": "resumen_json", "ruta": "diagnostico.json"}],
    }
    recipe_path = tmp_path / "recipe.json"
    recipe_path.write_text(json.dumps(recipe, ensure_ascii=False), encoding="utf-8")
    return root, source, recipe_path


def test_pilot_a_delivers_reproducible_summary_and_preserves_original(tmp_path):
    root, source, recipe = setup_job(tmp_path)
    original = source.read_bytes()
    before = hashlib.sha256(original).hexdigest()

    result = run_diagnostic(recipe, root, "cliente_a", "encargo_a")

    assert source.read_bytes() == original
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    summary_bytes = result.summary_path.read_bytes()
    summary = json.loads(summary_bytes)
    assert summary["entradas"]["clientes"]["filas"] == 6
    assert summary["entradas"]["clientes"]["columnas"] == 4
    assert summary["entradas"]["clientes"]["duplicados_exactos"] == 1
    assert summary["entradas"]["clientes"]["celdas_vacias"] == 3
    assert summary["entradas"]["clientes"]["celdas_solo_espacios"] == 1
    assert summary["entradas"]["clientes"]["detalle_columnas"][0]["tipo_inferido"] == "texto"
    manifest = json.loads(result.manifest_path.read_bytes())
    assert manifest["entradas"]["clientes"]["sha256"] == before
    assert manifest["salidas"]["diagnostico"]["sha256"] == hashlib.sha256(summary_bytes).hexdigest()
    assert manifest["estado"] == "diagnostico"
    assert b"Ana Ruiz" not in summary_bytes + result.manifest_path.read_bytes()
    assert b"ana@example.test" not in summary_bytes + result.manifest_path.read_bytes()

    second_root, _, second_recipe = setup_job(tmp_path / "second")
    second = run_diagnostic(second_recipe, second_root, "cliente_a", "encargo_a")
    assert second.summary_path.read_bytes() == summary_bytes


def test_cross_job_route_rejected_without_outputs(tmp_path):
    root, _, recipe = setup_job(tmp_path)
    other = root / "cliente_b" / "encargo_b"
    for folder in ("originales", "trabajo", "salidas", "evidencia"):
        (other / folder).mkdir(parents=True)
    with pytest.raises(WorkspaceError):
        run_diagnostic(recipe, root, "cliente_b", "encargo_b")
    assert list((other / "salidas").iterdir()) == []
    assert list((other / "evidencia").iterdir()) == []


def test_cross_client_recipe_route_is_rejected_before_foreign_read(tmp_path, monkeypatch):
    root, _, recipe_path = setup_job(tmp_path)
    foreign_base = root / "cliente_b" / "encargo_b"
    for folder in ("originales", "trabajo", "salidas", "evidencia"):
        (foreign_base / folder).mkdir(parents=True)
    foreign = foreign_base / "originales" / "clientes.csv"
    foreign.write_bytes(PILOT)
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["entradas"][0]["ruta"] = "../../cliente_b/encargo_b/originales/clientes.csv"
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
    original_open = type(foreign).open

    def deny_foreign_open(path, *args, **kwargs):
        if path == foreign:
            pytest.fail("foreign original was opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(type(foreign), "open", deny_foreign_open)
    with pytest.raises(RecipeError) as exc:
        run_diagnostic(recipe_path, root, "cliente_a", "encargo_a")
    assert (exc.value.code, exc.value.location) == ("invalid_path", "$.entradas[0].ruta")
    assert list((root / "cliente_a" / "encargo_a" / "salidas").iterdir()) == []
    assert list((root / "cliente_a" / "encargo_a" / "evidencia").iterdir()) == []


def test_bad_csv_or_schema_leaves_no_valid_delivery(tmp_path):
    root, source, recipe = setup_job(tmp_path, content=b"id,nombre,email,ciudad\n\"broken")
    with pytest.raises(CsvError):
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert not (source.parent.parent / "evidencia" / "manifiesto.json").exists()
    assert list((source.parent.parent / "salidas").iterdir()) == []

    source.write_bytes(b"id,nombre,email,otra\n1,Ana,,x\n")
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert exc.value.code == "schema_mismatch"
    assert list((source.parent.parent / "salidas").iterdir()) == []


def test_delimiter_confirmation_and_unsupported_capability_fail_before_read(tmp_path):
    root, source, recipe_path = setup_job(tmp_path, delimiter=None)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe_path, root, "cliente_a", "encargo_a")
    assert exc.value.code == "delimiter_required"
    result = run_diagnostic(recipe_path, root, "cliente_a", "encargo_a", {"clientes": ","})
    assert json.loads(result.manifest_path.read_bytes())["delimitadores"] == {"clientes": ","}

    root2, source2, recipe2 = setup_job(tmp_path / "unsupported", content=b"bad", rules=[
        {"id": "r1", "op": "recortar_espacios", "entrada": "clientes", "params": {"columnas": ["nombre"]}}
    ])
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe2, root2, "cliente_a", "encargo_a")
    assert exc.value.code == "unsupported_capability"
    assert source2.read_bytes() == b"bad"


def test_validation_is_rejected_before_reading_invalid_csv_or_creating_outputs(tmp_path, monkeypatch):
    root, source, recipe = setup_job(
        tmp_path,
        content=b'id,nombre,email,ciudad\n"broken',
        validations=[{
            "id": "v1", "op": "columnas_requeridas", "entrada": "clientes",
            "params": {"columnas": ["id", "nombre"]}, "severidad": "bloquear",
        }],
    )
    original_open = type(source).open

    def reject_source_open(path, *args, **kwargs):
        if path == source:
            pytest.fail("original CSV was opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(type(source), "open", reject_source_open)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")

    assert exc.value.code == "unsupported_capability"
    base = source.parent.parent
    assert list((base / "salidas").iterdir()) == []
    assert list((base / "evidencia").iterdir()) == []


def test_competing_output_is_never_deleted(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    output = source.parent.parent / "salidas" / "diagnostico.json"
    original_open = type(output).open

    def competing_open(path, mode="r", *args, **kwargs):
        if path == output and mode == "xb":
            output.write_bytes(b"other process")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(type(output), "open", competing_open)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert exc.value.code == "write_error"
    assert output.read_bytes() == b"other process"
    assert not (source.parent.parent / "evidencia" / "manifiesto.json").exists()


def test_manifest_does_not_export_unused_recipe_parameters(tmp_path):
    root, _, recipe_path = setup_job(tmp_path)
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["parametros"]["nota"] = "private-token-example"
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
    result = run_diagnostic(recipe_path, root, "cliente_a", "encargo_a")
    assert b"private-token-example" not in result.manifest_path.read_bytes()
