import hashlib
import json
import os
import tempfile

import pytest

from vyntrava_data_studio import delivery
from vyntrava_data_studio.delivery import DeliveryError, run_diagnostic, verify_delivery
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


def test_ambiguous_csv_requires_matching_confirmation_before_publication(tmp_path):
    content = b"id,nombre;alias,email,ciudad\nC001,Ana;A,ana@example.test,Buenos Aires\n"
    root, source, recipe_path = setup_job(tmp_path, content=content)
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["esquema"]["clientes"]["columnas"] = ["id", "nombre;alias", "email", "ciudad"]
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")

    with pytest.raises(CsvError) as exc:
        run_diagnostic(recipe_path, root, "cliente_a", "encargo_a")
    assert exc.value.code == "delimiter_ambiguous"
    assert list((source.parent.parent / "salidas").iterdir()) == []
    assert list((source.parent.parent / "evidencia").iterdir()) == []

    result = run_diagnostic(recipe_path, root, "cliente_a", "encargo_a", {"clientes": ","})
    assert json.loads(result.manifest_path.read_bytes())["delimitadores"] == {"clientes": ","}
    assert json.loads(result.summary_path.read_bytes())["entradas"]["clientes"]["columnas"] == 4


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
    original_rename = os.rename

    def competing_rename(source, target, *args, **kwargs):
        if target == output:
            output.write_bytes(b"other process")
        return original_rename(source, target, *args, **kwargs)

    monkeypatch.setattr(os, "rename", competing_rename)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert exc.value.code == "write_error"
    assert output.read_bytes() == b"other process"
    assert not (source.parent.parent / "evidencia" / "manifiesto.json").exists()


def test_original_change_after_preparation_preserves_competing_output(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    output = source.parent.parent / "salidas" / "diagnostico.json"
    original_sha256 = delivery._sha256
    changed = False

    def replace_after_preparation(path):
        nonlocal changed
        if path == source and not changed and list((source.parent.parent / "trabajo").iterdir()):
            assert not output.exists()
            output.write_bytes(b"third-party output")
            changed = True
            raise DeliveryError("original_changed")
        return original_sha256(path)

    monkeypatch.setattr(delivery, "_sha256", replace_after_preparation)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")

    assert exc.value.code == "original_changed"
    assert changed
    assert output.read_bytes() == b"third-party output"
    assert not (source.parent.parent / "evidencia" / "manifiesto.json").exists()


def test_recipe_change_after_preparation_blocks_publication(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    original_stage = delivery._stage_bytes
    stages = 0

    def change_recipe_after_staging(folder, content):
        nonlocal stages
        path = original_stage(folder, content)
        stages += 1
        if stages == 2:
            recipe.write_bytes(recipe.read_bytes() + b" ")
        return path

    monkeypatch.setattr(delivery, "_stage_bytes", change_recipe_after_staging)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")

    assert exc.value.code == "recipe_changed"
    assert stages == 2
    assert list((base / "salidas").iterdir()) == []
    assert list((base / "evidencia").iterdir()) == []
    assert source.read_bytes() == PILOT


def test_manifest_publication_failure_leaves_orphan_summary(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    summary = base / "salidas" / "diagnostico.json"
    manifest = base / "evidencia" / "manifiesto.json"
    original_rename = os.rename

    def failing_manifest_rename(source_path, target, *args, **kwargs):
        if target == manifest:
            raise OSError("synthetic publication failure")
        return original_rename(source_path, target, *args, **kwargs)

    monkeypatch.setattr(os, "rename", failing_manifest_rename)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")

    assert exc.value.code == "write_error"
    assert summary.exists()  # An orphan is pending recovery, not approved.
    assert not manifest.exists()
    assert not any(os.path.samefile(item, summary) for item in (base / "trabajo").iterdir())


def test_success_leaves_no_work_alias_for_published_files(tmp_path):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    result = run_diagnostic(recipe, root, "cliente_a", "encargo_a")

    assert result.summary_path.exists()
    assert result.manifest_path.exists()
    assert list((base / "trabajo").iterdir()) == []


def test_private_preparation_is_complete_before_any_final_file(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    original_sha256 = delivery._sha256
    inspected = False

    def inspect_preparation(path):
        nonlocal inspected
        if path == source and list((base / "trabajo").iterdir()) and not inspected:
            staged = list((base / "trabajo").iterdir())
            assert len(staged) == 2
            assert all(item.is_file() and item.stat().st_size > 0 for item in staged)
            assert list((base / "salidas").iterdir()) == []
            assert list((base / "evidencia").iterdir()) == []
            inspected = True
        return original_sha256(path)

    monkeypatch.setattr(delivery, "_sha256", inspect_preparation)
    run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert inspected


def test_unrelated_work_file_does_not_block_private_preparation(tmp_path):
    root, source, recipe = setup_job(tmp_path)
    unrelated = source.parent.parent / "trabajo" / "diagnostic-stage"
    unrelated.write_bytes(b"other work")
    result = run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert result.manifest_path.exists()
    assert unrelated.read_bytes() == b"other work"


@pytest.mark.parametrize("failure", ["write", "close"])
def test_private_temporary_failure_cannot_publish(tmp_path, monkeypatch, failure):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    original_temp = tempfile.NamedTemporaryFile

    class FailingTemporary:
        def __init__(self, target):
            self.target = target
            self.name = target.name

        def write(self, data):
            if failure == "write":
                raise OSError("synthetic temporary write failure")
            return self.target.write(data)

        def flush(self):
            return self.target.flush()

        def close(self):
            self.target.close()
            if failure == "close":
                raise OSError("synthetic temporary close failure")

    def failing_temp(*args, **kwargs):
        return FailingTemporary(original_temp(*args, **kwargs))

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", failing_temp)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert exc.value.code == "write_error"
    assert list((base / "salidas").iterdir()) == []
    assert list((base / "evidencia").iterdir()) == []


def test_temporary_creation_failure_has_generic_error_without_paths(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent

    def fail_creation(*args, **kwargs):
        raise OSError(f"cannot create {base / 'trabajo' / 'secret-path.tmp'}")

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", fail_creation)
    with pytest.raises(DeliveryError) as stage_exc:
        delivery._stage_bytes(base / "trabajo", b"payload")
    assert stage_exc.value.code == "write_error"
    assert str(stage_exc.value) == "write_error"
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert exc.value.code == "write_error"
    assert str(exc.value) == "write_error"
    assert str(base) not in str(exc.value)
    assert list((base / "salidas").iterdir()) == []
    assert list((base / "evidencia").iterdir()) == []


def test_corrupt_closed_temporary_cannot_publish(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    original_temp = tempfile.NamedTemporaryFile

    class CorruptOnClose:
        def __init__(self, target):
            self.target = target
            self.name = target.name

        def write(self, data):
            return self.target.write(data)

        def flush(self):
            return self.target.flush()

        def close(self):
            self.target.close()
            with open(self.name, "wb") as changed:
                changed.write(b"corrupted")

    def corrupt_temp(*args, **kwargs):
        return CorruptOnClose(original_temp(*args, **kwargs))

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", corrupt_temp)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert exc.value.code == "write_error"
    assert list((base / "salidas").iterdir()) == []
    assert list((base / "evidencia").iterdir()) == []


def test_preexisting_manifest_is_preserved_without_publication(tmp_path):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    manifest = base / "evidencia" / "manifiesto.json"
    manifest.write_bytes(b"other process")
    with pytest.raises((DeliveryError, WorkspaceError)):
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert manifest.read_bytes() == b"other process"
    assert not (base / "salidas" / "diagnostico.json").exists()


def test_competing_manifest_is_never_overwritten(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    manifest = base / "evidencia" / "manifiesto.json"
    original_rename = os.rename

    def competing_rename(source_path, target, *args, **kwargs):
        if target == manifest:
            manifest.write_bytes(b"other process")
        return original_rename(source_path, target, *args, **kwargs)

    monkeypatch.setattr(os, "rename", competing_rename)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert exc.value.code == "write_error"
    assert manifest.read_bytes() == b"other process"
    assert (base / "salidas" / "diagnostico.json").exists()


def test_published_summary_hash_mismatch_blocks_manifest(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    summary = base / "salidas" / "diagnostico.json"
    original_rename = os.rename

    def corrupt_published_summary(source_path, target, *args, **kwargs):
        original_rename(source_path, target, *args, **kwargs)
        if target == summary:
            target.write_bytes(b"corrupted")

    monkeypatch.setattr(os, "rename", corrupt_published_summary)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert exc.value.code == "write_error"
    assert summary.read_bytes() == b"corrupted"
    assert not (base / "evidencia" / "manifiesto.json").exists()


def test_manifest_publication_is_last_and_summary_hash_matches(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    summary = base / "salidas" / "diagnostico.json"
    manifest = base / "evidencia" / "manifiesto.json"
    original_rename = os.rename
    published = []

    def observe_rename(source_path, target, *args, **kwargs):
        assert source_path.parent == base / "trabajo"
        assert source_path.stat().st_size > 0
        if target == summary:
            assert not manifest.exists()
        elif target == manifest:
            assert summary.exists()
            staged_manifest = json.loads(source_path.read_bytes())
            assert hashlib.sha256(summary.read_bytes()).hexdigest() == staged_manifest["salidas"]["diagnostico"]["sha256"]
        published.append(target)
        return original_rename(source_path, target, *args, **kwargs)

    monkeypatch.setattr(os, "rename", observe_rename)
    run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert published == [summary, manifest]


@pytest.mark.skipif(os.name != "nt", reason="Windows NTFS rename collision semantics")
def test_windows_rename_rejects_existing_target(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_bytes(b"new")
    target.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        os.rename(source, target)
    assert source.read_bytes() == b"new"
    assert target.read_bytes() == b"existing"


def test_manifest_does_not_export_unused_recipe_parameters(tmp_path):
    root, _, recipe_path = setup_job(tmp_path)
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["parametros"]["nota"] = "private-token-example"
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
    result = run_diagnostic(recipe_path, root, "cliente_a", "encargo_a")
    assert b"private-token-example" not in result.manifest_path.read_bytes()


def test_delivery_verification_success_and_missing_manifest(tmp_path):
    root, source, recipe = setup_job(tmp_path)
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "incompleto"
    run = run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "completo-verificado"
    run.manifest_path.unlink()
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "incompleto"


@pytest.mark.parametrize("damage", ["fake_manifest", "bad_summary", "replaced_summary", "bad_hash", "route", "input_changed", "recipe_changed"])
def test_delivery_verification_rejects_inconsistent_artifacts(tmp_path, damage):
    root, source, recipe = setup_job(tmp_path)
    run = run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    if damage == "fake_manifest":
        run.manifest_path.write_text("{}", encoding="utf-8")
    elif damage == "bad_summary":
        run.summary_path.write_bytes(b"not json")
    elif damage == "replaced_summary":
        run.summary_path.write_bytes(b'{}')
    elif damage in {"bad_hash", "route"}:
        manifest = json.loads(run.manifest_path.read_bytes())
        manifest["salidas"]["diagnostico"]["sha256" if damage == "bad_hash" else "archivo"] = (
            "0" * 64 if damage == "bad_hash" else "../otro.json")
        run.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    elif damage == "input_changed":
        source.write_bytes(b"changed")
    else:
        recipe.write_text(recipe.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "inconsistente"


def test_delivery_verification_classifies_orphans_and_temporary(tmp_path):
    root, source, recipe = setup_job(tmp_path)
    base = source.parent.parent
    temporary = base / "trabajo" / "diagnostic-remnant.tmp"
    temporary.write_bytes(b"partial")
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "incompleto"
    temporary.unlink()
    run = run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    temporary.write_bytes(b"partial")
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "inconsistente"
    temporary.unlink()
    run.summary_path.unlink()
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "inconsistente"


def test_delivery_verification_hides_io_error_detail(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    run = run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    original_open = type(run.manifest_path).open

    def denied(path, *args, **kwargs):
        if path == run.manifest_path and args == ("rb",):
            raise PermissionError("sensitive-path-and-data")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(type(run.manifest_path), "open", denied)
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "no-verificable"


def test_delivery_verification_rejects_missing_input_and_duplicate_json_key(tmp_path):
    root, source, recipe = setup_job(tmp_path)
    run = run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    source.unlink()
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "inconsistente"
    source.write_bytes(PILOT)
    run.manifest_path.write_bytes(run.manifest_path.read_bytes().replace(
        b'"estado":"diagnostico"', b'"estado":"diagnostico","estado":"diagnostico"'))
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "inconsistente"


@pytest.mark.parametrize("artifact", ["summary", "manifest"])
@pytest.mark.parametrize("depth", [80, 10000])
def test_delivery_verification_rejects_nested_json_without_exposing_data(tmp_path, artifact, depth):
    root, _, recipe = setup_job(tmp_path)
    run = run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    target = run.summary_path if artifact == "summary" else run.manifest_path
    target.write_bytes(b"[" * depth + b'"sensitive-cell-value"' + b"]" * depth)

    result = verify_delivery(recipe, root, "cliente_a", "encargo_a")

    assert result == "inconsistente"
    assert "sensitive-cell-value" not in result
    assert str(tmp_path) not in result


def test_failed_manifest_publication_is_incomplete_for_consumer(tmp_path, monkeypatch):
    root, source, recipe = setup_job(tmp_path)
    manifest = source.parent.parent / "evidencia" / "manifiesto.json"
    original_rename = os.rename

    def fail_manifest(source_path, target, *args, **kwargs):
        if target == manifest:
            raise OSError("sensitive intermediate failure")
        return original_rename(source_path, target, *args, **kwargs)

    monkeypatch.setattr(os, "rename", fail_manifest)
    with pytest.raises(DeliveryError) as exc:
        run_diagnostic(recipe, root, "cliente_a", "encargo_a")
    assert str(exc.value) == "write_error"
    assert verify_delivery(recipe, root, "cliente_a", "encargo_a") == "incompleto"
