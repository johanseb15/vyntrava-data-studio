import hashlib
import hmac
import json

import pytest

from vyntrava_data_studio.delivery import DeliveryError
from vyntrava_data_studio.recipes import RecipeError
from vyntrava_data_studio.sprint02 import run_recipe
import vyntrava_data_studio.sprint02 as sprint02


PILOT = ("id,nombre,email,ciudad\n"
         "C001,Ana Ruiz,ana@example.test,Buenos Aires\n"
         "C002,Luis Paz,,Córdoba\n"
         "C002,Luis Paz,,Córdoba\n"
         "C003,  Mara Sol  ,mara@example.test,   \n"
         "C004,Jo Vale,no-es-email,Rosario\n"
         "C005,,eve@example.test,Mendoza\n").encode()


def setup(tmp_path, severity="advertir"):
    root = tmp_path / "clientes"
    base = root / "cliente_a" / "encargo_a"
    for folder in ("originales", "trabajo", "salidas", "evidencia"):
        (base / folder).mkdir(parents=True)
    source = base / "originales" / "clientes.csv"
    source.write_bytes(PILOT)
    data = {
        "id": "piloto_clientes", "version": "1.0.0", "tipo_encargo": "limpieza_clientes",
        "entradas": [{"id": "clientes", "ruta": "clientes.csv", "formato": "csv", "codificacion": "utf-8", "delimitador": ","}],
        "esquema": {"clientes": {"columnas": ["id", "nombre", "email", "ciudad"], "extras": "rechazar"}},
        "parametros": {"columna_email": "email"},
        "reglas": [
            {"id": "d", "op": "diagnosticar", "entrada": "clientes", "params": {}},
            {"id": "r1", "op": "eliminar_duplicados_exactos", "entrada": "clientes", "params": {"aprobacion": "deduplicar"}},
            {"id": "r2", "op": "recortar_espacios", "entrada": "clientes", "params": {"columnas": ["nombre", "ciudad"]}},
        ],
        "validaciones": [
            {"id": "v1", "op": "no_vacio", "entrada": "clientes", "params": {"columnas": ["nombre", "email", "ciudad"]}, "severidad": severity},
            {"id": "v2", "op": "email_simple", "entrada": "clientes", "params": {"columna": {"parametro": "columna_email"}}, "severidad": severity},
        ],
        "analisis": [],
        "salidas": [{"id": "resumen", "tipo": "resumen_json", "ruta": "resumen.json"},
                    {"id": "tabla", "tipo": "tabla_csv", "ruta": "clientes_limpios.csv", "fuente": "clientes"}],
    }
    recipe = tmp_path / "recipe.json"
    recipe.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return root, source, recipe


def approval(recipe, source, key=b"synthetic-test-key"):
    payload = {"id": "deduplicar", "responsable": "revisor_sintetico",
               "receta_sha256": hashlib.sha256(recipe.read_bytes()).hexdigest(),
               "entradas_sha256": {"clientes": hashlib.sha256(source.read_bytes()).hexdigest()}}
    signature = hmac.new(key, json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(), hashlib.sha256).hexdigest()
    return {**payload, "firma": signature}


def test_pilot_a_cleanup_and_repeat(tmp_path):
    root, source, recipe = setup(tmp_path / "first")
    signed = approval(recipe, source)
    result = run_recipe(recipe, root, "cliente_a", "encargo_a", approvals={"deduplicar": signed}, approval_key=b"synthetic-test-key")
    assert result.status == "revision_requerida"
    report = json.loads(result.outputs["resumen"].read_bytes())
    assert report["entradas"]["clientes"]["antes"]["filas"] == 6
    assert report["entradas"]["clientes"]["despues"]["filas"] == 5
    assert report["entradas"]["clientes"]["despues"]["duplicados_exactos"] == 0
    assert report["validaciones"] == {"v1": {"incidencias": 3, "severidad": "advertir"}, "v2": {"incidencias": 1, "severidad": "advertir"}}
    assert b"Mara Sol" in result.outputs["tabla"].read_bytes()
    assert b"  Mara Sol  " not in result.outputs["tabla"].read_bytes()
    assert source.read_bytes() == PILOT
    assert b"Ana Ruiz" not in result.outputs["resumen"].read_bytes() + result.manifest_path.read_bytes()
    root2, source2, recipe2 = setup(tmp_path / "second")
    result2 = run_recipe(recipe2, root2, "cliente_a", "encargo_a", approvals={"deduplicar": approval(recipe2, source2)}, approval_key=b"synthetic-test-key")
    assert result.outputs["resumen"].read_bytes() == result2.outputs["resumen"].read_bytes()
    assert result.outputs["tabla"].read_bytes() == result2.outputs["tabla"].read_bytes()


def test_blocking_validation_publishes_nothing(tmp_path):
    root, source, recipe = setup(tmp_path, "bloquear")
    result = run_recipe(recipe, root, "cliente_a", "encargo_a", approvals={"deduplicar": approval(recipe, source)}, approval_key=b"synthetic-test-key")
    assert result.status == "bloqueado"
    assert result.manifest_path is None
    assert list((source.parent.parent / "salidas").iterdir()) == []
    assert list((source.parent.parent / "evidencia").iterdir()) == []


@pytest.mark.parametrize("bad", ["missing", "signature", "hash"])
def test_destructive_rule_requires_matching_signature(tmp_path, bad):
    root, source, recipe = setup(tmp_path)
    record = approval(recipe, source)
    if bad == "signature":
        record["firma"] = "0" * 64
    elif bad == "hash":
        record["entradas_sha256"]["clientes"] = "0" * 64
    with pytest.raises(DeliveryError) as exc:
        run_recipe(recipe, root, "cliente_a", "encargo_a", approvals={} if bad == "missing" else {"deduplicar": record}, approval_key=b"synthetic-test-key")
    assert exc.value.code == "approval_required"
    assert list((source.parent.parent / "salidas").iterdir()) == []


@pytest.mark.parametrize("overrides,code", [({"desconocido": "email"}, "unknown_reference"),
                                            ({"columna_email": 7}, "invalid_type"),
                                            ({"columna_email": "fantasma"}, "unknown_reference")])
def test_invalid_overrides_fail_before_publication(tmp_path, overrides, code):
    root, source, recipe = setup(tmp_path)
    with pytest.raises(RecipeError) as exc:
        run_recipe(recipe, root, "cliente_a", "encargo_a", overrides=overrides)
    assert exc.value.code == code
    assert list((source.parent.parent / "salidas").iterdir()) == []


def test_numeric_validations_count_invalid_rows(tmp_path):
    root, source, recipe = setup(tmp_path)
    source.write_bytes(b"id,nombre,email,ciudad\n1,2,3,4\n2,0,-1,4\n3,1.5,NaN,4\n")
    data = json.loads(recipe.read_text(encoding="utf-8"))
    data["reglas"] = []
    data["validaciones"] = [
        {"id": "v1", "op": "entero_positivo", "entrada": "clientes", "params": {"columna": "nombre"}, "severidad": "advertir"},
        {"id": "v2", "op": "decimal_positivo", "entrada": "clientes", "params": {"columna": "email"}, "severidad": "advertir"},
    ]
    recipe.write_text(json.dumps(data), encoding="utf-8")
    result = run_recipe(recipe, root, "cliente_a", "encargo_a")
    assert result.validations == {"v1": {"incidencias": 2, "severidad": "advertir"},
                                  "v2": {"incidencias": 2, "severidad": "advertir"}}


def test_existing_output_is_not_overwritten(tmp_path):
    root, source, recipe = setup(tmp_path)
    target = source.parent.parent / "salidas" / "resumen.json"
    target.write_bytes(b"preserve")
    with pytest.raises(ValueError):
        run_recipe(recipe, root, "cliente_a", "encargo_a", approvals={"deduplicar": approval(recipe, source)}, approval_key=b"synthetic-test-key")
    assert target.read_bytes() == b"preserve"


def test_recipe_change_after_parse_cannot_be_approved_as_executed(tmp_path, monkeypatch):
    root, source, recipe = setup(tmp_path)
    data = json.loads(recipe.read_text(encoding="utf-8"))
    data["reglas"] = []
    recipe.write_text(json.dumps(data), encoding="utf-8")
    original_load = sprint02.load_recipe

    def change_after_parse(path, overrides=None):
        parsed = original_load(path, overrides)
        replacement = json.loads(path.read_text(encoding="utf-8"))
        replacement["id"] = "otra_receta"
        path.write_text(json.dumps(replacement), encoding="utf-8")
        return parsed

    monkeypatch.setattr(sprint02, "load_recipe", change_after_parse)
    with pytest.raises(DeliveryError) as exc:
        run_recipe(recipe, root, "cliente_a", "encargo_a")
    assert exc.value.code == "recipe_changed"
    assert list((source.parent.parent / "salidas").iterdir()) == []


def test_optional_required_column_reports_warning(tmp_path):
    root, source, recipe = setup(tmp_path)
    data = json.loads(recipe.read_text(encoding="utf-8"))
    data["reglas"] = []
    data["validaciones"] = [{"id": "v1", "op": "columnas_requeridas", "entrada": "clientes",
                            "params": {"columnas": ["id", "telefono"]}, "severidad": "advertir"}]
    recipe.write_text(json.dumps(data), encoding="utf-8")
    result = run_recipe(recipe, root, "cliente_a", "encargo_a")
    assert result.status == "revision_requerida"
    assert result.validations["v1"] == {"incidencias": 1, "severidad": "advertir"}
